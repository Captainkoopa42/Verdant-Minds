from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import multiprocessing as mp
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from verdant_benchmarks import ArmName, BenchmarkConfig, EthomorphismBenchmarkHarness

from .models import new_id, utc_now_iso
from .release_identity import RELEASE_ID

EXPERIMENT_SCHEMA_VERSION = "verdant.experiment.v1"
EXPERIMENT_RESULT_SCHEMA_VERSION = "verdant.experiment.result.v1"
EXPERIMENT_PACKAGE_MEDIA_TYPE = "application/vnd.verdant.experiment+zip"
EXPERIMENT_PROTOCOL_ETHOMORPHISM = "ethomorphism.m19.v1"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)


class ExperimentAssertion(FrozenModel):
    path: str
    op: Literal["eq", "true", "false", "gte", "lte"] = "true"
    value: Any | None = None
    label: str | None = None


class ExperimentAuthorRequest(FrozenModel):
    project_id: str
    title: str = "Ethomorphism M19 Verification"
    protocol_id: str = EXPERIMENT_PROTOCOL_ETHOMORPHISM
    seed: int = 1901
    state_dim: int = Field(default=16, ge=4)
    repeats_per_edge: int = Field(default=2, ge=1, le=20)
    noise_concepts: int = Field(default=16, ge=4, le=512)
    noise_repeats: int = Field(default=1, ge=1, le=20)
    relation_type: str = "linked"
    expected_assertions: tuple[ExperimentAssertion, ...] = ()
    parent_experiment_id: str | None = None


class ExperimentForkRequest(FrozenModel):
    title: str | None = None
    seed: int | None = None
    state_dim: int | None = Field(default=None, ge=4)
    repeats_per_edge: int | None = Field(default=None, ge=1, le=20)
    noise_concepts: int | None = Field(default=None, ge=4, le=512)
    noise_repeats: int | None = Field(default=None, ge=1, le=20)
    relation_type: str | None = None
    keep_expected_assertions: bool = True


class ExperimentManifest(FrozenModel):
    schema_id: Literal[EXPERIMENT_SCHEMA_VERSION] = Field(
        default=EXPERIMENT_SCHEMA_VERSION, alias="schema", serialization_alias="schema"
    )
    experiment_id: str
    project_id: str
    title: str
    version: int
    protocol_id: Literal[EXPERIMENT_PROTOCOL_ETHOMORPHISM] = EXPERIMENT_PROTOCOL_ETHOMORPHISM
    created_at: str
    parent_experiment_id: str | None = None
    engine_baseline: str = "verdant-m19"
    workbench_schema: str = "workbench-1.0.1"
    release_id: str = RELEASE_ID
    engine_source_sha256: str = ""
    workbench_source_sha256: str = ""
    dependency_lock_sha256: str = ""
    protocol_config: dict[str, Any]
    arms: tuple[str, ...] = tuple(arm.value for arm in ArmName)
    curriculum_sha256: str
    curriculum_event_count: int
    resource_lock: dict[str, Any]
    metrics: tuple[str, ...]
    interventions: tuple[dict[str, Any], ...]
    expected_assertions: tuple[ExperimentAssertion, ...]


class ExperimentPackageError(RuntimeError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def default_assertions() -> tuple[ExperimentAssertion, ...]:
    paths = (
        "headline_checks.same_external_curriculum_count_all_arms",
        "headline_checks.target_abstraction_not_taught",
        "headline_checks.d_forms_earned_structures",
        "headline_checks.d_forms_higher_order_q",
        "headline_checks.c_has_plasticity_without_promoted_folds",
        "headline_checks.all_arms_reconstruct_heldout_world",
        "headline_checks.d_uses_compiled_structure",
        "headline_checks.p_ablation_restoration_is_causal",
        "headline_checks.q_ablation_restoration_is_causal",
        "headline_checks.d_rejects_star_from_path_family",
        "headline_checks.refolding_preserves_lineage",
        "headline_checks.refolding_preserves_semantic_counts",
        "headline_checks.c_long_run_within_caps",
        "headline_checks.d_long_run_within_caps",
    )
    return tuple(ExperimentAssertion(path=path, op="true", label=path.rsplit(".", 1)[-1]) for path in paths)


def config_from_manifest(manifest: ExperimentManifest) -> BenchmarkConfig:
    return BenchmarkConfig(**manifest.protocol_config)


def default_metrics() -> tuple[str, ...]:
    return (
        "local_reconstruction_work", "local_reconstruction_success", "promoted_structures",
        "layered_structures", "family_comparison_work", "family_selectivity_success",
        "plastic_density", "plastic_edge_ratio", "plastic_max_degree", "persistent_bytes",
    )


def default_interventions() -> tuple[dict[str, Any], ...]:
    return (
        {"arm": "D_full_earned_folds", "action": "ablate_restore_P", "measurement": "local_reconstruction_work"},
        {"arm": "D_full_earned_folds", "action": "ablate_restore_Q", "measurement": "family_comparison_work"},
        {"arm": "D_full_earned_folds", "action": "typed_structural_challenge_then_refold", "measurement": "lineage_and_semantic_firewall"},
        {"arm": "C_plastic_no_folds,D_full_earned_folds", "action": "bounded_plasticity_stress", "measurement": "density_degree_edge_ratio"},
    )


def manifest_curriculum_payload(config: BenchmarkConfig) -> tuple[str, list[dict[str, Any]]]:
    harness = EthomorphismBenchmarkHarness(config)
    commands = [item.model_dump(mode="json") for item in harness.curriculum_commands()]
    return harness.curriculum_sha256(), commands


def build_experiment_package(manifest: ExperimentManifest) -> bytes:
    config = config_from_manifest(manifest)
    curriculum_sha, commands = manifest_curriculum_payload(config)
    if curriculum_sha != manifest.curriculum_sha256:
        raise ExperimentPackageError("Manifest curriculum hash does not match protocol curriculum.")
    files: dict[str, bytes] = {
        "manifest.json": json.dumps(manifest.model_dump(mode="json", by_alias=True), indent=2, sort_keys=True).encode("utf-8"),
        "curriculum/compiled_commands.json": json.dumps(commands, indent=2, sort_keys=True).encode("utf-8"),
        "expected_assertions.json": json.dumps(
            [item.model_dump(mode="json") for item in manifest.expected_assertions], indent=2, sort_keys=True
        ).encode("utf-8"),
    }
    hashes = {name: sha256_bytes(data) for name, data in files.items()}
    files["hashes.json"] = json.dumps(hashes, indent=2, sort_keys=True).encode("utf-8")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(files):
            info = zipfile.ZipInfo(name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, files[name])
    return buffer.getvalue()


def read_experiment_package(path: Path | str) -> tuple[ExperimentManifest, dict[str, Any]]:
    path = Path(path)
    with zipfile.ZipFile(path, "r") as zf:
        names = set(zf.namelist())
        required = {"manifest.json", "curriculum/compiled_commands.json", "expected_assertions.json", "hashes.json"}
        missing = required - names
        if missing:
            raise ExperimentPackageError(f"Experiment package is missing {sorted(missing)}")
        hashes = json.loads(zf.read("hashes.json"))
        for name, expected in hashes.items():
            if name not in names:
                raise ExperimentPackageError(f"Hash ledger references missing member {name}")
            actual = sha256_bytes(zf.read(name))
            if actual != expected:
                raise ExperimentPackageError(f"Experiment member integrity failure for {name}")
        manifest = ExperimentManifest.model_validate_json(zf.read("manifest.json"))
        commands = json.loads(zf.read("curriculum/compiled_commands.json"))
        curriculum_sha = hashlib.sha256(canonical_json(commands)).hexdigest()
        # The engine's benchmark hash is defined over JSON payload with sort/separators,
        # which canonical_json reproduces.
        if curriculum_sha != manifest.curriculum_sha256:
            raise ExperimentPackageError("Embedded curriculum does not match manifest curriculum_sha256")
        return manifest, {"hashes": hashes, "commands": commands}


def _worker_env() -> dict[str, str]:
    env = os.environ.copy()
    here = Path(__file__).resolve()
    backend = here.parents[1]
    root = here.parents[3]
    current = [item for item in env.get("PYTHONPATH", "").split(os.pathsep) if item]
    env["PYTHONPATH"] = os.pathsep.join([str(root), str(backend), *current])
    # Keep isolated benchmark workers from spawning large BLAS thread pools.
    # These runs are small and process-level reproducibility matters more than
    # opportunistic linear-algebra parallelism.
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    env["NUMEXPR_NUM_THREADS"] = "1"
    return env


def _invoke_worker(mode: str, config: BenchmarkConfig, arm: str | None = None) -> dict[str, Any]:
    args = [sys.executable, "-m", "verdant_workbench.experiment_worker", "--mode", mode,
            "--config", json.dumps(asdict(config), sort_keys=True)]
    if arm is not None:
        args += ["--arm", arm]
    # File-backed stdio is intentional. Some numerical/runtime stacks can keep
    # pipe handles alive longer than expected under capture_output, whereas the
    # laboratory protocol only needs the final machine-readable payload.
    with tempfile.TemporaryDirectory(prefix="verdant-xworker-") as td:
        out_path = Path(td) / "stdout.json"
        err_path = Path(td) / "stderr.txt"
        with out_path.open("wb") as out, err_path.open("wb") as err:
            proc = subprocess.run(args, env=_worker_env(), stdout=out, stderr=err, check=False)
        stdout = out_path.read_text(encoding="utf-8", errors="replace")
        stderr = err_path.read_text(encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(
            f"Experiment worker failed ({mode}/{arm}): {stderr.strip() or stdout.strip()}"
        )
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Experiment worker returned invalid JSON: {stdout[:500]}") from exc


def _assemble_summary(config: BenchmarkConfig, worker_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    harness = EthomorphismBenchmarkHarness(config)
    arms = {name: worker_results[name]["arm_metrics"] for name in (arm.value for arm in ArmName)}
    d_result = worker_results[ArmName.D_FULL.value]
    c_result = worker_results[ArmName.C_PLASTIC.value]
    causal = d_result["causal_controls"]
    refold = d_result["refolding"]
    health = {
        ArmName.C_PLASTIC.value: c_result["health"],
        ArmName.D_FULL.value: d_result["health"],
    }
    d = arms[ArmName.D_FULL.value]
    c = arms[ArmName.C_PLASTIC.value]
    checks = {
        "same_external_curriculum_count_all_arms": len({m["curriculum_events"] for m in arms.values()}) == 1,
        "target_abstraction_not_taught": True,
        "d_forms_earned_structures": d["promoted_structures"] >= 5,
        "d_forms_higher_order_q": d["layered_structures"] >= 1,
        "c_has_plasticity_without_promoted_folds": c["plastic_associations"] > 0 and c["promoted_structures"] == 0,
        "all_arms_reconstruct_heldout_world": all(m["local_reconstruction_success"] for m in arms.values()),
        "all_arms_identify_path_family_under_evaluator": all(m["family_transfer_success"] for m in arms.values()),
        "d_uses_compiled_structure": bool(d["local_structure_used"]),
        "p_ablation_restoration_is_causal": bool(causal["gain_followed_structure"] and causal["same_reconstruction"]),
        "q_ablation_restoration_is_causal": bool(causal["q_gain_followed_object"] and causal["same_family_matches"]),
        "d_rejects_star_from_path_family": bool(d["family_selectivity_success"]),
        "refolding_preserves_lineage": bool(refold["lineage_preserved"] and refold["parent_preserved"]),
        "refolding_preserves_semantic_counts": bool(refold["semantic_counts_unchanged"]),
        "c_long_run_within_caps": bool(health[ArmName.C_PLASTIC.value]["within_degree_cap"] and health[ArmName.C_PLASTIC.value]["within_edge_ratio_cap"]),
        "d_long_run_within_caps": bool(health[ArmName.D_FULL.value]["within_degree_cap"] and health[ArmName.D_FULL.value]["within_edge_ratio_cap"]),
    }
    return {
        "schema": "verdant.ethomorphism_benchmark.v1",
        "config": asdict(config),
        "curriculum_sha256": harness.curriculum_sha256(),
        "target_abstraction_taught": False,
        "arms": arms,
        "causal_controls": causal,
        "refolding": refold,
        "long_run_health": health,
        "headline_checks": checks,
        "interpretation": {
            "scope": "Controlled synthetic benchmark of representational formation, reuse, family recognition, ablation/restoration, refolding, and saturation health.",
            "not_claimed": "This benchmark does not establish general intelligence, autonomous language-level theory discovery, or learned manifold geometry. World boundaries and scoring labels exist only in the external evaluator.",
            "fairness": "All four arms receive the same ordered primitive edge curriculum, seed, state dimension, and hidden family labels are never installed in canonical Verdant state. C and D additionally share the same developmental resource/plasticity policies; their intended difference is fold promotion/use.",
        },
    }


def normalized_scientific_result(summary: dict[str, Any]) -> dict[str, Any]:
    """Remove descriptive/non-deterministic telemetry from a benchmark result."""
    payload = json.loads(json.dumps(summary))
    for arm in payload.get("arms", {}).values():
        arm.pop("training_wall_seconds", None)
    return payload


def scientific_result_sha256(summary: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json(normalized_scientific_result(summary)))




def _full_protocol_process(config_dict: dict[str, Any], output_path: str) -> None:
    config = BenchmarkConfig(**config_dict)
    summary = EthomorphismBenchmarkHarness(config).run().to_dict()
    Path(output_path).write_text(
        json.dumps({"worker_pid": os.getpid(), "summary": summary}, sort_keys=True),
        encoding="utf-8",
    )


def _run_protocol_process(config: BenchmarkConfig, timeout: float = 300.0) -> dict[str, Any]:
    # Prefer fork on Unix because the current Verdant engine is already loaded
    # in the Workbench process and a clean copy-on-write child avoids a second
    # import/bootstrap path. Spawn remains the portable fallback.
    methods = mp.get_all_start_methods()
    method = "fork" if "fork" in methods else "spawn"
    ctx = mp.get_context(method)
    with tempfile.TemporaryDirectory(prefix="verdant-experiment-") as td:
        result_path = Path(td) / "result.json"
        proc = ctx.Process(
            target=_full_protocol_process,
            args=(asdict(config), str(result_path)),
            daemon=False,
        )
        proc.start()
        pid = proc.pid
        proc.join(timeout)
        if proc.is_alive():
            proc.terminate()
            proc.join(10.0)
            raise RuntimeError(f"Experiment worker timed out after {timeout:.0f}s")
        if proc.exitcode != 0:
            raise RuntimeError(f"Experiment worker exited with code {proc.exitcode}")
        if not result_path.is_file():
            raise RuntimeError("Experiment worker produced no result artifact")
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        payload["start_method"] = method
        payload["worker_pid"] = int(payload.get("worker_pid") or pid or 0)
        return payload

def run_ethomorphism_isolated(config: BenchmarkConfig) -> dict[str, Any]:
    # The complete protocol runs outside the Workbench server in one supervised
    # OS process. Inside that process the M19 harness creates four independent
    # kernel/runtime arms, so no canonical state is shared between A/B/C/D.
    # OS-process-per-arm fanout is deliberately deferred: on memory-limited
    # machines it can distort or stall the benchmark without changing the
    # scientific isolation property under test.
    result = _run_protocol_process(config)
    summary = result["summary"]
    return {
        "summary": summary,
        "scientific_result_sha256": scientific_result_sha256(summary),
        "worker_isolation": {
            "mode": "dedicated experiment subprocess; independent kernel/runtime per arm",
            "experiment_worker_pid": int(result["worker_pid"]),
            "process_start_method": result.get("start_method"),
            "arm_state_isolation": True,
            "arm_ids": [arm.value for arm in ArmName],
        },
    }


def _lookup_path(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(path)
        current = current[part]
    return current


def evaluate_assertions(summary: dict[str, Any], assertions: tuple[ExperimentAssertion, ...]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for assertion in assertions:
        try:
            actual = _lookup_path(summary, assertion.path)
            if assertion.op == "true":
                passed = actual is True
            elif assertion.op == "false":
                passed = actual is False
            elif assertion.op == "eq":
                passed = actual == assertion.value
            elif assertion.op == "gte":
                passed = actual >= assertion.value
            elif assertion.op == "lte":
                passed = actual <= assertion.value
            else:
                passed = False
            error = None
        except Exception as exc:  # inspection result, not engine mutation
            actual = None
            passed = False
            error = str(exc)
        results.append({
            "path": assertion.path,
            "op": assertion.op,
            "expected": assertion.value if assertion.op not in {"true", "false"} else (assertion.op == "true"),
            "actual": actual,
            "passed": bool(passed),
            "label": assertion.label,
            "error": error,
        })
    return results


def build_verification_package(
    source_package: Path | str,
    *,
    result_payload: dict[str, Any],
    assertion_results: list[dict[str, Any]],
    verification: dict[str, Any],
) -> bytes:
    source_package = Path(source_package)
    source_bytes = source_package.read_bytes()
    manifest, package = read_experiment_package(source_package)
    files: dict[str, bytes] = {
        "source_experiment.vexp": source_bytes,
        "manifest.json": json.dumps(manifest.model_dump(mode="json", by_alias=True), indent=2, sort_keys=True).encode("utf-8"),
        "curriculum/compiled_commands.json": json.dumps(package["commands"], indent=2, sort_keys=True).encode("utf-8"),
        "results/summary.json": json.dumps(result_payload["summary"], indent=2, sort_keys=True).encode("utf-8"),
        "results/scientific_result.json": json.dumps(normalized_scientific_result(result_payload["summary"]), indent=2, sort_keys=True).encode("utf-8"),
        "results/worker_isolation.json": json.dumps(result_payload["worker_isolation"], indent=2, sort_keys=True).encode("utf-8"),
        "results/assertions.json": json.dumps(assertion_results, indent=2, sort_keys=True).encode("utf-8"),
        "verification.json": json.dumps(verification, indent=2, sort_keys=True).encode("utf-8"),
    }
    hashes = {name: sha256_bytes(data) for name, data in files.items()}
    files["hashes.json"] = json.dumps(hashes, indent=2, sort_keys=True).encode("utf-8")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(files):
            info = zipfile.ZipInfo(name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, files[name])
    return buffer.getvalue()


def read_verification_package(path: Path | str) -> dict[str, Any]:
    path = Path(path)
    with zipfile.ZipFile(path, "r") as zf:
        names = set(zf.namelist())
        required = {
            "source_experiment.vexp", "manifest.json", "curriculum/compiled_commands.json",
            "results/summary.json", "results/scientific_result.json", "results/worker_isolation.json",
            "results/assertions.json", "verification.json", "hashes.json",
        }
        missing = required - names
        if missing:
            raise ExperimentPackageError(f"Verification package is missing {sorted(missing)}")
        hashes = json.loads(zf.read("hashes.json"))
        for name, expected in hashes.items():
            actual = sha256_bytes(zf.read(name))
            if actual != expected:
                raise ExperimentPackageError(f"Verification member integrity failure for {name}")
        summary = json.loads(zf.read("results/summary.json"))
        scientific = json.loads(zf.read("results/scientific_result.json"))
        if sha256_bytes(canonical_json(scientific)) != scientific_result_sha256(summary):
            raise ExperimentPackageError("Scientific-result view is inconsistent with raw summary")
        return {
            "manifest": json.loads(zf.read("manifest.json")),
            "summary": summary,
            "scientific_result": scientific,
            "worker_isolation": json.loads(zf.read("results/worker_isolation.json")),
            "assertions": json.loads(zf.read("results/assertions.json")),
            "verification": json.loads(zf.read("verification.json")),
            "hashes": hashes,
        }
