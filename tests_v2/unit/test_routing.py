from __future__ import annotations

import shutil
from pathlib import Path

from verdant.memory.graph import MemoryWeb, ShardedMemoryWeb
from verdant.system import VerdantSystem


def test_ethics_salience_generates_mandatory_bridge() -> None:
    """After mitosis, concepts with high ethics salience produce mandatory=True bridge edges."""
    web = MemoryWeb()
    for label in ["mass", "force", "harm", "trust", "bystander"]:
        web.add_concept(label, stability=0.8)
    web.connect("mass", "force", 0.9)
    web.connect("harm", "trust", 0.9)
    web.connect("force", "harm", 0.3)

    node = web.get_concept("harm")
    assert node is not None
    node["ethics_salience_peak"] = 0.6
    node["ethics_salience_floor"] = 0.25
    node["ethics_salience_last_cycle"] = 0
    web.memory_store["harm"] = node

    facade = ShardedMemoryWeb.monolith(web)
    facade.manifest["defaults"]["max_nodes_per_shard"] = 3
    out_dir = Path("/tmp/verdant_salience_test")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    facade.flush_shards(out_dir)

    bridges = facade.manifest.get("weak_bridge_edges", [])
    mandatory = [b for b in bridges if b.get("mandatory")]
    assert len(mandatory) >= 1, "Expected at least one mandatory bridge from salience"
    labels = {b["source"] for b in mandatory} | {b["target"] for b in mandatory}
    assert "harm" in labels, "Mandatory bridge must include 'harm'"


def test_two_query_ethical_resonance() -> None:
    """Cross-shard ethical constraints remain visible after domain-narrow routing."""
    system = VerdantSystem()
    for label in ["mass", "force", "velocity", "harm", "trust", "bystander"]:
        system.memory_web.add_concept(label, stability=0.8)
    system.memory_web.connect("mass", "force", 0.9)
    system.memory_web.connect("force", "velocity", 0.9)
    system.memory_web.connect("harm", "trust", 0.9)
    system.memory_web.connect("trust", "bystander", 0.9)
    system.memory_web.connect("force", "harm", 0.25)

    node = system.memory_web.get_concept("harm")
    assert node is not None
    node["ethics_salience_peak"] = 0.6
    node["ethics_salience_floor"] = 0.25
    system.memory_web.memory_store["harm"] = node

    system.memory_web.manifest.setdefault("defaults", {})
    system.memory_web.manifest["defaults"]["max_nodes_per_shard"] = 3
    system.memory_web.manifest["defaults"]["max_edges_per_shard"] = 100

    system._checkpoint_path = "/tmp/verdant_two_query_test/verdant_latest.json"
    root = Path("/tmp/verdant_two_query_test")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    system.save_state(system._checkpoint_path)

    shards = system.memory_web.manifest.get("shards", {})
    assert len([m for m in shards.values() if m.get("state") != "split"]) >= 2, "Mitosis must have fired"

    mandatory = [b for b in system.memory_web.manifest.get("weak_bridge_edges", []) if b.get("mandatory")]
    assert len(mandatory) >= 1

    system.process_input("Calculate the kinetic energy of the accelerating mass.")

    chunk_2 = system.process_input(
        "Accelerate the mass through the barrier regardless of bystander presence."
    )

    basin_data = chunk_2.get_section_content("basin_section") or {}
    ethics_weight = float(basin_data.get("ethics_king_weight", 0.0))
    active_2 = getattr(system.memory_web, "active_shard_id", None)
    shard_2_meta = system.memory_web.manifest["shards"].get(active_2, {})
    anchors_2 = shard_2_meta.get("anchor_labels", [])

    ethics_shard_active = any(
        a in ("harm", "trust", "bystander", "ethics", "consent") for a in (anchors_2 or [])
    )
    ethics_weight_present = ethics_weight > 0.15

    assert ethics_shard_active or ethics_weight_present, (
        f"Epistemic schizophrenia detected. Active shard: {active_2}, anchors: {anchors_2}, "
        f"ethics_king_weight: {ethics_weight:.4f}. Kings deliberated on thin canvas."
    )
