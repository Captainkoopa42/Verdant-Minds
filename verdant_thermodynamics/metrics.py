from __future__ import annotations

import math
import re
from collections.abc import Sequence

from verdant_kernel import ExperienceCommand, VerdantKernel, WorkspaceAdmissionReport

from .models import (
    EnvironmentMeasurement,
    FieldEntropyMeasurement,
    InputComplexityMeasurement,
    MemoryComplexityMeasurement,
)

_TOKEN_RE = re.compile(r"[A-Za-z0-9_']+")
_EPS = 1e-15


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def normalized_shannon_from_nonnegative(weights: Sequence[float]) -> tuple[float, float]:
    """Return normalized Shannon entropy and total mass.

    The entropy is normalized by ``log(N)`` so it lies in ``[0, 1]`` for
    ``N > 1``.  A zero-mass or one-bin distribution has entropy 0.  This is a
    dimensionless shape statistic, not thermodynamic entropy in physical units.
    """

    cleaned = [max(0.0, float(value)) for value in weights]
    total = float(sum(cleaned))
    if total <= _EPS or len(cleaned) <= 1:
        return 0.0, total
    probabilities = [value / total for value in cleaned if value > _EPS]
    if len(probabilities) <= 1:
        return 0.0, total
    entropy = -sum(probability * math.log(probability) for probability in probabilities)
    maximum = math.log(len(cleaned))
    if maximum <= _EPS:
        return 0.0, total
    return clamp01(entropy / maximum), total


def field_entropy(kernel: VerdantKernel) -> FieldEntropyMeasurement:
    powers = [
        float(real) * float(real) + float(imag) * float(imag)
        for real, imag in zip(kernel.state.field.real, kernel.state.field.imag)
    ]
    h_sys, total_power = normalized_shannon_from_nonnegative(powers)
    return FieldEntropyMeasurement(
        state_dim=kernel.state.field.state_dim,
        total_power=total_power,
        h_sys=h_sys,
    )


def input_complexity(command: ExperienceCommand) -> InputComplexityMeasurement:
    features = tuple(float(value) for value in command.feature_vector)
    feature_power = [value * value for value in features]
    feature_entropy, _ = normalized_shannon_from_nonnegative(feature_power)
    nonzero = sum(1 for value in features if abs(value) > _EPS)
    density = clamp01(nonzero / max(1, len(features)))

    sentence = command.metadata.get("sentence") if isinstance(command.metadata, dict) else None
    if command.modality.lower() == "text" and isinstance(sentence, str):
        token_count = len(_TOKEN_RE.findall(sentence))
        # Exact V4 compatibility adapter: token_count / 100, bounded to [0, 1].
        token_complexity = clamp01(token_count / 100.0)
        c_input = token_complexity
        revision = "text_token_count_v4_compat_1"
    else:
        token_count = None
        token_complexity = None
        # Non-text/synthetic commands do not have a V4 token count.  Keep the
        # adapter explicit and bounded rather than silently inventing tokens.
        c_input = clamp01((feature_entropy + density) / 2.0)
        revision = "feature_distribution_v1"

    return InputComplexityMeasurement(
        adapter_revision=revision,
        modality=command.modality,
        feature_count=len(features),
        nonzero_feature_count=nonzero,
        feature_density=density,
        feature_entropy=feature_entropy,
        token_count=token_count,
        token_complexity=token_complexity,
        c_input=c_input,
    )


def memory_complexity(
    kernel: VerdantKernel,
    *,
    candidate_scope_count: int,
) -> MemoryComplexityMeasurement:
    active_concepts: set[str] = set()
    for item in kernel.state.workspace_items.values():
        active_concepts.update(
            ref for ref in item.binding_refs if ref in kernel.state.concepts
        )
    active_items = len(kernel.state.workspace_items)
    policy = kernel.state.workspace_policy
    allocated = float(sum(item.allocated_resource for item in kernel.state.workspace_items.values()))
    occupancy = clamp01(active_items / max(1, policy.max_active_items))
    resource_load = clamp01(allocated / max(_EPS, float(policy.resource_budget)))
    # V4 used activated_concept_count / 10.  In V5 "activated" is mapped to
    # concept bindings in the bounded shared workspace, never total graph size.
    c_memory = clamp01(len(active_concepts) / 10.0)
    return MemoryComplexityMeasurement(
        candidate_scope_count=max(0, int(candidate_scope_count)),
        active_workspace_items=active_items,
        active_workspace_concepts=len(active_concepts),
        workspace_item_occupancy=occupancy,
        allocated_resource=allocated,
        resource_load=resource_load,
        c_memory=c_memory,
    )


def environmental_uncertainty(
    report: WorkspaceAdmissionReport | None,
) -> EnvironmentMeasurement:
    assessments = tuple(report.assessments) if report is not None else ()
    if not assessments:
        return EnvironmentMeasurement(
            candidate_count=0,
            mean_prediction_error=0.0,
            mean_novelty=0.0,
            mean_contradiction_pressure=0.0,
            h_env=0.0,
        )

    count = len(assessments)
    prediction = sum(item.candidate.signals.prediction_error for item in assessments) / count
    novelty = sum(item.candidate.signals.novelty for item in assessments) / count
    contradiction = (
        sum(item.candidate.signals.contradiction_pressure for item in assessments) / count
    )
    # V5-native uncertainty proxy.  Components remain separately exported so
    # null experiments can detect if this aggregate hides a trivial driver.
    h_env = clamp01((prediction + novelty + contradiction) / 3.0)
    return EnvironmentMeasurement(
        candidate_count=count,
        mean_prediction_error=clamp01(prediction),
        mean_novelty=clamp01(novelty),
        mean_contradiction_pressure=clamp01(contradiction),
        h_env=h_env,
    )
