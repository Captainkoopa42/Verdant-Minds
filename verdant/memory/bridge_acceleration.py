"""Verdant-side bridge acceleration helpers.

These helpers extend bridge runtime behavior without modifying the upstream
`ethomorphic` package.
"""

from __future__ import annotations

import time
import hashlib
from types import MethodType
from typing import Any

import numpy as np

from ethomorphic.bridge.bridge import EthomorphicBridge


def install_fast_bridge_hooks(bridge: EthomorphicBridge) -> None:
    """Patch a bridge instance with optional fast co-activation linking."""
    if getattr(bridge, "_verdant_fast_bridge_installed", False):
        return

    bridge._verdant_fast_bridge_installed = True
    bridge._verdant_fast_bridge_enabled = False
    bridge._verdant_bridge_pairs_evaluated = 0
    bridge._verdant_last_activation_cycle = {}
    bridge._verdant_original_update_memory_from_ecwf = bridge.update_memory_from_ecwf
    bridge._verdant_original_assign_concept_mappings = bridge.assign_concept_mappings

    def assign_concept_mappings_deterministic(
        self: EthomorphicBridge,
        concept: str,
        is_ethical: bool | None = None,
    ) -> list[tuple[str, int, float]]:
        if is_ethical is None:
            is_ethical = self._is_ethical_concept(concept)

        cog_dims = self.ecwf.num_cognitive_dims
        eth_dims = self.ecwf.num_ethical_dims
        base_seed = int(getattr(self.ecwf, "random_state", 0) or 0)
        digest = hashlib.sha256(f"{concept}|{base_seed}".encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], "big") % (2**32)
        rng = np.random.default_rng(seed)

        dimensions: list[tuple[str, int, float]] = []
        if is_ethical:
            primary = int(rng.integers(0, eth_dims))
            dimensions.append(("ethical", primary, 0.8 + float(rng.random()) * 0.2))
            for _ in range(min(2, eth_dims - 1)):
                sec = int(rng.integers(0, eth_dims))
                while sec == primary:
                    sec = int(rng.integers(0, eth_dims))
                dimensions.append(("ethical", sec, 0.3 + float(rng.random()) * 0.3))
            dimensions.append(("cognitive", int(rng.integers(0, cog_dims)), 0.2 + float(rng.random()) * 0.2))
        else:
            primary = int(rng.integers(0, cog_dims))
            dimensions.append(("cognitive", primary, 0.8 + float(rng.random()) * 0.2))
            for _ in range(min(2, cog_dims - 1)):
                sec = int(rng.integers(0, cog_dims))
                while sec == primary:
                    sec = int(rng.integers(0, cog_dims))
                dimensions.append(("cognitive", sec, 0.3 + float(rng.random()) * 0.3))
            dimensions.append(("ethical", int(rng.integers(0, eth_dims)), 0.1 + float(rng.random()) * 0.2))

        self.concept_dimension_mapping[concept] = dimensions
        self.activation_history.setdefault(concept, [])
        return dimensions

    bridge.assign_concept_mappings = MethodType(assign_concept_mappings_deterministic, bridge)

    def update_memory_from_ecwf_fast(
        self: EthomorphicBridge,
        cognitive_state: np.ndarray,
        ethical_state: np.ndarray,
        t: float,
    ) -> dict[str, Any]:
        if cognitive_state.ndim == 1:
            cognitive_state = cognitive_state.reshape(1, 1, -1)
        if ethical_state.ndim == 1:
            ethical_state = ethical_state.reshape(1, 1, -1)

        wave_output = self.ecwf.compute_ecwf(cognitive_state, ethical_state, t)
        magnitude = np.abs(wave_output).flatten()
        phase = np.angle(wave_output).flatten()
        entropy = self.ecwf.calculate_entropy(wave_output)

        activations: dict[str, float] = {}
        for concept, mappings in self.concept_dimension_mapping.items():
            activation = 0.0
            for mtype, dim_idx, weight in mappings:
                if mtype == "cognitive" and dim_idx < cognitive_state.shape[-1]:
                    activation += cognitive_state[0, 0, dim_idx] * weight
                elif mtype == "ethical" and dim_idx < ethical_state.shape[-1]:
                    activation += ethical_state[0, 0, dim_idx] * weight

            if len(magnitude) > 0:
                activation *= magnitude[0]
                activation *= max(0.2, 1.0 - entropy / 5.0)
                activation *= 0.5 + 0.5 * np.cos(phase[0])

            if activation > 0.2:
                activations[concept] = min(1.0, activation)

        updated_concepts: list[str] = []
        created_concepts: list[str] = []
        current_cycle = int(t)
        newly_activated: set[str] = set()

        for concept, activation in activations.items():
            existing = self.memory.get_concept(concept)
            if existing is not None:
                self.memory.reinforce(concept, activation * self.influence_factor)
                updated_concepts.append(concept)
            else:
                self.memory.add_concept(
                    concept,
                    stability=activation * 0.5,
                    metadata={"creation_time": time.time()},
                )
                created_concepts.append(concept)
                self.assign_concept_mappings(concept)

            last_cycle = int(self._verdant_last_activation_cycle.get(concept, -10**9))
            if last_cycle != current_cycle - 1:
                newly_activated.add(concept)
            self._verdant_last_activation_cycle[concept] = current_cycle
            self.activation_history.setdefault(concept, [])
            self.activation_history[concept].append((time.time(), activation))

        concepts_list = list(activations.keys())
        pair_evaluated = 0
        for idx, c1 in enumerate(concepts_list):
            for c2 in concepts_list[idx + 1:]:
                if self._verdant_fast_bridge_enabled and c1 not in newly_activated and c2 not in newly_activated:
                    continue
                pair_evaluated += 1
                self.memory.connect(c1, c2, min(activations[c1], activations[c2]))
        self._verdant_bridge_pairs_evaluated = pair_evaluated

        self.metrics["ecwf_to_memory_transfers"] += 1
        self.metrics["concepts_activated"] += len(updated_concepts)
        self.metrics["last_update"] = time.time()

        return {
            "activated_concepts": activations,
            "updated_concepts": updated_concepts,
            "created_concepts": created_concepts,
            "wave_magnitude": magnitude.tolist(),
            "wave_phase": phase.tolist(),
            "entropy": entropy,
        }

    bridge.update_memory_from_ecwf = MethodType(update_memory_from_ecwf_fast, bridge)


def set_fast_bridge_enabled(bridge: EthomorphicBridge, enabled: bool) -> None:
    """Toggle fast bridge behavior for the patched bridge instance."""
    install_fast_bridge_hooks(bridge)
    bridge._verdant_fast_bridge_enabled = bool(enabled)


def get_fast_bridge_state(bridge: EthomorphicBridge) -> dict[str, Any]:
    """Return persisted Verdant-side acceleration state for checkpoints."""
    return {
        "fast_bridge_enabled": bool(getattr(bridge, "_verdant_fast_bridge_enabled", False)),
        "bridge_pairs_evaluated": int(getattr(bridge, "_verdant_bridge_pairs_evaluated", 0)),
        "last_activation_cycle": dict(getattr(bridge, "_verdant_last_activation_cycle", {})),
    }


def restore_fast_bridge_state(bridge: EthomorphicBridge, state: dict[str, Any] | None) -> None:
    """Reinstall hooks and restore persisted acceleration state."""
    install_fast_bridge_hooks(bridge)
    data = state or {}
    bridge._verdant_fast_bridge_enabled = bool(data.get("fast_bridge_enabled", False))
    bridge._verdant_bridge_pairs_evaluated = int(data.get("bridge_pairs_evaluated", 0))
    bridge._verdant_last_activation_cycle = {
        str(concept): int(cycle)
        for concept, cycle in dict(data.get("last_activation_cycle", {})).items()
    }
