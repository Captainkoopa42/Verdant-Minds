from __future__ import annotations

import multiprocessing as mp
import traceback
from pathlib import Path
from threading import Lock
from typing import Any

from .adapter import VerdantEngineAdapter
from .models import (
    CommandEnvelope,
    GrammarPreviewRequest,
    GrammarRuleTeachRequest,
    LanguageSentenceTeachRequest,
    LexemeTeachRequest,
    OrganismConfig,
    ProbeRequest,
    SnapshotScope,
    TeachingRequest,
    WorkerRequest,
    WorkerResponse,
)
from verdant_kernel import ExperienceCommand


def _worker_main(connection, initial: dict[str, Any]) -> None:
    adapter: VerdantEngineAdapter | None = None
    try:
        if initial["mode"] == "create":
            adapter = VerdantEngineAdapter.create(
                OrganismConfig.model_validate(initial["config"]),
                run_id=initial["run_id"], organism_id=initial["organism_id"],
            )
        elif initial["mode"] == "load":
            adapter = VerdantEngineAdapter.load(
                initial["checkpoint_path"], run_id=initial["run_id"], organism_id=initial["organism_id"],
            )
        else:
            raise ValueError("Unknown worker initialization mode.")

        while True:
            raw = connection.recv()
            request = WorkerRequest.model_validate(raw)
            if request.action == "shutdown":
                connection.send(WorkerResponse(request_id=request.request_id, ok=True, payload={"shutdown": True}).model_dump(mode="json"))
                break
            try:
                payload = _dispatch(adapter, request)
                response = WorkerResponse(request_id=request.request_id, ok=True, payload=payload)
            except Exception as exc:  # worker boundary intentionally serializes failures
                response = WorkerResponse(
                    request_id=request.request_id,
                    ok=False,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                    payload={"traceback": traceback.format_exc()},
                )
            connection.send(response.model_dump(mode="json"))
    except EOFError:
        pass
    finally:
        connection.close()


def _dispatch(adapter: VerdantEngineAdapter, request: WorkerRequest) -> dict[str, Any]:
    action = request.action
    payload = request.payload
    if action == "descriptor":
        return adapter.descriptor().model_dump(mode="json")
    if action == "metrics":
        return adapter.metrics()
    if action == "snapshot":
        return adapter.snapshot(SnapshotScope(payload.get("scope", "summary"))).model_dump(mode="json")
    if action == "teach":
        envelope = CommandEnvelope.model_validate(payload["envelope"])
        teaching = TeachingRequest.model_validate(payload["request"])
        return adapter.submit_teaching(envelope, teaching).model_dump(mode="json")
    if action == "experience":
        envelope = CommandEnvelope.model_validate(payload["envelope"])
        command = ExperienceCommand.model_validate(payload["command"])
        return adapter.submit_experience(envelope, command).model_dump(mode="json")
    if action == "grammar_status":
        return adapter.grammar_status()
    if action == "grammar_preview":
        return adapter.grammar_preview(GrammarPreviewRequest.model_validate(payload["request"]))
    if action == "grammar_teach_rule":
        envelope = CommandEnvelope.model_validate(payload["envelope"])
        request_model = GrammarRuleTeachRequest.model_validate(payload["request"])
        return adapter.teach_grammar_rule(envelope, request_model).model_dump(mode="json")
    if action == "grammar_teach_lexeme":
        envelope = CommandEnvelope.model_validate(payload["envelope"])
        request_model = LexemeTeachRequest.model_validate(payload["request"])
        return adapter.teach_lexeme(envelope, request_model).model_dump(mode="json")
    if action == "grammar_teach_sentence":
        envelope = CommandEnvelope.model_validate(payload["envelope"])
        request_model = LanguageSentenceTeachRequest.model_validate(payload["request"])
        return adapter.teach_language_sentence(envelope, request_model).model_dump(mode="json")
    if action == "probe":
        envelope = CommandEnvelope.model_validate(payload["envelope"])
        probe = ProbeRequest.model_validate(payload["request"])
        return adapter.probe(envelope, probe).model_dump(mode="json")
    if action == "forensic_list_structures":
        return adapter.forensic_list_structures()
    if action == "forensic_structure_detail":
        return adapter.forensic_structure_detail(str(payload["structure_id"]))
    if action == "forensic_structure_replay":
        return adapter.forensic_structure_replay(str(payload["structure_id"]))
    if action == "forensic_structure_graph":
        return adapter.forensic_structure_graph(str(payload["structure_id"]))
    if action == "living_explorer_frame":
        return adapter.living_explorer_frame(
            None if payload.get("cycle") is None else int(payload["cycle"]),
            max_nodes=int(payload.get("max_nodes", 240)),
            max_edges=int(payload.get("max_edges", 500)),
        )
    if action == "living_explorer_timeline":
        return adapter.living_explorer_timeline(
            max_frames=int(payload.get("max_frames", 240)),
            max_nodes=int(payload.get("max_nodes", 240)),
            max_edges=int(payload.get("max_edges", 500)),
            include_frames=bool(payload.get("include_frames", True)),
        )
    if action == "promote_structure":
        envelope = CommandEnvelope.model_validate(payload["envelope"])
        return adapter.promote_structure(envelope, str(payload["candidate_id"])).model_dump(mode="json")
    if action == "ablate_structure":
        envelope = CommandEnvelope.model_validate(payload["envelope"])
        return adapter.ablate_structure(envelope, str(payload["structure_id"])).model_dump(mode="json")
    if action == "restore_structure":
        envelope = CommandEnvelope.model_validate(payload["envelope"])
        return adapter.restore_structure(envelope, str(payload["structure_id"])).model_dump(mode="json")
    if action == "interact_structure":
        envelope = CommandEnvelope.model_validate(payload["envelope"])
        return adapter.interact(envelope, str(payload["structure_id"])).model_dump(mode="json")
    if action == "observe_hierarchy":
        envelope = CommandEnvelope.model_validate(payload["envelope"])
        return adapter.observe_hierarchy(envelope).model_dump(mode="json")
    if action == "promote_hierarchy":
        envelope = CommandEnvelope.model_validate(payload["envelope"])
        return adapter.promote_hierarchy(envelope, str(payload["candidate_id"])).model_dump(mode="json")
    if action == "challenge_structure":
        envelope = CommandEnvelope.model_validate(payload["envelope"])
        concept_ids = tuple(sorted((str(payload["concept_ids"][0]), str(payload["concept_ids"][1]))))
        return adapter.challenge(
            envelope, structure_id=str(payload["structure_id"]), concept_ids=concept_ids,
            confidence=float(payload["confidence"]), evidence_ref=str(payload["evidence_ref"]),
        ).model_dump(mode="json")
    if action == "refold_structure":
        envelope = CommandEnvelope.model_validate(payload["envelope"])
        return adapter.refold(envelope, str(payload["structure_id"])).model_dump(mode="json")
    if action == "save":
        return adapter.save(Path(payload["path"])).model_dump(mode="json")
    raise ValueError(f"Unsupported worker action: {action}")


class EngineWorkerSupervisor:
    """Supervises one isolated Verdant organism process."""

    def __init__(self, process: mp.Process, connection, *, run_id: str, organism_id: str) -> None:
        self._process = process
        self._connection = connection
        self._lock = Lock()
        self.run_id = run_id
        self.organism_id = organism_id

    @classmethod
    def create(cls, config: OrganismConfig, *, run_id: str, organism_id: str) -> "EngineWorkerSupervisor":
        return cls._spawn({
            "mode": "create", "config": config.model_dump(mode="json"),
            "run_id": run_id, "organism_id": organism_id,
        }, run_id=run_id, organism_id=organism_id)

    @classmethod
    def load(cls, checkpoint_path: Path | str, *, run_id: str, organism_id: str) -> "EngineWorkerSupervisor":
        return cls._spawn({
            "mode": "load", "checkpoint_path": str(checkpoint_path),
            "run_id": run_id, "organism_id": organism_id,
        }, run_id=run_id, organism_id=organism_id)

    @classmethod
    def _spawn(cls, initial, *, run_id: str, organism_id: str):
        context = mp.get_context("spawn")
        parent, child = context.Pipe()
        process = context.Process(target=_worker_main, args=(child, initial), daemon=True)
        process.start()
        child.close()
        return cls(process, parent, run_id=run_id, organism_id=organism_id)

    @property
    def alive(self) -> bool:
        return self._process.is_alive()

    def request(self, action: str, payload: dict[str, Any] | None = None, *, timeout: float = 20.0) -> dict[str, Any]:
        request = WorkerRequest(action=action, payload=payload or {})
        with self._lock:
            if not self.alive:
                raise RuntimeError("Verdant engine worker is not alive.")
            self._connection.send(request.model_dump(mode="json"))
            if not self._connection.poll(timeout):
                raise TimeoutError(f"Engine worker timed out handling {action}.")
            response = WorkerResponse.model_validate(self._connection.recv())
        if not response.ok:
            raise RuntimeError(f"Worker {response.error_type}: {response.error_message}\n{response.payload.get('traceback','')}")
        return response.payload

    def close(self, *, timeout: float = 5.0) -> None:
        if not self.alive:
            return
        try:
            self.request("shutdown", timeout=timeout)
        finally:
            self._process.join(timeout=timeout)
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(timeout=timeout)
            self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
