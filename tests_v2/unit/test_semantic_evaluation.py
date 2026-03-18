from __future__ import annotations

import json
from pathlib import Path

from analysis.extract_emergent_concepts import extract_emergent_concepts
from analysis.semantic_evaluation import clean_emergent_name, evaluate_semantics


def test_extract_emergent_concepts(tmp_path: Path) -> None:
    state = {
        "memory_web": {
            "memory_store": {
                "ethics": {"connections": [["autonomy", 0.9]], "first_seen": 0.0, "access_count": 3, "metadata": {}},
                "autonomy": {"connections": [["ethics", 0.9]], "first_seen": 0.1, "access_count": 4, "metadata": {}},
                "responsibility": {"connections": [["ethics", 0.8]], "first_seen": 0.2, "access_count": 2, "metadata": {}},
                "Emergent_ethics_autonomy_abc123": {
                    "connections": [["ethics", 0.99], ["autonomy", 0.98], ["responsibility", 0.97]],
                    "first_seen": 1.2,
                    "access_count": 8,
                    "metadata": {"creation_time": 1.2, "parent_concepts": ["ethics", "autonomy", "responsibility"]},
                },
                "Emergent_mystery_bridge_def456": {
                    "connections": [["autonomy", 0.95], ["responsibility", 0.85], ["Emergent_ethics_autonomy_abc123", 0.99]],
                    "first_seen": 2.5,
                    "access_count": 5,
                    "metadata": {"creation_time": 2.5},
                },
            },
            "edges": [
                ["ethics", "autonomy", 0.9],
                ["Emergent_ethics_autonomy_abc123", "ethics", 0.99],
                ["Emergent_ethics_autonomy_abc123", "autonomy", 0.98],
                ["Emergent_ethics_autonomy_abc123", "responsibility", 0.97],
                ["Emergent_mystery_bridge_def456", "autonomy", 0.95],
                ["Emergent_mystery_bridge_def456", "responsibility", 0.85],
                ["Emergent_mystery_bridge_def456", "Emergent_ethics_autonomy_abc123", 0.99],
            ],
        }
    }
    basins = {
        "basins": [
            {"basin_id": "basin_0", "nodes": ["ethics", "autonomy", "Emergent_ethics_autonomy_abc123"]},
            {"basin_id": "basin_1", "nodes": ["responsibility", "Emergent_mystery_bridge_def456"]},
        ]
    }
    state_path = tmp_path / "state.json"
    basins_path = tmp_path / "basins.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    basins_path.write_text(json.dumps(basins), encoding="utf-8")

    extracted = extract_emergent_concepts(state_path, basins_path)

    assert extracted["total_emergent"] == 2
    assert extracted["total_seeded"] == 3
    concept_map = {concept["name"]: concept for concept in extracted["concepts"]}
    assert concept_map["Emergent_ethics_autonomy_abc123"]["parents"] == ["ethics", "autonomy", "responsibility"]
    assert concept_map["Emergent_ethics_autonomy_abc123"]["basin_id"] == "basin_0"
    assert concept_map["Emergent_mystery_bridge_def456"]["parents"][:2] == ["autonomy", "responsibility"]
    assert concept_map["Emergent_mystery_bridge_def456"]["basin_id"] == "basin_1"


def test_local_scoring() -> None:
    payload = {
        "state_path": "mock_state.json",
        "concepts": [
            {
                "name": "Emergent_ethics_autonomy_abc123",
                "parents": ["ethics", "autonomy", "responsibility"],
                "creation_time": 1.0,
                "access_count": 10,
                "connection_count": 4,
                "basin_id": "basin_0",
            }
        ],
    }

    result = evaluate_semantics(payload, mode="local")
    assert result["per_concept"][0]["score"] >= 0.6
    assert result["per_concept"][0]["rating"] == "meaningful"


def test_local_scoring_random() -> None:
    payload = {
        "state_path": "mock_state.json",
        "concepts": [
            {
                "name": "Emergent_xyz_qrs_abc123",
                "parents": ["consciousness", "time", "growth"],
                "creation_time": 1.0,
                "access_count": 5,
                "connection_count": 3,
                "basin_id": "basin_1",
            }
        ],
    }

    result = evaluate_semantics(payload, mode="local")
    assert result["per_concept"][0]["score"] < 0.6
    assert result["per_concept"][0]["rating"] != "meaningful"


def test_name_cleaning() -> None:
    assert clean_emergent_name("Emergent_abstraction_autonomy_a1d776") == ["abstraction", "autonomy"]
    assert clean_emergent_name("Emergent_boundary_basin_0_basin_1_42") == ["boundary", "basin_0", "basin_1"]
