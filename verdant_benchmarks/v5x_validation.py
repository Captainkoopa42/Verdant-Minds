from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import platform
from pathlib import Path
import sys

from verdant_compilation import VerdantCompilationPipeline
from verdant_hierarchy import VerdantHierarchyPipeline

from .ethomorphism import ArmName, BenchmarkConfig, EthomorphismBenchmarkHarness
from .interventions import fork_destructive_p_lesion, fork_destructive_q_lesion
from .recovery import governed_rederive_p, governed_rederive_q
from .thermodynamic_sweep import ThermodynamicSweepHarness


class V5XValidationHarness:
    """Headless pre-merge validation harness for the V5-X engineering branch."""

    def __init__(
        self,
        *,
        seed: int = 1901,
        state_dim: int = 16,
        noise_concepts: int = 0,
        source_ref: str = "V5-X",
    ) -> None:
        self.seed = int(seed)
        self.state_dim = int(state_dim)
        self.noise_concepts = int(noise_concepts)
        self.source_ref = str(source_ref)

    @staticmethod
    def _source_identity() -> dict:
        root = Path(__file__).resolve().parents[1]
        paths = [
            "verdant_kernel/kernel.py",
            "verdant_development/__init__.py",
            "verdant_development/pipeline.py",
            "verdant_development/v5x.py",
            "verdant_language/pipeline.py",
            "verdant_benchmarks/ethomorphism.py",
            "verdant_benchmarks/interventions.py",
            "verdant_benchmarks/recovery.py",
            "verdant_benchmarks/thermodynamic_sweep.py",
            "verdant_benchmarks/v5x_validation.py",
            "run_v5x_cultivation.py",
            "workbench/backend/verdant_workbench/v5x_adapter.py",
            "workbench/backend/verdant_workbench/worker.py",
            "verdant_thermodynamics/models.py",
            "verdant_thermodynamics/metrics.py",
            "verdant_thermodynamics/phase.py",
            "verdant_thermodynamics/observer.py",
            "verdant_thermodynamics/controller.py",
            "verdant_thermodynamics/telemetry.py",
        ]
        hashes = {}
        for relative in paths:
            data = (root / relative).read_bytes()
            hashes[relative] = hashlib.sha256(data).hexdigest()
        aggregate = hashlib.sha256(
            json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return {
            "aggregate_sha256": aggregate,
            "files": hashes,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        }

    def _m19(self) -> dict:
        summary = EthomorphismBenchmarkHarness(
            BenchmarkConfig(
                seed=self.seed,
                state_dim=self.state_dim,
                noise_concepts=self.noise_concepts,
            )
        ).run()
        return summary.to_dict()

    def _lesions(self) -> dict:
        harness = EthomorphismBenchmarkHarness(
            BenchmarkConfig(seed=self.seed, state_dim=self.state_dim, noise_concepts=0)
        )
        runtime = harness.train_arm(ArmName.D_FULL)
        source = runtime.kernel
        source_fingerprint = source.fingerprint()
        novel_p = runtime.structure_by_world[harness.novel_world.name]
        q_id = runtime.layered_structure_id
        if q_id is None:
            raise RuntimeError("V5-X lesion assay requires M19 D arm to form Q.")
        cue = harness._concept_id(source, harness.novel_world.labels[0])

        p_before = VerdantCompilationPipeline().inspect(source, (cue,))
        p_lesion = fork_destructive_p_lesion(source, novel_p)
        p_damaged = VerdantCompilationPipeline().inspect(p_lesion.kernel, (cue,))
        p_recovery = governed_rederive_p(p_lesion)
        p_after = VerdantCompilationPipeline().inspect(p_lesion.kernel, (cue,))

        q_before = VerdantHierarchyPipeline().inspect_probe(source, novel_p)
        q_lesion = fork_destructive_q_lesion(source, q_id)
        q_damaged = VerdantHierarchyPipeline().inspect_probe(q_lesion.kernel, novel_p)
        q_recovery = governed_rederive_q(q_lesion)
        q_after = VerdantHierarchyPipeline().inspect_probe(q_lesion.kernel, novel_p)

        return {
            "schema_id": "verdant.v5x_lesion_assay.v1",
            "source_fingerprint": source_fingerprint,
            "source_unchanged_after_forks": source.fingerprint() == source_fingerprint,
            "p": {
                "manifest": asdict(p_lesion.manifest),
                "work_before": p_before.cost.low_level_work,
                "work_damaged": p_damaged.cost.low_level_work,
                "work_after_governed_rederivation": p_after.cost.low_level_work,
                "same_reconstruction": p_before.reconstructed_concept_ids == p_damaged.reconstructed_concept_ids == p_after.reconstructed_concept_ids,
                "recovery": asdict(p_recovery),
            },
            "q": {
                "manifest": asdict(q_lesion.manifest),
                "work_before": q_before.cost.comparison_work,
                "work_damaged": q_damaged.cost.comparison_work,
                "work_after_governed_rederivation": q_after.cost.comparison_work,
                "same_matches": q_before.matched_structure_ids == q_damaged.matched_structure_ids == q_after.matched_structure_ids,
                "recovery": asdict(q_recovery),
            },
            "claim_boundary": (
                "This assay demonstrates destructive fork lesion plus native governed re-derivation. "
                "It does not claim autonomous self-repair because promotion is externally invoked."
            ),
        }

    def run(self, *, experiment: str = "all") -> dict:
        if experiment not in {"all", "m19", "thermodynamics", "lesions"}:
            raise ValueError("experiment must be one of: all, m19, thermodynamics, lesions")
        payload = {
            "schema_id": "verdant.v5x_validation.v1",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "seed": self.seed,
            "state_dim": self.state_dim,
            "noise_concepts": self.noise_concepts,
            "experiment": experiment,
            "expected_branch": "V5-X",
            "source_ref": self.source_ref,
            "source_identity": self._source_identity(),
            "behavioral_thermodynamic_control_enabled": False,
        }
        if experiment in {"all", "m19"}:
            payload["m19"] = self._m19()
        if experiment in {"all", "thermodynamics"}:
            payload["thermodynamics"] = ThermodynamicSweepHarness(
                seed=self.seed,
                state_dim=max(16, self.state_dim),
            ).run().to_dict()
        if experiment in {"all", "lesions"}:
            payload["lesions"] = self._lesions()

        checks = {}
        if "m19" in payload:
            checks["m19_all_headline_checks_pass"] = all(payload["m19"]["headline_checks"].values())
        if "thermodynamics" in payload:
            thermo = payload["thermodynamics"]
            checks["thermodynamic_observer_is_null_equivalent"] = bool(thermo["observer_null_equivalence"])
            checks["thermodynamics_does_not_mutate_governance_tg"] = bool(thermo["governance_tg_unchanged"])
            checks["v4_formula_grid_reaches_all_phase_regions"] = bool(thermo["formula_grid"]["all_phase_regions_reachable"])
        if "lesions" in payload:
            lesions = payload["lesions"]
            checks["lesion_forks_leave_source_unchanged"] = bool(lesions["source_unchanged_after_forks"])
            checks["p_damage_has_causal_cost"] = lesions["p"]["work_damaged"] > lesions["p"]["work_before"]
            checks["p_governed_rederivation_recovers_cost"] = lesions["p"]["work_after_governed_rederivation"] == lesions["p"]["work_before"]
            checks["q_damage_has_causal_cost"] = lesions["q"]["work_damaged"] > lesions["q"]["work_before"]
            checks["q_governed_rederivation_recovers_cost"] = lesions["q"]["work_after_governed_rederivation"] == lesions["q"]["work_before"]
            checks["no_restore_operation_used_for_rederivation"] = not lesions["p"]["recovery"]["used_restore_operation"] and not lesions["q"]["recovery"]["used_restore_operation"]
        payload["headline_checks"] = checks
        payload["validation_qualifies"] = bool(checks) and all(checks.values())
        return payload

    @staticmethod
    def write_package(payload: dict, output: Path | str) -> tuple[Path, Path]:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"
        path.write_bytes(encoded)
        digest = hashlib.sha256(encoded).hexdigest()
        sha_path = path.with_suffix(path.suffix + ".sha256")
        sha_path.write_text(f"{digest}  {path.name}\n", encoding="utf-8")
        return path, sha_path
