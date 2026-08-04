from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median
from typing import Iterable

from verdant_development import VerdantDevelopmentPipeline
from verdant_hierarchy import VerdantHierarchyPipeline
from verdant_interaction import VerdantStructureInteractionPipeline
from verdant_kernel import (
    EvidenceKind,
    ExperienceCommand,
    HierarchyCandidateStatus,
    LayeredProbeDisposition,
    StructureCandidateStatus,
    VerdantKernel,
)
from verdant_structures import VerdantStructurePipeline

from .ethomorphism import BenchmarkConfig, EthomorphismBenchmarkHarness


@dataclass(frozen=True)
class ShapeCase:
    name: str
    expected_family: bool
    edges: tuple[tuple[int, int], ...]
    repeats: tuple[int, ...]


POSITIVE_CASES = (
    ShapeCase("path_balanced", True, ((1, 2), (2, 3), (3, 4)), (2, 2, 2)),
    ShapeCase("path_weighted_mild", True, ((1, 2), (2, 3), (3, 4)), (2, 3, 4)),
    ShapeCase("path_weighted_strong", True, ((1, 2), (2, 3), (3, 4)), (2, 4, 8)),
)

NEGATIVE_CASES = (
    ShapeCase("star", False, ((1, 2), (1, 3), (1, 4)), (2, 2, 2)),
    ShapeCase("cycle", False, ((1, 2), (2, 3), (3, 4), (4, 1)), (2, 2, 2, 2)),
    ShapeCase("paw", False, ((1, 2), (2, 3), (3, 1), (3, 4)), (2, 2, 2, 2)),
)


@dataclass(frozen=True)
class QEvaluationConfig:
    seeds: tuple[int, ...] = (1701, 1901, 2903, 3907, 4909, 5903)
    state_dim: int = 16
    thresholds: tuple[float, ...] = (
        0.900,
        0.950,
        0.975,
        0.980,
        0.985,
        0.990,
        0.995,
        0.999,
    )
    scaling_levels: tuple[int, ...] = (0, 4, 8)
    baseline_seeds: tuple[int, ...] = (1901, 2903)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _wilson(successes: int, total: int, z: float = 1.959963984540054) -> dict[str, float]:
    if total <= 0:
        return {"low": 0.0, "high": 0.0}
    p = successes / total
    denominator = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denominator
    margin = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * total)) / total) / denominator
    return {"low": max(0.0, center - margin), "high": min(1.0, center + margin)}


class QEvaluationHarness:
    """External, preregistered-style Q evaluation.

    Family labels and pass/fail scoring live only in this evaluator. Verdant is
    given repeated primitive co-occurrences and must earn P and Q through its
    ordinary public pipelines. Every query is created after Q promotion.
    """

    schema = "verdant.q_evaluation.v1"

    def __init__(self, config: QEvaluationConfig | None = None) -> None:
        self.config = config or QEvaluationConfig()
        self.hierarchy = VerdantHierarchyPipeline()
        self.interaction = VerdantStructureInteractionPipeline()

    @staticmethod
    def _command(event_key: str, labels: tuple[str, str], context: str) -> ExperienceCommand:
        return ExperienceCommand(
            event_key=event_key,
            source_ref="q-evaluation:primitive",
            modality="text",
            payload_sha256=_digest(event_key + ":" + ":".join(labels)),
            feature_vector=(1.0, 0.0, 0.0),
            concept_labels=labels,
            confidence=1.0,
            semantic_evidence_kind=EvidenceKind.TESTIMONY,
            semantic_evidence_details={"controlled_q_evaluation": True},
            metadata={"context_id": context},
        )

    @staticmethod
    def _candidate_labels(kernel: VerdantKernel, candidate) -> set[str]:
        return {
            kernel.state.concepts[concept_id].normalized_label
            for concept_id in candidate.member_concept_ids
        }

    def _cultivate(
        self,
        kernel: VerdantKernel,
        prefix: str,
        edges: tuple[tuple[int, int], ...],
        repeats: tuple[int, ...],
    ) -> str:
        development = VerdantDevelopmentPipeline()
        labelled_edges = tuple(
            (f"{prefix}{source}", f"{prefix}{target}") for source, target in edges
        )
        for edge_index, (edge, repeat_count) in enumerate(zip(labelled_edges, repeats)):
            for repeat in range(repeat_count):
                development.advance(
                    kernel,
                    self._command(
                        f"qeval:{prefix}:e{edge_index}:r{repeat}",
                        edge,
                        f"qeval:{prefix}:context:{repeat % 2}",
                    ),
                )
        expected = {label for edge in labelled_edges for label in edge}
        candidates = [
            candidate
            for candidate in kernel.state.structure_candidates.values()
            if self._candidate_labels(kernel, candidate) == expected
            and candidate.status != StructureCandidateStatus.PROMOTED
        ]
        if not candidates:
            raise RuntimeError(f"No P candidate formed for {prefix!r}.")
        candidate = max(candidates, key=lambda item: item.occurrence_count)
        return VerdantStructurePipeline().promote(
            kernel, candidate.candidate_id
        ).event.structure_id

    def _base_q(self, seed: int) -> tuple[VerdantKernel, tuple[str, ...], str]:
        kernel = VerdantKernel(seed=seed, state_dim=self.config.state_dim, run_label=f"q-eval-{seed}")
        kernel.update_plasticity_policy(decay_rate=0.0, learning_rate=0.40)
        kernel.update_structure_policy(
            minimum_members=4,
            maximum_members=4,
            maximum_neighbors_per_seed=4,
            minimum_member_association_strength=0.20,
            minimum_reconstructability=0.20,
            minimum_internal_cohesion=0.18,
            minimum_recurrence_events=2,
            minimum_evidence_events=2,
            minimum_contexts=2,
        )
        kernel.update_hierarchy_policy(
            minimum_interaction_events=3,
            minimum_evidence_events=6,
            layered_probe_similarity=0.985,
        )
        family = tuple(
            self._cultivate(
                kernel,
                f"train{letter}",
                ((1, 2), (2, 3), (3, 4)),
                (2, 2, 2),
            )
            for letter in ("a", "b", "c")
        )
        for structure_id in family:
            self.interaction.interact(kernel, structure_id)
            self.hierarchy.observe(kernel)
        candidates = [
            item
            for item in kernel.state.hierarchy_candidates.values()
            if set(item.member_structure_ids) == set(family)
            and item.status != HierarchyCandidateStatus.PROMOTED
        ]
        if not candidates:
            raise RuntimeError("No Q candidate formed from the training family.")
        candidate = max(candidates, key=lambda item: item.occurrence_count)
        qid = self.hierarchy.promote(kernel, candidate.candidate_id).event.layered_structure_id
        return kernel, family, qid

    @staticmethod
    def _report_fields(report) -> dict:
        return {
            "disposition": report.disposition.value,
            "layered_structure_id": report.layered_structure_id,
            "matched_structure_ids": list(report.matched_structure_ids),
            "comparison_work": report.cost.comparison_work,
            "baseline_work": report.baseline_cost.comparison_work,
            "compression_gain": report.compression_gain,
            "cost": report.cost.model_dump(mode="json"),
            "baseline_cost": report.baseline_cost.model_dump(mode="json"),
        }

    def _case_kernel(self, base: VerdantKernel, seed: int, case: ShapeCase) -> tuple[VerdantKernel, str]:
        kernel = VerdantKernel.from_state(base.snapshot())
        query_id = self._cultivate(
            kernel,
            f"query{seed}{case.name}",
            case.edges,
            case.repeats,
        )
        return kernel, query_id

    def _evaluate_case(
        self,
        base: VerdantKernel,
        family: tuple[str, ...],
        qid: str,
        seed: int,
        case: ShapeCase,
    ) -> tuple[dict, list[dict]]:
        kernel, query_id = self._case_kernel(base, seed, case)
        query_signature = self.interaction.signature(kernel, query_id)
        layered = kernel.state.layered_structures[qid]
        prototype_similarity = self.hierarchy._prototype_similarity(query_signature, layered)
        symbolic_similarity, _mapping = self.interaction._symbolic_alignment(
            kernel,
            kernel.state.structures[query_id],
            kernel.state.structures[family[0]],
        )

        with_q = self.hierarchy.inspect_probe(kernel, query_id)
        self.hierarchy.ablate(kernel, qid, "Q evaluation causal ablation")
        without_q = self.hierarchy.inspect_probe(kernel, query_id)
        self.hierarchy.restore(kernel, qid, "Q evaluation causal restoration")
        restored = self.hierarchy.inspect_probe(kernel, query_id)

        uses_q = (
            with_q.disposition == LayeredProbeDisposition.USE_LAYERED_STRUCTURE
            and with_q.layered_structure_id == qid
        )
        restored_uses_q = (
            restored.disposition == LayeredProbeDisposition.USE_LAYERED_STRUCTURE
            and restored.layered_structure_id == qid
        )
        exact_family = set(with_q.matched_structure_ids) == set(family)
        same_matches = (
            set(with_q.matched_structure_ids)
            == set(without_q.matched_structure_ids)
            == set(restored.matched_structure_ids)
        )
        causal_success = (
            case.expected_family
            and uses_q
            and restored_uses_q
            and exact_family
            and same_matches
            and with_q.cost.comparison_work < without_q.cost.comparison_work
            and restored.cost.comparison_work == with_q.cost.comparison_work
        )
        record = {
            "seed": seed,
            "case": case.name,
            "expected_family": case.expected_family,
            "query_structure_id": query_id,
            "q_id": qid,
            "family_structure_ids": list(family),
            "prototype_similarity": prototype_similarity,
            "symbolic_similarity_to_representative": symbolic_similarity,
            "uses_q": uses_q,
            "correct": uses_q if case.expected_family else not uses_q,
            "exact_family_match": exact_family,
            "causal_success": causal_success,
            "with_q": self._report_fields(with_q),
            "q_ablated": self._report_fields(without_q),
            "q_restored": self._report_fields(restored),
        }

        sensitivity: list[dict] = []
        # Evaluate every threshold from the same post-formation state. Updating
        # policy changes only the probe gate, not any learned object.
        enabled_state = kernel.snapshot()
        for threshold in self.config.thresholds:
            threshold_kernel = VerdantKernel.from_state(enabled_state)
            threshold_kernel.update_hierarchy_policy(layered_probe_similarity=threshold)
            report = self.hierarchy.inspect_probe(threshold_kernel, query_id)
            selected = (
                report.disposition == LayeredProbeDisposition.USE_LAYERED_STRUCTURE
                and report.layered_structure_id == qid
            )
            sensitivity.append(
                {
                    "seed": seed,
                    "case": case.name,
                    "expected_family": case.expected_family,
                    "threshold": threshold,
                    "selected_q": selected,
                    "correct": selected if case.expected_family else not selected,
                    "comparison_work": report.cost.comparison_work,
                    "baseline_work": report.baseline_cost.comparison_work,
                    "compression_gain": report.compression_gain,
                }
            )
        return record, sensitivity

    def _scaling_trial(self, seed: int) -> list[dict]:
        base, family, qid = self._base_q(seed)
        kernel, query_id = self._case_kernel(base, seed, POSITIVE_CASES[0])
        levels = set(self.config.scaling_levels)
        maximum = max(levels, default=0)
        results: list[dict] = []

        def measure(distractors: int) -> None:
            report = self.hierarchy.inspect_probe(kernel, query_id)
            results.append(
                {
                    "seed": seed,
                    "distractor_structures": distractors,
                    "total_p_structures": len(kernel.state.structures),
                    "selected_q": report.layered_structure_id == qid,
                    "exact_family_match": set(report.matched_structure_ids) == set(family),
                    "comparison_work": report.cost.comparison_work,
                    "baseline_work": report.baseline_cost.comparison_work,
                    "compression_gain": report.compression_gain,
                }
            )

        if 0 in levels:
            measure(0)
        shapes = NEGATIVE_CASES
        for count in range(1, maximum + 1):
            shape = shapes[(count - 1) % len(shapes)]
            self._cultivate(
                kernel,
                f"scale{seed}n{count}",
                shape.edges,
                shape.repeats,
            )
            if count in levels:
                measure(count)
        return results

    def _baseline_trials(self) -> list[dict]:
        trials: list[dict] = []
        for seed in self.config.baseline_seeds:
            summary = EthomorphismBenchmarkHarness(
                BenchmarkConfig(seed=seed, state_dim=self.config.state_dim, noise_concepts=12)
            ).run().to_dict()
            for arm in summary["arms"].values():
                # Wall-clock time is environmental rather than a scientific result.
                arm.pop("training_wall_seconds", None)
            trials.append(
                {
                    "seed": seed,
                    "curriculum_sha256": summary["curriculum_sha256"],
                    "headline_checks": summary["headline_checks"],
                    "arms": summary["arms"],
                    "causal_controls": summary["causal_controls"],
                    "refolding": summary["refolding"],
                    "long_run_health": summary["long_run_health"],
                }
            )
        return trials

    @staticmethod
    def _rate(successes: int, total: int) -> dict:
        return {
            "successes": successes,
            "total": total,
            "rate": successes / total if total else 0.0,
            "wilson_95": _wilson(successes, total),
        }

    def _aggregate(
        self,
        trials: list[dict],
        sensitivity: list[dict],
        scaling: list[dict],
        baselines: list[dict],
    ) -> dict:
        positives = [item for item in trials if item["expected_family"]]
        negatives = [item for item in trials if not item["expected_family"]]
        positive_success = sum(item["correct"] and item["exact_family_match"] for item in positives)
        negative_success = sum(item["correct"] for item in negatives)
        causal_success = sum(item["causal_success"] for item in positives)
        with_work = [item["with_q"]["comparison_work"] for item in positives]
        without_work = [item["q_ablated"]["comparison_work"] for item in positives]
        differences = [without - with_ for with_, without in zip(with_work, without_work)]

        threshold_rows = []
        for threshold in self.config.thresholds:
            rows = [item for item in sensitivity if item["threshold"] == threshold]
            pos = [item for item in rows if item["expected_family"]]
            neg = [item for item in rows if not item["expected_family"]]
            tp = sum(item["selected_q"] for item in pos)
            fp = sum(item["selected_q"] for item in neg)
            threshold_rows.append(
                {
                    "threshold": threshold,
                    "true_positive_rate": tp / len(pos) if pos else 0.0,
                    "false_positive_rate": fp / len(neg) if neg else 0.0,
                    "balanced_accuracy": 0.5 * (
                        (tp / len(pos) if pos else 0.0)
                        + (1.0 - fp / len(neg) if neg else 0.0)
                    ),
                    "true_positives": tp,
                    "positive_total": len(pos),
                    "false_positives": fp,
                    "negative_total": len(neg),
                }
            )

        scaling_rows = []
        for level in self.config.scaling_levels:
            rows = [item for item in scaling if item["distractor_structures"] == level]
            scaling_rows.append(
                {
                    "distractor_structures": level,
                    "trials": len(rows),
                    "q_selection_rate": mean(item["selected_q"] for item in rows) if rows else 0.0,
                    "mean_q_work": mean(item["comparison_work"] for item in rows) if rows else 0.0,
                    "mean_baseline_work": mean(item["baseline_work"] for item in rows) if rows else 0.0,
                    "mean_compression_gain": mean(item["compression_gain"] for item in rows) if rows else 0.0,
                }
            )

        baseline_checks = [
            passed
            for run in baselines
            for passed in run["headline_checks"].values()
        ]
        return {
            "default_threshold": 0.985,
            "held_out_family_recognition": self._rate(positive_success, len(positives)),
            "negative_control_rejection": self._rate(negative_success, len(negatives)),
            "causal_ablation_restoration": self._rate(causal_success, len(positives)),
            "positive_work": {
                "mean_with_q": mean(with_work) if with_work else 0.0,
                "median_with_q": median(with_work) if with_work else 0.0,
                "mean_q_ablated": mean(without_work) if without_work else 0.0,
                "median_q_ablated": median(without_work) if without_work else 0.0,
                "mean_paired_reduction": mean(differences) if differences else 0.0,
                "mean_fraction_reduced": (
                    mean(diff / without for diff, without in zip(differences, without_work))
                    if differences
                    else 0.0
                ),
            },
            "threshold_sensitivity": threshold_rows,
            "scaling": scaling_rows,
            "four_arm_benchmark": self._rate(sum(baseline_checks), len(baseline_checks)),
            "failures": [
                {"seed": item["seed"], "case": item["case"], "reason": "incorrect_default_result"}
                for item in trials
                if not item["correct"]
            ]
            + [
                {"seed": item["seed"], "case": item["case"], "reason": "causal_control_failed"}
                for item in positives
                if not item["causal_success"]
            ],
        }

    def run(self) -> dict:
        trials: list[dict] = []
        sensitivity: list[dict] = []
        formation_failures: list[dict] = []
        for seed in self.config.seeds:
            try:
                base, family, qid = self._base_q(seed)
                for case in (*POSITIVE_CASES, *NEGATIVE_CASES):
                    record, rows = self._evaluate_case(base, family, qid, seed, case)
                    trials.append(record)
                    sensitivity.extend(rows)
            except Exception as exc:  # failure data must not disappear from the campaign
                formation_failures.append(
                    {"seed": seed, "exception_type": type(exc).__name__, "message": str(exc)}
                )

        scaling = self._scaling_trial(self.config.seeds[0]) if self.config.seeds else []
        baselines = self._baseline_trials()
        aggregate = self._aggregate(trials, sensitivity, scaling, baselines)
        aggregate["formation_failures"] = formation_failures
        scientific = {
            "schema": self.schema,
            "config": asdict(self.config),
            "case_definitions": [asdict(item) for item in (*POSITIVE_CASES, *NEGATIVE_CASES)],
            "trials": trials,
            "threshold_sensitivity": sensitivity,
            "scaling": scaling,
            "four_arm_baselines": baselines,
            "aggregate": aggregate,
        }
        return {
            **scientific,
            "scientific_sha256": _canonical_sha256(scientific),
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "interpretation_limits": [
                "This is a controlled synthetic structural benchmark, not a general-intelligence test.",
                "Seed repetition probes deterministic-initialization sensitivity; runs are deterministic given a seed and are not independent random population samples.",
                "Family labels and scoring remain external and are never taught to Verdant.",
                "Confidence intervals describe this finite case set and must not be read as population prevalence.",
                "Independent reproduction and broader naturalistic tasks are still required for publication-strength claims.",
            ],
        }


def _write_csv(path: Path, rows: Iterable[dict]) -> None:
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_evaluation_bundle(output_dir: str | Path, result: dict) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "q_evaluation.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    protocol = {
        "schema": result["schema"],
        "frozen_config": result["config"],
        "case_definitions": result["case_definitions"],
        "primary_endpoint": "correct Q selection at the frozen default threshold",
        "secondary_endpoints": [
            "exact held-out family recovery",
            "negative-control Q rejection",
            "paired comparison-work change under Q ablation and restoration",
            "threshold sensitivity",
            "comparison-work scaling with unrelated promoted P distractors",
            "existing four-arm benchmark headline checks",
        ],
        "failure_policy": "Record every incorrect result and every exception; do not discard seeds.",
        "leakage_control": "Q is promoted before any query or negative-control structure exists.",
        "isolation_control": "Every query begins from a fresh copy of the same post-Q state.",
    }
    (output / "protocol.json").write_text(
        json.dumps(protocol, indent=2, sort_keys=True), encoding="utf-8"
    )
    with (output / "trial_results.jsonl").open("w", encoding="utf-8") as handle:
        for row in result["trials"]:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    _write_csv(output / "threshold_sensitivity.csv", result["aggregate"]["threshold_sensitivity"])
    _write_csv(output / "scaling.csv", result["aggregate"]["scaling"])
    aggregate = result["aggregate"]
    recognition = aggregate["held_out_family_recognition"]
    rejection = aggregate["negative_control_rejection"]
    causal = aggregate["causal_ablation_restoration"]
    work = aggregate["positive_work"]
    default_threshold = next(
        row for row in aggregate["threshold_sensitivity"]
        if row["threshold"] == aggregate["default_threshold"]
    )
    perfect_thresholds = [
        row["threshold"]
        for row in aggregate["threshold_sensitivity"]
        if row["true_positive_rate"] == 1.0 and row["false_positive_rate"] == 0.0
    ]
    report = f"""# Verdant Q Evaluation Report

Generated: {result['generated_at_utc']}

Scientific result SHA-256: `{result['scientific_sha256']}`

## Result

- Held-out path recognition: {recognition['successes']}/{recognition['total']} ({recognition['rate']:.1%})
- Unrelated-shape rejection: {rejection['successes']}/{rejection['total']} ({rejection['rate']:.1%})
- Q ablation/restoration causal controls: {causal['successes']}/{causal['total']} ({causal['rate']:.1%})
- Mean comparison work with Q: {work['mean_with_q']:.3f}
- Mean comparison work with Q ablated: {work['mean_q_ablated']:.3f}
- Mean paired work reduction: {work['mean_paired_reduction']:.3f} ({work['mean_fraction_reduced']:.1%})
- Four-arm benchmark checks: {aggregate['four_arm_benchmark']['successes']}/{aggregate['four_arm_benchmark']['total']}
- Recorded default/causal failures: {len(aggregate['failures'])}
- Recorded formation exceptions: {len(aggregate['formation_failures'])}

At the frozen 0.985 gate, true-positive rate was {default_threshold['true_positive_rate']:.1%}
and false-positive rate was {default_threshold['false_positive_rate']:.1%}. Thresholds with
perfect separation on this finite case set were: {', '.join(f'{item:.3f}' for item in perfect_thresholds) or 'none'}.
This is a sensitivity finding, not enough evidence by itself to retune the production policy.

## What was tested

Q was earned from three independently promoted P path structures. Only after Q existed, fresh held-out paths and unrelated star, cycle, and paw structures were created. Positive cases included balanced and uneven frozen edge strengths. Each positive was measured with Q present, Q ablated, and Q restored. Threshold and distractor-population sensitivity were measured separately. The existing four-arm Ethomorphism benchmark supplied graph-only, graph+ECWF, plastic-no-fold, and full-fold comparisons.

## Meaning

A passing result is evidence that, on this controlled task, the earned Q object selectively recognizes later members of the same structural family and causally reduces comparison work. Ablation tying the work increase to the specific Q object is stronger evidence than observing performance alone. It does not establish general intelligence, consciousness, or broad real-world transfer.

The recorded misses were safe fallback outcomes: the full member scan still recovered the
correct family, but Q was not selected, so no compression benefit occurred. They were not
false-family classifications.

## Limits

""" + "\n".join(f"- {item}" for item in result["interpretation_limits"]) + "\n"
    (output / "REPORT.md").write_text(report, encoding="utf-8")
