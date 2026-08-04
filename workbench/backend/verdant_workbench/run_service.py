from __future__ import annotations

import hashlib
import json
import tempfile
import time
from dataclasses import asdict
from pathlib import Path
from threading import Event, RLock, Thread
from typing import Any

from verdant_kernel import ExperienceCommand
from verdant_benchmarks.ethomorphism import ArmName, BenchmarkConfig, EthomorphismBenchmarkHarness

from .artifact_store import ArtifactIntegrityError, ContentAddressedArtifactStore
from .events import payload_hash
from .curriculum import (
    CURRICULUM_COMPILER_VERSION,
    CURRICULUM_PACKAGE_MEDIA_TYPE,
    CurriculumCompileRequest,
    CurriculumCompiler,
    CurriculumFreezeRequest,
    CurriculumPackCompileRequest,
    CurriculumPackFreezeRequest,
    curriculum_pack_bundle_source,
    curriculum_pack_selection_title,
    build_curriculum_package,
    compiled_commands_jsonl,
    read_curriculum_package,
)
from .models import (
    CommandEnvelope,
    EventEnvelope,
    GrammarPreviewRequest,
    GrammarRuleTeachRequest,
    LanguageSentenceTeachRequest,
    LexemeTeachRequest,
    OrganismConfig,
    ProbeRequest,
    TeachingRequest,
    new_id,
    utc_now_iso,
)
from .repository import (
    AppendOnlyEventLedger, CheckpointRecord, CurriculumRecord, ExperimentRecord, ExperimentRunRecord,
    QueueItemRecord, RunRecord, WorkbenchRepository,
)
from .experiments import (
    EXPERIMENT_PACKAGE_MEDIA_TYPE, EXPERIMENT_PROTOCOL_ETHOMORPHISM, ExperimentAuthorRequest,
    ExperimentForkRequest, ExperimentManifest, build_experiment_package, build_verification_package,
    config_from_manifest, default_assertions, default_interventions, default_metrics, evaluate_assertions,
    read_experiment_package, read_verification_package,
    run_ethomorphism_isolated, sha256_bytes,
)
from .worker import EngineWorkerSupervisor
from .providers import (
    ProviderCapture, ProviderConfiguration, ProviderProposalRequest, ProviderRegistry,
    PROVIDER_CAPTURE_MEDIA_TYPE, build_provider_capture_package, read_provider_capture_package,
)
from .plugins import PluginManager
from .release_identity import source_build_identity


class RunServiceError(RuntimeError):
    pass


class RunNotActiveError(RunServiceError):
    pass


def _assert_manifest_build_identity(manifest: ExperimentManifest) -> None:
    current_build = source_build_identity()
    for key in ("engine_source_sha256", "workbench_source_sha256", "dependency_lock_sha256"):
        expected = getattr(manifest, key, "")
        if expected and expected != current_build[key]:
            raise RunServiceError(
                f"Experiment build identity mismatch for {key}: expected {expected}, current {current_build[key]}"
            )


class RunExecutionControl:
    def __init__(self) -> None:
        self.state = "idle"
        self.pause_requested = Event()
        self.stop_requested = Event()
        self.thread: Thread | None = None
        self.last_error: str | None = None
        self.active_queue_item_id: str | None = None


class DurableRunService:
    """Persistent laboratory identity/history around isolated Verdant workers."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.repository = WorkbenchRepository(self.root / "workbench.db")
        self.recovered_stale_runs = self.repository.recover_stale_active_runs()
        self.artifacts = ContentAddressedArtifactStore(self.root / "artifacts")
        self.events = AppendOnlyEventLedger(self.root / "runs", self.repository)
        self.curriculum_compiler = CurriculumCompiler()
        self.providers = ProviderRegistry(self.root / "connections")
        self.plugins = PluginManager(self.root / "plugins", bundled_root=Path(__file__).resolve().parents[2] / "plugins")
        self._workers: dict[str, EngineWorkerSupervisor] = {}
        self._execution: dict[str, RunExecutionControl] = {}
        self._experiment_threads: dict[str, Thread] = {}
        self._lock = RLock()

    def close(self) -> None:
        with self._lock:
            controls = list(self._execution.items())
        for _, control in controls:
            control.stop_requested.set()
        for _, control in controls:
            thread = control.thread
            if thread is not None and thread.is_alive():
                thread.join(timeout=10.0)
        with self._lock:
            experiment_threads = list(self._experiment_threads.values())
        for thread in experiment_threads:
            if thread.is_alive():
                thread.join(timeout=2.0)
        with self._lock:
            for run_id, worker in list(self._workers.items()):
                worker.close()
                try:
                    self.repository.set_run_status(run_id, "closed")
                except KeyError:
                    pass
            self._workers.clear()
            self._execution.clear()
            self._experiment_threads.clear()
        self.repository.close()

    def create_project(self, name: str, *, project_id: str | None = None):
        return self.repository.create_project(project_id or new_id("proj"), name.strip() or "Verdant Project")

    def _control(self, run_id: str) -> RunExecutionControl:
        self.repository.get_run(run_id)
        with self._lock:
            control = self._execution.get(run_id)
            if control is None:
                control = RunExecutionControl()
                self._execution[run_id] = control
            return control

    def _emit_control_event(self, run_id: str, event_type: str, payload: dict[str, Any], *, command_id: str | None = None) -> EventEnvelope:
        run = self.repository.get_run(run_id)
        digest = payload_hash(payload)
        event = EventEnvelope(
            event_id=new_id("evt"),
            run_id=run_id,
            organism_id=run.organism_id,
            engine_cycle=run.latest_cycle,
            state_revision=run.latest_state_revision,
            event_type=event_type,
            source_command_id=command_id or new_id("cmd"),
            timestamp_utc=utc_now_iso(),
            payload=payload,
            payload_sha256=digest,
        )
        self.events.append((event,))
        return event

    def _dirty_state(self, run: RunRecord) -> dict[str, Any]:
        if run.head_checkpoint_id is None:
            return {"dirty": True, "head_checkpoint_id": None, "saved_state_revision": None, "saved_cycle": None}
        checkpoint = self.repository.get_checkpoint(run.head_checkpoint_id)
        dirty = run.latest_fingerprint != checkpoint.canonical_fingerprint
        return {
            "dirty": dirty,
            "head_checkpoint_id": checkpoint.checkpoint_id,
            "saved_state_revision": checkpoint.state_revision,
            "saved_cycle": checkpoint.cycle,
        }

    def create_run(self, project_id: str, config: OrganismConfig, *, organism_id: str | None = None, run_id: str | None = None) -> dict[str, Any]:
        self.repository.get_project(project_id)
        organism_id = organism_id or new_id("org")
        run_id = run_id or new_id("run")
        self.repository.create_organism(
            organism_id=organism_id,
            project_id=project_id,
            seed=config.seed,
            state_dim=config.state_dim,
            run_label=config.run_label,
        )
        worker = EngineWorkerSupervisor.create(config, run_id=run_id, organism_id=organism_id)
        descriptor = worker.request("descriptor")
        self.repository.create_run(
            run_id=run_id,
            project_id=project_id,
            organism_id=organism_id,
            status="active",
            latest_state_revision=descriptor["state_revision"],
            latest_cycle=descriptor["cycle"],
            latest_fingerprint=descriptor["fingerprint"],
        )
        with self._lock:
            self._workers[run_id] = worker
            self._execution[run_id] = RunExecutionControl()
        self._emit_control_event(run_id, "RUN_STARTED", {"reason": "organism_created", "execution_state": "idle"})
        return descriptor

    def _worker(self, run_id: str) -> EngineWorkerSupervisor:
        with self._lock:
            worker = self._workers.get(run_id)
        if worker is None or not worker.alive:
            raise RunNotActiveError(f"Run {run_id} is not active.")
        return worker

    def _sync_after_receipt(self, run_id: str, receipt: dict[str, Any]) -> None:
        from .models import EventEnvelope
        events = tuple(EventEnvelope.model_validate(item) for item in receipt.get("events", ()))
        if events:
            self.events.append(events)
        self.repository.update_run_head(
            run_id,
            state_revision=int(receipt["state_revision_after"]),
            cycle=int(receipt["cycle_after"]),
            fingerprint=str(receipt["fingerprint_after"]),
            status="active",
        )

    def teach(self, run_id: str, request: TeachingRequest, *, expected_state_revision: int | None = None, command_id: str | None = None) -> dict[str, Any]:
        worker = self._worker(run_id)
        run = self.repository.get_run(run_id)
        envelope = CommandEnvelope(
            command_id=command_id or new_id("cmd"),
            run_id=run_id,
            organism_id=run.organism_id,
            command_type="TEACH",
            expected_state_revision=expected_state_revision,
        )
        receipt = worker.request("teach", {
            "envelope": envelope.model_dump(mode="json"),
            "request": request.model_dump(mode="json"),
        })
        self._sync_after_receipt(run_id, receipt)
        return receipt

    def submit_experience(self, run_id: str, command: ExperienceCommand, *, expected_state_revision: int | None = None, command_id: str | None = None) -> dict[str, Any]:
        worker = self._worker(run_id)
        run = self.repository.get_run(run_id)
        envelope = CommandEnvelope(
            command_id=command_id or new_id("cmd"),
            run_id=run_id,
            organism_id=run.organism_id,
            command_type="EXPERIENCE",
            expected_state_revision=expected_state_revision,
        )
        receipt = worker.request("experience", {
            "envelope": envelope.model_dump(mode="json"),
            "command": command.model_dump(mode="json"),
        })
        self._sync_after_receipt(run_id, receipt)
        return receipt

    def probe(self, run_id: str, request: ProbeRequest, *, expected_state_revision: int | None = None, command_id: str | None = None) -> dict[str, Any]:
        worker = self._worker(run_id)
        run = self.repository.get_run(run_id)
        envelope = CommandEnvelope(
            command_id=command_id or new_id("cmd"),
            run_id=run_id,
            organism_id=run.organism_id,
            command_type="PROBE",
            expected_state_revision=expected_state_revision,
        )
        receipt = worker.request("probe", {
            "envelope": envelope.model_dump(mode="json"),
            "request": request.model_dump(mode="json"),
        })
        self._sync_after_receipt(run_id, receipt)
        return receipt

    def forensic_structures(self, run_id: str) -> dict[str, Any]:
        return self._worker(run_id).request("forensic_list_structures")

    def forensic_structure_detail(self, run_id: str, structure_id: str) -> dict[str, Any]:
        return self._worker(run_id).request("forensic_structure_detail", {"structure_id": structure_id})

    def forensic_structure_replay(self, run_id: str, structure_id: str) -> dict[str, Any]:
        return self._worker(run_id).request("forensic_structure_replay", {"structure_id": structure_id})

    def forensic_structure_graph(self, run_id: str, structure_id: str) -> dict[str, Any]:
        return self._worker(run_id).request("forensic_structure_graph", {"structure_id": structure_id})

    def living_explorer_frame(self, run_id: str, cycle: int | None = None, *, max_nodes: int = 240, max_edges: int = 500) -> dict[str, Any]:
        return self._worker(run_id).request("living_explorer_frame", {"cycle": cycle, "max_nodes": max_nodes, "max_edges": max_edges})

    def living_explorer_timeline(self, run_id: str, *, max_frames: int = 240, max_nodes: int = 240, max_edges: int = 500, include_frames: bool = True) -> dict[str, Any]:
        return self._worker(run_id).request("living_explorer_timeline", {"max_frames": max_frames, "max_nodes": max_nodes, "max_edges": max_edges, "include_frames": include_frames})

    def _structure_command(self, run_id: str, action: str, command_type: str, payload: dict[str, Any], *, expected_state_revision: int | None = None) -> dict[str, Any]:
        worker = self._worker(run_id)
        run = self.repository.get_run(run_id)
        envelope = CommandEnvelope(
            command_id=new_id("cmd"), run_id=run_id, organism_id=run.organism_id,
            command_type=command_type, expected_state_revision=expected_state_revision,
        )
        receipt = worker.request(action, {"envelope": envelope.model_dump(mode="json"), **payload})
        self._sync_after_receipt(run_id, receipt)
        return receipt

    def promote_structure(self, run_id: str, candidate_id: str, *, expected_state_revision: int | None = None) -> dict[str, Any]:
        return self._structure_command(run_id, "promote_structure", "PROMOTE_STRUCTURE", {"candidate_id": candidate_id}, expected_state_revision=expected_state_revision)

    def ablate_structure(self, run_id: str, structure_id: str, *, expected_state_revision: int | None = None) -> dict[str, Any]:
        return self._structure_command(run_id, "ablate_structure", "ABLATE_STRUCTURE", {"structure_id": structure_id}, expected_state_revision=expected_state_revision)

    def restore_structure(self, run_id: str, structure_id: str, *, expected_state_revision: int | None = None) -> dict[str, Any]:
        return self._structure_command(run_id, "restore_structure", "RESTORE_STRUCTURE", {"structure_id": structure_id}, expected_state_revision=expected_state_revision)

    def interact_structure(self, run_id: str, structure_id: str, *, expected_state_revision: int | None = None) -> dict[str, Any]:
        return self._structure_command(run_id, "interact_structure", "INTERACT_STRUCTURE", {"structure_id": structure_id}, expected_state_revision=expected_state_revision)

    def observe_hierarchy(self, run_id: str, *, expected_state_revision: int | None = None) -> dict[str, Any]:
        return self._structure_command(run_id, "observe_hierarchy", "OBSERVE_HIERARCHY", {}, expected_state_revision=expected_state_revision)

    def promote_hierarchy(self, run_id: str, candidate_id: str, *, expected_state_revision: int | None = None) -> dict[str, Any]:
        return self._structure_command(run_id, "promote_hierarchy", "PROMOTE_HIERARCHY", {"candidate_id": candidate_id}, expected_state_revision=expected_state_revision)

    def challenge_structure(self, run_id: str, structure_id: str, concept_ids: tuple[str, str], evidence_ref: str, confidence: float, *, expected_state_revision: int | None = None) -> dict[str, Any]:
        return self._structure_command(
            run_id, "challenge_structure", "CHALLENGE_STRUCTURE",
            {"structure_id": structure_id, "concept_ids": list(concept_ids), "evidence_ref": evidence_ref, "confidence": confidence},
            expected_state_revision=expected_state_revision,
        )

    def refold_structure(self, run_id: str, structure_id: str, *, expected_state_revision: int | None = None) -> dict[str, Any]:
        return self._structure_command(run_id, "refold_structure", "REFOLD_STRUCTURE", {"structure_id": structure_id}, expected_state_revision=expected_state_revision)

    def causal_compare_structure(self, run_id: str, structure_id: str, cue_label: str | None = None) -> dict[str, Any]:
        detail = self.forensic_structure_detail(run_id, structure_id)
        if detail.get("kind") != "P":
            raise RunServiceError("Causal P ablation comparison requires a base P structure.")
        if not detail.get("available"):
            raise RunServiceError("Structure must be available before causal comparison.")
        labels = [item.get("display_label") or item.get("label") for item in detail.get("member_concepts", [])]
        labels = [item for item in labels if item]
        if not labels:
            raise RunServiceError("Structure has no resolvable member labels.")
        cue = cue_label or labels[0]
        if cue.lower() not in {item.lower() for item in labels}:
            raise RunServiceError("Cue label is not a member of the selected structure.")
        enabled = self.probe(run_id, ProbeRequest(cue_labels=(cue,)))
        self.ablate_structure(run_id, structure_id)
        try:
            ablated = self.probe(run_id, ProbeRequest(cue_labels=(cue,)))
        finally:
            self.restore_structure(run_id, structure_id)
        restored = self.probe(run_id, ProbeRequest(cue_labels=(cue,)))
        def view(receipt: dict[str, Any]) -> dict[str, Any]:
            report = receipt.get("result", {})
            return {
                "disposition": report.get("disposition"),
                "structure_id": report.get("structure_id"),
                "compression_gain": report.get("compression_gain"),
                "cost": report.get("cost", {}),
                "baseline_cost": report.get("baseline_cost", {}),
                "reconstructed_concept_ids": report.get("reconstructed_concept_ids", []),
                "command_id": receipt.get("command_id"),
                "state_revision_after": receipt.get("state_revision_after"),
            }
        return {
            "structure_id": structure_id,
            "cue_label": cue,
            "with_structure": view(enabled),
            "ablated": view(ablated),
            "restored": view(restored),
            "available_after": self.forensic_structure_detail(run_id, structure_id).get("available"),
        }

    def status(self, run_id: str) -> dict[str, Any]:
        record = self.repository.get_run(run_id)
        worker = self._workers.get(run_id)
        control = self._control(run_id)
        execution = {
            "state": control.state,
            "last_error": control.last_error,
            "active_queue_item_id": control.active_queue_item_id,
            "queue_counts": self.repository.queue_counts(run_id),
        }
        dirty = self._dirty_state(record)
        if worker is not None and worker.alive:
            descriptor = worker.request("descriptor")
            metrics = worker.request("metrics")
            return {"run": record.__dict__, "descriptor": descriptor, "metrics": metrics, "worker_alive": True, "execution": execution, **dirty}
        return {"run": record.__dict__, "descriptor": None, "metrics": None, "worker_alive": False, "execution": execution, **dirty}

    def enqueue_teaching(self, run_id: str, request: TeachingRequest) -> QueueItemRecord:
        self.repository.get_run(run_id)
        item = self.repository.enqueue_command(
            queue_item_id=new_id("qitem"),
            run_id=run_id,
            command_type="TEACH",
            payload=request.model_dump(mode="json"),
        )
        self._emit_control_event(run_id, "RUN_QUEUE_CHANGED", {"action": "enqueued", "queue_item_id": item.queue_item_id, "command_type": item.command_type})
        return item

    def enqueue_experience(self, run_id: str, command: ExperienceCommand) -> QueueItemRecord:
        self.repository.get_run(run_id)
        item = self.repository.enqueue_command(
            queue_item_id=new_id("qitem"),
            run_id=run_id,
            command_type="EXPERIENCE",
            payload=command.model_dump(mode="json"),
        )
        self._emit_control_event(run_id, "RUN_QUEUE_CHANGED", {
            "action": "enqueued",
            "queue_item_id": item.queue_item_id,
            "command_type": item.command_type,
            "experience_event_key": command.event_key,
        })
        return item

    def enqueue_grammar_rule(self, run_id: str, request: GrammarRuleTeachRequest) -> QueueItemRecord:
        self.repository.get_run(run_id)
        item = self.repository.enqueue_command(
            queue_item_id=new_id("qitem"),
            run_id=run_id,
            command_type="GRAMMAR_RULE",
            payload=request.model_dump(mode="json"),
        )
        self._emit_control_event(run_id, "RUN_QUEUE_CHANGED", {
            "action": "enqueued",
            "queue_item_id": item.queue_item_id,
            "command_type": item.command_type,
            "rule_id": request.rule_id,
        })
        return item

    def enqueue_lexeme(self, run_id: str, request: LexemeTeachRequest) -> QueueItemRecord:
        self.repository.get_run(run_id)
        item = self.repository.enqueue_command(
            queue_item_id=new_id("qitem"),
            run_id=run_id,
            command_type="LEXEME",
            payload=request.model_dump(mode="json"),
        )
        self._emit_control_event(run_id, "RUN_QUEUE_CHANGED", {
            "action": "enqueued",
            "queue_item_id": item.queue_item_id,
            "command_type": item.command_type,
            "lemma": request.lemma,
        })
        return item

    def enqueue_probe(self, run_id: str, request: ProbeRequest) -> QueueItemRecord:
        self.repository.get_run(run_id)
        item = self.repository.enqueue_command(
            queue_item_id=new_id("qitem"),
            run_id=run_id,
            command_type="PROBE",
            payload=request.model_dump(mode="json"),
        )
        self._emit_control_event(run_id, "RUN_QUEUE_CHANGED", {"action": "enqueued", "queue_item_id": item.queue_item_id, "command_type": item.command_type})
        return item

    def list_queue(self, run_id: str) -> list[dict[str, Any]]:
        result = []
        for item in self.repository.list_queue(run_id):
            data = item.__dict__.copy()
            data["payload"] = item.payload()
            data["result"] = item.result()
            data.pop("payload_json", None)
            data.pop("result_json", None)
            result.append(data)
        return result

    def execution_status(self, run_id: str) -> dict[str, Any]:
        control = self._control(run_id)
        return {
            "state": control.state,
            "last_error": control.last_error,
            "active_queue_item_id": control.active_queue_item_id,
            "queue_counts": self.repository.queue_counts(run_id),
        }

    def _execute_queue_item(self, run_id: str, item: QueueItemRecord) -> dict[str, Any]:
        claimed = self.repository.mark_queue_running(item.queue_item_id)
        control = self._control(run_id)
        control.active_queue_item_id = claimed.queue_item_id
        self._emit_control_event(run_id, "RUN_QUEUE_CHANGED", {"action": "started", "queue_item_id": claimed.queue_item_id, "command_type": claimed.command_type})
        try:
            if claimed.command_type == "TEACH":
                receipt = self.teach(run_id, TeachingRequest.model_validate(claimed.payload()))
            elif claimed.command_type == "EXPERIENCE":
                receipt = self.submit_experience(run_id, ExperienceCommand.model_validate(claimed.payload()))
            elif claimed.command_type == "PROBE":
                receipt = self.probe(run_id, ProbeRequest.model_validate(claimed.payload()))
            elif claimed.command_type == "GRAMMAR_RULE":
                receipt = self.teach_grammar_rule(run_id, GrammarRuleTeachRequest.model_validate(claimed.payload()))
            elif claimed.command_type == "LEXEME":
                receipt = self.teach_lexeme(run_id, LexemeTeachRequest.model_validate(claimed.payload()))
            else:
                raise RunServiceError(f"Unsupported queued command type: {claimed.command_type}")
            self.repository.mark_queue_completed(claimed.queue_item_id, receipt)
            self._emit_control_event(run_id, "RUN_QUEUE_CHANGED", {"action": "completed", "queue_item_id": claimed.queue_item_id, "command_type": claimed.command_type})
            return receipt
        except Exception as exc:
            self.repository.mark_queue_failed(claimed.queue_item_id, str(exc))
            control.last_error = str(exc)
            self._emit_control_event(run_id, "ERROR", {"scope": "run_queue", "queue_item_id": claimed.queue_item_id, "error": str(exc)})
            raise
        finally:
            control.active_queue_item_id = None

    def step_queue(self, run_id: str) -> dict[str, Any]:
        self._worker(run_id)
        control = self._control(run_id)
        thread = control.thread
        if thread is not None and thread.is_alive():
            raise RunServiceError("Cannot single-step while the run queue is executing.")
        item = self.repository.next_queued(run_id)
        if item is None:
            control.state = "idle"
            return {"executed": False, "reason": "queue_empty", "execution": self.execution_status(run_id)}
        control.state = "stepping"
        try:
            result = self._execute_queue_item(run_id, item)
            control.last_error = None
        finally:
            control.state = "idle"
        return {"executed": True, "queue_item_id": item.queue_item_id, "receipt": result, "execution": self.execution_status(run_id)}

    def start_queue(self, run_id: str) -> dict[str, Any]:
        self._worker(run_id)
        control = self._control(run_id)
        with self._lock:
            if control.thread is not None and control.thread.is_alive():
                return self.execution_status(run_id)
            control.pause_requested.clear()
            control.stop_requested.clear()
            control.last_error = None
            control.state = "running"
            thread = Thread(target=self._queue_loop, args=(run_id,), daemon=True, name=f"verdant-run-{run_id}")
            control.thread = thread
        self._emit_control_event(run_id, "RUN_STARTED", {"reason": "queue_start", "execution_state": "running"})
        thread.start()
        return self.execution_status(run_id)

    def pause_queue(self, run_id: str) -> dict[str, Any]:
        control = self._control(run_id)
        control.pause_requested.set()
        if control.thread is None or not control.thread.is_alive():
            control.state = "paused"
            self._emit_control_event(run_id, "RUN_PAUSED", {"reason": "operator", "execution_state": "paused"})
        return self.execution_status(run_id)

    def stop_queue(self, run_id: str) -> dict[str, Any]:
        control = self._control(run_id)
        control.stop_requested.set()
        if control.thread is None or not control.thread.is_alive():
            control.state = "stopped"
            self._emit_control_event(run_id, "RUN_STOPPED", {"reason": "operator", "execution_state": "stopped"})
        return self.execution_status(run_id)

    def _queue_loop(self, run_id: str) -> None:
        control = self._control(run_id)
        reason = "queue_drained"
        try:
            while True:
                if control.stop_requested.is_set():
                    reason = "operator_stop"
                    control.state = "stopped"
                    break
                if control.pause_requested.is_set():
                    reason = "operator_pause"
                    control.state = "paused"
                    break
                item = self.repository.next_queued(run_id)
                if item is None:
                    control.state = "idle"
                    reason = "queue_drained"
                    break
                try:
                    self._execute_queue_item(run_id, item)
                except Exception:
                    control.state = "paused"
                    reason = "queue_error"
                    break
                time.sleep(0)
        finally:
            control.active_queue_item_id = None
            control.thread = None
            event_type = "RUN_STOPPED" if control.state == "stopped" else "RUN_PAUSED"
            self._emit_control_event(run_id, event_type, {"reason": reason, "execution_state": control.state})

    def grammar_status(self, run_id: str) -> dict[str, Any]:
        return self._worker(run_id).request("grammar_status")

    def grammar_preview(self, run_id: str, request: GrammarPreviewRequest) -> dict[str, Any]:
        return self._worker(run_id).request("grammar_preview", {"request": request.model_dump(mode="json")})

    def _language_mutation(self, run_id: str, action: str, command_type: str, request_model, *, expected_state_revision: int | None = None) -> dict[str, Any]:
        worker = self._worker(run_id)
        run = self.repository.get_run(run_id)
        envelope = CommandEnvelope(
            run_id=run_id, organism_id=run.organism_id, command_type=command_type,
            expected_state_revision=expected_state_revision,
        )
        receipt = worker.request(action, {
            "envelope": envelope.model_dump(mode="json"),
            "request": request_model.model_dump(mode="json"),
        })
        self._sync_after_receipt(run_id, receipt)
        return receipt

    def teach_grammar_rule(self, run_id: str, request: GrammarRuleTeachRequest, *, expected_state_revision: int | None = None) -> dict[str, Any]:
        return self._language_mutation(run_id, "grammar_teach_rule", "TEACH_GRAMMAR_RULE", request, expected_state_revision=expected_state_revision)

    def teach_lexeme(self, run_id: str, request: LexemeTeachRequest, *, expected_state_revision: int | None = None) -> dict[str, Any]:
        return self._language_mutation(run_id, "grammar_teach_lexeme", "TEACH_LEXEME", request, expected_state_revision=expected_state_revision)

    def teach_language_sentence(self, run_id: str, request: LanguageSentenceTeachRequest, *, expected_state_revision: int | None = None) -> dict[str, Any]:
        return self._language_mutation(run_id, "grammar_teach_sentence", "TEACH_LANGUAGE_SENTENCE", request, expected_state_revision=expected_state_revision)

    def _baseline_curriculum_jsonl(self, curriculum_id: str | None) -> str | None:
        if curriculum_id is None:
            return None
        record = self.repository.get_curriculum(curriculum_id)
        path = self.artifacts.resolve(record.artifact_sha256, verify=True)
        package = read_curriculum_package(path)
        return compiled_commands_jsonl(package.compiled_commands)

    def compile_curriculum(self, request: CurriculumCompileRequest) -> dict[str, Any]:
        self.repository.get_project(request.project_id)
        baseline = self._baseline_curriculum_jsonl(request.baseline_curriculum_id)
        return self.curriculum_compiler.compile(request, baseline_jsonl=baseline).model_dump(mode="json", by_alias=True)

    def compile_curriculum_pack(self, request: CurriculumPackCompileRequest) -> dict[str, Any]:
        self.repository.get_project(request.project_id)
        baseline = self._baseline_curriculum_jsonl(request.baseline_curriculum_id)
        pack, _bundle, selected, probes, source = curriculum_pack_bundle_source(
            request.pack_text, request.selected_section_ids
        )
        compile_request = CurriculumCompileRequest(
            project_id=request.project_id,
            title=curriculum_pack_selection_title(pack, selected),
            source_format="teaching_bundle_json",
            source_text=source,
            state_dim=pack.state_dim,
            baseline_curriculum_id=request.baseline_curriculum_id,
        )
        compiled = self.curriculum_compiler.compile(compile_request, baseline_jsonl=baseline)
        return {
            "schema": "verdant.curriculum.pack.compile.v1",
            "pack": {
                "schema": pack.schema_id,
                "title": pack.title,
                "description": pack.description,
                "state_dim": pack.state_dim,
                "section_count": len(pack.sections),
            },
            "selected_sections": [
                {
                    "section_id": section.section_id,
                    "title": section.title,
                    "description": section.description,
                    "item_count": len(section.items),
                    "test_count": len(section.tests),
                }
                for section in selected
            ],
            "tests": [test.model_dump(mode="json") for test in probes],
            "bundle_source_text": source,
            "curriculum": compiled.model_dump(mode="json", by_alias=True),
        }

    def freeze_curriculum_pack(self, request: CurriculumPackFreezeRequest) -> CurriculumRecord:
        prepared = self.compile_curriculum_pack(
            CurriculumPackCompileRequest(
                project_id=request.project_id,
                pack_text=request.pack_text,
                selected_section_ids=request.selected_section_ids,
                baseline_curriculum_id=request.baseline_curriculum_id,
            )
        )
        compiled = prepared["curriculum"]
        freeze_request = CurriculumFreezeRequest(
            project_id=request.project_id,
            title=compiled["title"],
            source_format="teaching_bundle_json",
            source_text=prepared["bundle_source_text"],
            state_dim=int(compiled["state_dim"]),
            baseline_curriculum_id=request.baseline_curriculum_id,
            expected_compiled_sha256=request.expected_compiled_sha256,
        )
        return self.freeze_curriculum(freeze_request)

    def freeze_curriculum(self, request: CurriculumFreezeRequest) -> CurriculumRecord:
        self.repository.get_project(request.project_id)
        baseline = self._baseline_curriculum_jsonl(request.baseline_curriculum_id)
        compiled = self.curriculum_compiler.compile(request, baseline_jsonl=baseline)
        if request.expected_compiled_sha256 is not None and request.expected_compiled_sha256 != compiled.compiled_sha256:
            raise RunServiceError(
                f"Compiled curriculum changed since review: expected {request.expected_compiled_sha256}, got {compiled.compiled_sha256}."
            )
        package_bytes = build_curriculum_package(compiled)
        temp_path = self.artifacts.tmp / f"{new_id('vcurr')}.vcurr"
        temp_path.write_bytes(package_bytes)
        try:
            stored = self.artifacts.ingest_file(temp_path, media_type=CURRICULUM_PACKAGE_MEDIA_TYPE)
        finally:
            temp_path.unlink(missing_ok=True)
        version = self.repository.next_curriculum_version(request.project_id, compiled.title)
        record = CurriculumRecord(
            curriculum_id=new_id("vcurr"),
            project_id=request.project_id,
            title=compiled.title,
            version=version,
            source_format=compiled.source_format,
            source_sha256=compiled.source_sha256,
            compiled_sha256=compiled.compiled_sha256,
            artifact_sha256=stored.sha256,
            artifact_size_bytes=stored.size_bytes,
            item_count=compiled.item_count,
            state_dim=compiled.state_dim,
            compiler_version=CURRICULUM_COMPILER_VERSION,
            created_at=utc_now_iso(),
        )
        return self.repository.add_curriculum(record)

    def curriculum_detail(self, curriculum_id: str) -> dict[str, Any]:
        record = self.repository.get_curriculum(curriculum_id)
        path = self.artifacts.resolve(record.artifact_sha256, verify=True)
        package = read_curriculum_package(path)
        return {
            "record": record.__dict__,
            "manifest": package.manifest,
            "source_text": package.source_text,
            "curriculum_ir": package.curriculum_ir,
            "compiled_commands": [item.model_dump(mode="json") for item in package.compiled_commands],
            "language_scaffold": package.language_scaffold,
            "hashes": package.hashes,
        }

    def queue_curriculum(self, run_id: str, curriculum_id: str) -> dict[str, Any]:
        run = self.repository.get_run(run_id)
        record = self.repository.get_curriculum(curriculum_id)
        if run.project_id != record.project_id:
            raise RunServiceError("Curriculum and run belong to different Workbench projects.")
        if record.state_dim != self.repository.get_organism(run.organism_id).state_dim:
            raise RunServiceError(
                f"Curriculum state_dim {record.state_dim} does not match organism state_dim {self.repository.get_organism(run.organism_id).state_dim}."
            )
        path = self.artifacts.resolve(record.artifact_sha256, verify=True)
        package = read_curriculum_package(path)
        queue_ids: list[str] = []
        scaffold_ids: list[str] = []
        scaffold = package.language_scaffold or {}
        for rule_id in scaffold.get("grammar_rules", []):
            item = self.enqueue_grammar_rule(run_id, GrammarRuleTeachRequest(rule_id=str(rule_id)))
            queue_ids.append(item.queue_item_id)
            scaffold_ids.append(item.queue_item_id)
        for lexeme in scaffold.get("lexicon", []):
            request = LexemeTeachRequest.model_validate(lexeme)
            item = self.enqueue_lexeme(run_id, request)
            queue_ids.append(item.queue_item_id)
            scaffold_ids.append(item.queue_item_id)
        experience_ids = [self.enqueue_experience(run_id, command).queue_item_id for command in package.compiled_commands]
        queue_ids.extend(experience_ids)
        self._emit_control_event(run_id, "CURRICULUM_QUEUED", {
            "curriculum_id": curriculum_id,
            "compiled_sha256": record.compiled_sha256,
            "item_count": len(queue_ids),
            "scaffold_item_count": len(scaffold_ids),
            "experience_item_count": len(experience_ids),
            "queue_item_ids": queue_ids,
        })
        return {
            "curriculum_id": curriculum_id,
            "compiled_sha256": record.compiled_sha256,
            "item_count": len(queue_ids),
            "scaffold_item_count": len(scaffold_ids),
            "experience_item_count": len(experience_ids),
            "queue_item_ids": queue_ids,
        }

    # ------------------------------------------------------------------
    # WB-08 provider connections

    def list_providers(self) -> list[dict[str, Any]]:
        return [item.model_dump(mode="json") for item in self.providers.list_configs()]

    def save_provider(self, config: ProviderConfiguration) -> dict[str, Any]:
        return self.providers.save_config(config).model_dump(mode="json")

    def _persist_provider_capture(self, capture: ProviderCapture) -> dict[str, Any]:
        package_bytes = build_provider_capture_package(capture)
        temp_path = self.artifacts.tmp / f"{capture.capture_id}.vpcap"
        temp_path.write_bytes(package_bytes)
        try:
            stored = self.artifacts.ingest_file(temp_path, media_type=PROVIDER_CAPTURE_MEDIA_TYPE)
        finally:
            temp_path.unlink(missing_ok=True)
        record = self.providers.register_capture_artifact(capture, stored.sha256, stored.size_bytes)
        return {**record, "capture": capture.model_dump(mode="json")}

    def capture_provider_paste(self, provider_id: str, request: ProviderProposalRequest, raw_response: str) -> dict[str, Any]:
        capture = self.providers.capture_paste(provider_id, request, raw_response)
        return self._persist_provider_capture(capture)

    def call_provider(self, provider_id: str, request: ProviderProposalRequest) -> dict[str, Any]:
        capture = self.providers.propose_http(provider_id, request)
        return self._persist_provider_capture(capture)

    def list_provider_captures(self) -> list[dict[str, Any]]:
        return self.providers.list_capture_index()

    def provider_capture_detail(self, capture_id: str) -> dict[str, Any]:
        record = next((item for item in self.providers.list_capture_index() if item["capture_id"] == capture_id), None)
        if record is None:
            raise KeyError(capture_id)
        path = self.artifacts.resolve(record["artifact_sha256"], verify=True)
        capture = read_provider_capture_package(path)
        return {"record": record, "capture": capture.model_dump(mode="json", by_alias=True)}

    def provider_capture_curriculum_source(self, capture_id: str) -> dict[str, Any]:
        detail = self.provider_capture_detail(capture_id)
        capture = ProviderCapture.model_validate(detail["capture"])
        if capture.parsed_teaching_bundle is None:
            raise RunServiceError("Provider capture does not contain a valid editable teaching bundle.")
        source = json.dumps(capture.parsed_teaching_bundle, indent=2, sort_keys=True) + "\n"
        return {
            "capture_id": capture_id,
            "source_format": "teaching_bundle_json",
            "source_text": source,
            "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "provider_id": capture.provider_id,
            "response_sha256": capture.response_sha256,
        }

    # ------------------------------------------------------------------
    # WB-09 plugins / hardening

    def list_plugins(self) -> list[dict[str, Any]]:
        return self.plugins.list_plugins()

    def invoke_metric_plugin(self, plugin_id: str, run_id: str) -> dict[str, Any]:
        metrics = self.metrics(run_id)
        result = self.plugins.invoke(plugin_id, {"run_id": run_id, "metrics": metrics}, required_kind="metric")
        return result.model_dump(mode="json")

    def integrity_scan(self) -> dict[str, Any]:
        checkpoint_rows = []
        for run in self.repository.list_runs():
            for cp in self.repository.list_checkpoints(run.run_id):
                checkpoint_rows.append({"checkpoint_id": cp.checkpoint_id, "artifact_sha256": cp.artifact_sha256, "ok": self.artifacts.verify(cp.artifact_sha256)})
        curriculum_rows = [{"curriculum_id": c.curriculum_id, "artifact_sha256": c.artifact_sha256, "ok": self.artifacts.verify(c.artifact_sha256)} for c in self.repository.list_curricula()]
        experiment_rows = [{"experiment_id": e.experiment_id, "artifact_sha256": e.artifact_sha256, "ok": self.artifacts.verify(e.artifact_sha256)} for e in self.repository.list_experiments()]
        provider_rows = [{"capture_id": c["capture_id"], "artifact_sha256": c["artifact_sha256"], "ok": self.artifacts.verify(c["artifact_sha256"])} for c in self.providers.list_capture_index()]
        rows = checkpoint_rows + curriculum_rows + experiment_rows + provider_rows
        return {
            "schema": "verdant.workbench.integrity.v1",
            "artifact_count": len(rows),
            "all_ok": all(row["ok"] for row in rows),
            "checkpoints": checkpoint_rows,
            "curricula": curriculum_rows,
            "experiments": experiment_rows,
            "provider_captures": provider_rows,
        }

    # ------------------------------------------------------------------
    # WB-07 experiment manager

    def experiment_template(self, project_id: str) -> dict[str, Any]:
        self.repository.get_project(project_id)
        request = ExperimentAuthorRequest(project_id=project_id)
        config = BenchmarkConfig(
            seed=request.seed, state_dim=request.state_dim, repeats_per_edge=request.repeats_per_edge,
            noise_concepts=request.noise_concepts, noise_repeats=request.noise_repeats, relation_type=request.relation_type,
        )
        harness = EthomorphismBenchmarkHarness(config)
        return {
            "schema": "verdant.workbench.experiment-template.v1",
            "protocol_id": EXPERIMENT_PROTOCOL_ETHOMORPHISM,
            "title": request.title,
            "config": asdict(config),
            "arms": [arm.value for arm in ArmName],
            "curriculum_sha256": harness.curriculum_sha256(),
            "curriculum_event_count": len(harness.curriculum_commands()),
            "expected_assertions": [item.model_dump(mode="json") for item in default_assertions()],
        }

    def freeze_experiment(self, request: ExperimentAuthorRequest) -> ExperimentRecord:
        self.repository.get_project(request.project_id)
        if request.protocol_id != EXPERIMENT_PROTOCOL_ETHOMORPHISM:
            raise RunServiceError(f"Unsupported experiment protocol {request.protocol_id}")
        if request.parent_experiment_id is not None:
            parent = self.repository.get_experiment(request.parent_experiment_id)
            if parent.project_id != request.project_id:
                raise RunServiceError("Parent experiment belongs to a different project.")
        version = self.repository.next_experiment_version(request.project_id, request.title)
        experiment_id = new_id("vexp")
        config = BenchmarkConfig(
            seed=request.seed, state_dim=request.state_dim, repeats_per_edge=request.repeats_per_edge,
            noise_concepts=request.noise_concepts, noise_repeats=request.noise_repeats, relation_type=request.relation_type,
        )
        harness = EthomorphismBenchmarkHarness(config)
        assertions = request.expected_assertions or default_assertions()
        build_identity = source_build_identity()
        manifest = ExperimentManifest(
            experiment_id=experiment_id, project_id=request.project_id, title=request.title, version=version,
            created_at=utc_now_iso(), parent_experiment_id=request.parent_experiment_id,
            release_id=build_identity["release_id"],
            engine_source_sha256=build_identity["engine_source_sha256"],
            workbench_source_sha256=build_identity["workbench_source_sha256"],
            dependency_lock_sha256=build_identity["dependency_lock_sha256"],
            protocol_config=asdict(config), curriculum_sha256=harness.curriculum_sha256(),
            curriculum_event_count=len(harness.curriculum_commands()),
            resource_lock={
                "same_seed_all_arms": True, "seed": config.seed, "state_dim": config.state_dim,
                "relation_type": config.relation_type, "ordered_curriculum_locked": True,
            },
            metrics=default_metrics(), interventions=default_interventions(),
            expected_assertions=tuple(assertions),
        )
        package_bytes = build_experiment_package(manifest)
        temp_path = self.artifacts.tmp / f"{experiment_id}.vexp"
        temp_path.write_bytes(package_bytes)
        try:
            stored = self.artifacts.ingest_file(temp_path, media_type=EXPERIMENT_PACKAGE_MEDIA_TYPE)
        finally:
            temp_path.unlink(missing_ok=True)
        record = ExperimentRecord(
            experiment_id=experiment_id, project_id=request.project_id, title=request.title, version=version,
            protocol_id=request.protocol_id, manifest_sha256=sha256_bytes(json.dumps(manifest.model_dump(mode="json", by_alias=True), sort_keys=True, separators=(",", ":")).encode("utf-8")),
            artifact_sha256=stored.sha256, artifact_size_bytes=stored.size_bytes,
            parent_experiment_id=request.parent_experiment_id, created_at=manifest.created_at,
        )
        return self.repository.add_experiment(record)

    def experiment_detail(self, experiment_id: str) -> dict[str, Any]:
        record = self.repository.get_experiment(experiment_id)
        package_path = self.artifacts.resolve(record.artifact_sha256, verify=True)
        manifest, package = read_experiment_package(package_path)
        return {
            "record": record.__dict__,
            "manifest": manifest.model_dump(mode="json", by_alias=True),
            "package_hashes": package["hashes"],
            "runs": [item.__dict__ for item in self.repository.list_experiment_runs(experiment_id)],
        }

    def fork_experiment(self, experiment_id: str, request: ExperimentForkRequest) -> ExperimentRecord:
        detail = self.experiment_detail(experiment_id)
        manifest = ExperimentManifest.model_validate(detail["manifest"])
        cfg = dict(manifest.protocol_config)
        for key in ("seed", "state_dim", "repeats_per_edge", "noise_concepts", "noise_repeats", "relation_type"):
            value = getattr(request, key)
            if value is not None:
                cfg[key] = value
        assertions = manifest.expected_assertions if request.keep_expected_assertions else default_assertions()
        return self.freeze_experiment(ExperimentAuthorRequest(
            project_id=manifest.project_id,
            title=request.title or f"{manifest.title} Fork",
            seed=int(cfg["seed"]), state_dim=int(cfg["state_dim"]), repeats_per_edge=int(cfg["repeats_per_edge"]),
            noise_concepts=int(cfg["noise_concepts"]), noise_repeats=int(cfg["noise_repeats"]), relation_type=str(cfg["relation_type"]),
            expected_assertions=tuple(assertions), parent_experiment_id=experiment_id,
        ))

    def _execute_experiment_run(self, experiment_run_id: str) -> None:
        record = self.repository.get_experiment_run(experiment_run_id)
        experiment = self.repository.get_experiment(record.experiment_id)
        try:
            package_path = self.artifacts.resolve(experiment.artifact_sha256, verify=True)
            manifest, _ = read_experiment_package(package_path)
            _assert_manifest_build_identity(manifest)
            result = run_ethomorphism_isolated(config_from_manifest(manifest))
            assertions = evaluate_assertions(result["summary"], manifest.expected_assertions)
            verification = {
                "schema": "verdant.experiment.verification.v1",
                "experiment_id": experiment.experiment_id,
                "experiment_run_id": experiment_run_id,
                "created_at": utc_now_iso(),
                "source_experiment_sha256": experiment.artifact_sha256,
                "scientific_result_sha256": result["scientific_result_sha256"],
                "assertions_passed": sum(1 for item in assertions if item["passed"]),
                "assertions_total": len(assertions),
                "all_assertions_pass": all(item["passed"] for item in assertions),
                "reproduction_match": None,
            }
            verification_bytes = build_verification_package(
                package_path, result_payload=result, assertion_results=assertions, verification=verification
            )
            tmp = self.artifacts.tmp / f"{experiment_run_id}-verification.vexp"
            tmp.write_bytes(verification_bytes)
            try:
                stored = self.artifacts.ingest_file(tmp, media_type=EXPERIMENT_PACKAGE_MEDIA_TYPE)
            finally:
                tmp.unlink(missing_ok=True)
            self.repository.update_experiment_run(
                experiment_run_id, status="completed", completed_at=utc_now_iso(),
                result_artifact_sha256=stored.sha256, result_artifact_size_bytes=stored.size_bytes,
                scientific_result_sha256=result["scientific_result_sha256"],
                assertions_passed=verification["assertions_passed"], assertions_total=verification["assertions_total"],
                verified=0, error_message=None,
            )
        except Exception as exc:
            self.repository.update_experiment_run(
                experiment_run_id, status="failed", completed_at=utc_now_iso(), error_message=str(exc)
            )
        finally:
            with self._lock:
                self._experiment_threads.pop(experiment_run_id, None)

    def start_experiment(self, experiment_id: str) -> ExperimentRunRecord:
        experiment = self.repository.get_experiment(experiment_id)
        # Integrity/readability is checked before accepting the run.
        read_experiment_package(self.artifacts.resolve(experiment.artifact_sha256, verify=True))
        run_record = ExperimentRunRecord(
            experiment_run_id=new_id("xrun"), experiment_id=experiment_id, status="running", started_at=utc_now_iso(),
            completed_at=None, result_artifact_sha256=None, result_artifact_size_bytes=None, scientific_result_sha256=None,
            assertions_passed=0, assertions_total=0, verified=0, error_message=None,
        )
        self.repository.add_experiment_run(run_record)
        thread = Thread(target=self._execute_experiment_run, args=(run_record.experiment_run_id,), daemon=True, name=f"experiment-{run_record.experiment_run_id}")
        with self._lock:
            self._experiment_threads[run_record.experiment_run_id] = thread
        thread.start()
        return self.repository.get_experiment_run(run_record.experiment_run_id)

    def wait_experiment_run(self, experiment_run_id: str, timeout: float = 300.0) -> ExperimentRunRecord:
        with self._lock:
            thread = self._experiment_threads.get(experiment_run_id)
        if thread is not None:
            thread.join(timeout=timeout)
        return self.repository.get_experiment_run(experiment_run_id)

    def experiment_run_detail(self, experiment_run_id: str) -> dict[str, Any]:
        record = self.repository.get_experiment_run(experiment_run_id)
        payload: dict[str, Any] = {"record": record.__dict__}
        if record.result_artifact_sha256 is not None:
            path = self.artifacts.resolve(record.result_artifact_sha256, verify=True)
            payload.update(read_verification_package(path))
        return payload

    def verify_experiment_run(self, experiment_run_id: str) -> dict[str, Any]:
        existing = self.repository.get_experiment_run(experiment_run_id)
        if existing.status != "completed" or existing.scientific_result_sha256 is None:
            raise RunServiceError("Only a completed experiment run can be verified by reproduction.")
        experiment = self.repository.get_experiment(existing.experiment_id)
        package_path = self.artifacts.resolve(experiment.artifact_sha256, verify=True)
        manifest, _ = read_experiment_package(package_path)
        _assert_manifest_build_identity(manifest)
        reproduction = run_ethomorphism_isolated(config_from_manifest(manifest))
        assertion_results = evaluate_assertions(reproduction["summary"], manifest.expected_assertions)
        match = reproduction["scientific_result_sha256"] == existing.scientific_result_sha256
        verified = bool(match and all(item["passed"] for item in assertion_results))
        updated = self.repository.update_experiment_run(experiment_run_id, verified=1 if verified else 0)
        return {
            "schema": "verdant.experiment.reproduction.v1",
            "experiment_run": updated.__dict__,
            "original_scientific_result_sha256": existing.scientific_result_sha256,
            "reproduced_scientific_result_sha256": reproduction["scientific_result_sha256"],
            "reproduction_match": match,
            "assertions": assertion_results,
            "verified": verified,
            "worker_isolation": reproduction["worker_isolation"],
        }

    def experiment_artifact_path(self, experiment_id: str) -> Path:
        record = self.repository.get_experiment(experiment_id)
        return self.artifacts.resolve(record.artifact_sha256, verify=True)

    def experiment_run_artifact_path(self, experiment_run_id: str) -> Path:
        record = self.repository.get_experiment_run(experiment_run_id)
        if record.result_artifact_sha256 is None:
            raise RunServiceError("Experiment run has no verification artifact yet.")
        return self.artifacts.resolve(record.result_artifact_sha256, verify=True)

    def editable_teaching_template(self) -> dict[str, Any]:
        template = {
            "schema": "verdant.teaching.bundle.v1",
            "language_scaffold": {
                "grammar_rules": ["transitive_svo"],
                "lexicon": [
                    {"lemma": "the", "category": "determiner", "forms": ["the"], "attributes": {}},
                    {"lemma": "move", "category": "verb", "forms": ["move", "moves", "moved"], "attributes": {}},
                ],
                "notes": "Optional parser scaffold. Remove or edit anything you do not want taught.",
            },
            "items": [
                {
                    "item_id": "lesson-001",
                    "context_id": "motion-lesson",
                    "source_text": "The kren moves toward the tar.",
                    "concepts": [
                        {"label": "kren", "attributes": {"kind": "entity"}},
                        {"label": "tar", "attributes": {"kind": "entity"}},
                    ],
                    "relations": [
                        {
                            "source": "kren",
                            "relation": "moves_toward",
                            "target": "tar",
                            "directed": True,
                            "weight": 0.8,
                            "confidence": 1.0,
                        }
                    ],
                    "claims": [],
                    "confidence": 1.0,
                    "provenance": {"author": "human", "note": "Everything in this record is editable."},
                    "grammar_annotation": {
                        "subject": "kren",
                        "predicate": "move",
                        "relation": "toward",
                        "object": "tar",
                    },
                    "lexicon_annotation": [
                        {"surface": "kren", "role": "noun"},
                        {"surface": "moves", "lemma": "move", "role": "verb"},
                        {"surface": "toward", "role": "relation"},
                        {"surface": "tar", "role": "noun"},
                    ],
                }
            ],
            "notes": "Workbench does not infer truth or semantics from source_text. Concepts, relations and claims are the explicit teaching plan.",
        }
        return {
            "title": "Editable Teaching Record",
            "source_format": "teaching_bundle_json",
            "state_dim": 128,
            "source_text": __import__("json").dumps(template, indent=2, ensure_ascii=False),
        }

    def m19_curriculum_template(self) -> dict[str, Any]:
        harness = EthomorphismBenchmarkHarness()
        commands = harness.curriculum_commands()
        source = compiled_commands_jsonl(commands)
        return {
            "title": "M19 Alien Worlds Reference Curriculum",
            "source_format": "experience_jsonl",
            "state_dim": harness.config.state_dim,
            "source_text": source,
            "item_count": len(commands),
            "compiled_sha256": harness.curriculum_sha256(),
        }

    def snapshot(self, run_id: str, *, scope: str = "summary") -> dict[str, Any]:
        return self._worker(run_id).request("snapshot", {"scope": scope})

    def metrics(self, run_id: str) -> dict[str, Any]:
        return self._worker(run_id).request("metrics")

    def save_checkpoint(self, run_id: str, *, label: str | None = None, checkpoint_id: str | None = None) -> CheckpointRecord:
        worker = self._worker(run_id)
        run = self.repository.get_run(run_id)
        temp_dir = self.root / "artifacts" / "tmp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_id = checkpoint_id or new_id("ckpt")
        temp_path = temp_dir / f"{checkpoint_id}.vdk"
        descriptor = worker.request("save", {"path": str(temp_path)})
        stored = self.artifacts.ingest_file(
            temp_path,
            media_type="application/vnd.verdant.checkpoint",
            expected_sha256=descriptor["checkpoint_sha256"],
        )
        temp_path.unlink(missing_ok=True)
        parent_checkpoint_id = run.head_checkpoint_id
        record = CheckpointRecord(
            checkpoint_id=checkpoint_id,
            run_id=run_id,
            organism_id=run.organism_id,
            artifact_sha256=stored.sha256,
            artifact_size_bytes=stored.size_bytes,
            canonical_fingerprint=descriptor["canonical_fingerprint"],
            state_revision=int(descriptor["state_revision"]),
            cycle=int(descriptor["cycle"]),
            created_at=utc_now_iso(),
            parent_checkpoint_id=parent_checkpoint_id,
            label=label,
        )
        self.repository.add_checkpoint(record)
        self.repository.update_run_head(
            run_id,
            state_revision=record.state_revision,
            cycle=record.cycle,
            fingerprint=record.canonical_fingerprint,
            status="active",
            head_checkpoint_id=record.checkpoint_id,
        )
        self._emit_control_event(run_id, "CHECKPOINT_SAVED", {
            "checkpoint_id": record.checkpoint_id,
            "artifact_sha256": record.artifact_sha256,
            "canonical_fingerprint": record.canonical_fingerprint,
            "label": record.label,
        })
        return record

    def verify_checkpoint(self, checkpoint_id: str) -> CheckpointRecord:
        record = self.repository.get_checkpoint(checkpoint_id)
        self.artifacts.resolve(record.artifact_sha256, verify=True)
        return record

    def close_run(self, run_id: str) -> RunRecord:
        control = self._control(run_id)
        control.stop_requested.set()
        thread = control.thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=10.0)
        with self._lock:
            worker = self._workers.pop(run_id, None)
        if worker is not None:
            worker.close()
        control.state = "closed"
        return self.repository.set_run_status(run_id, "closed")

    def reopen_run(self, run_id: str, *, checkpoint_id: str | None = None) -> dict[str, Any]:
        run = self.repository.get_run(run_id)
        if run_id in self._workers and self._workers[run_id].alive:
            return self._workers[run_id].request("descriptor")
        target_id = checkpoint_id or run.head_checkpoint_id
        if target_id is None:
            raise RunServiceError("Cannot reopen an inactive run that has no checkpoint.")
        checkpoint = self.verify_checkpoint(target_id)
        if checkpoint.run_id != run_id:
            raise RunServiceError("Checkpoint does not belong to the requested run.")
        checkpoint_is_older_than_head = (
            checkpoint.state_revision < run.latest_state_revision
            or checkpoint.cycle < run.latest_cycle
            or (
                bool(run.latest_fingerprint)
                and checkpoint.canonical_fingerprint != run.latest_fingerprint
            )
        )
        if checkpoint_is_older_than_head:
            descriptor = self.branch_from_checkpoint(target_id)
            return {
                **descriptor,
                "auto_forked": True,
                "auto_forked_from_run_id": run_id,
                "resumed_from_checkpoint_id": target_id,
            }
        path = self.artifacts.resolve(checkpoint.artifact_sha256, verify=True)
        worker = EngineWorkerSupervisor.load(path, run_id=run_id, organism_id=run.organism_id)
        descriptor = worker.request("descriptor")
        if descriptor["fingerprint"] != checkpoint.canonical_fingerprint:
            worker.close()
            raise ArtifactIntegrityError("Loaded checkpoint canonical fingerprint does not match checkpoint metadata.")
        with self._lock:
            self._workers[run_id] = worker
            self._execution[run_id] = RunExecutionControl()
        self.repository.requeue_running_items(run_id)
        self.repository.update_run_head(
            run_id,
            state_revision=descriptor["state_revision"],
            cycle=descriptor["cycle"],
            fingerprint=descriptor["fingerprint"],
            status="active",
            head_checkpoint_id=target_id,
        )
        return {
            **descriptor,
            "auto_forked": False,
            "resumed_from_checkpoint_id": target_id,
        }

    def branch_from_checkpoint(self, checkpoint_id: str, *, new_run_id: str | None = None) -> dict[str, Any]:
        checkpoint = self.verify_checkpoint(checkpoint_id)
        parent_run = self.repository.get_run(checkpoint.run_id)
        new_run_id = new_run_id or new_id("run")
        path = self.artifacts.resolve(checkpoint.artifact_sha256, verify=True)
        worker = EngineWorkerSupervisor.load(path, run_id=new_run_id, organism_id=parent_run.organism_id)
        descriptor = worker.request("descriptor")
        if descriptor["fingerprint"] != checkpoint.canonical_fingerprint:
            worker.close()
            raise ArtifactIntegrityError("Branch loaded checkpoint fingerprint mismatch.")
        self.repository.create_run(
            run_id=new_run_id,
            project_id=parent_run.project_id,
            organism_id=parent_run.organism_id,
            status="active",
            latest_state_revision=descriptor["state_revision"],
            latest_cycle=descriptor["cycle"],
            latest_fingerprint=descriptor["fingerprint"],
            parent_run_id=parent_run.run_id,
            parent_checkpoint_id=checkpoint.checkpoint_id,
            head_checkpoint_id=checkpoint.checkpoint_id,
        )
        with self._lock:
            self._workers[new_run_id] = worker
            self._execution[new_run_id] = RunExecutionControl()
        self._emit_control_event(new_run_id, "RUN_STARTED", {"reason": "branch_created", "parent_run_id": parent_run.run_id, "parent_checkpoint_id": checkpoint.checkpoint_id, "execution_state": "idle"})
        return descriptor

    def ancestry(self, run_id: str) -> list[dict[str, Any]]:
        return [item.__dict__ for item in self.repository.ancestry(run_id)]

    def checkpoint_path(self, checkpoint_id: str) -> Path:
        checkpoint = self.verify_checkpoint(checkpoint_id)
        return self.artifacts.resolve(checkpoint.artifact_sha256, verify=True)
