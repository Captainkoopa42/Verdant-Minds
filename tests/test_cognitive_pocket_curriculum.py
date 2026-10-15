"""Query-only frozen curriculum and exact native-checkpoint v2 CLI tests."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

import pytest

from test_cognitive_pocket_composition import composed_case
from verdant_kernel import save_checkpoint
from verdant_pockets import PocketIntegrityError
from verdant_pockets.composition import CompositionQuery
from verdant_pockets.curriculum import grade_frozen_tasks
from verdant_pockets.composition_cli import inspect_native_task


def test_frozen_curriculum_separates_grades_from_composition(composed_case):
    kernel, family, qid, names, bridge, pocket, query = composed_case
    frozen = kernel.fingerprint()
    tasks = [
        {"task_id": "01_full_chain", "source_concept_id": names["a1"], "target_concept_id": names["b4"], "maximum_hops": 9},
        {"task_id": "02_short_chain", "source_concept_id": names["a3"], "target_concept_id": names["b2"], "maximum_hops": 9},
        {"task_id": "03_reversed", "source_concept_id": names["b4"], "target_concept_id": names["a1"]},
        {"task_id": "04_decoy", "source_concept_id": names["a1"], "target_concept_id": names["c4"]},
        {"task_id": "05_unlicensed", "source_concept_id": names["a1"], "target_concept_id": names["b4"], "relation_type": "supports"},
        {"task_id": "06_swapped", "source_concept_id": names["b1"], "target_concept_id": names["a4"]},
    ]
    grades = {x["task_id"]: {"expected": "supported_composition" if x["task_id"] in ("01_full_chain","02_short_chain") else "abstain"} for x in tasks}
    report = grade_frozen_tasks(pocket, tasks, grades)
    assert report["confusion"] == {"true_positive": 2, "true_negative": 4, "false_positive": 0, "false_negative": 0}
    assert report["graded_accuracy"] == 1.0
    assert not any(result["proof"] for result in report["trials"] if not result["expected_positive"])
    assert all(result["evidence_refs"] for result in report["trials"] if result["expected_positive"])
    assert kernel.fingerprint() == frozen
    assert report == grade_frozen_tasks(pocket, list(reversed(tasks)), grades)


def test_frozen_grader_cannot_accept_task_injected_grade_or_bad_ids(composed_case):
    _, _, _, names, _, pocket, query = composed_case
    valid = [{"task_id": "A", "source_concept_id": names["a1"], "target_concept_id": names["b4"]}]
    with pytest.raises(PocketIntegrityError):
        grade_frozen_tasks(pocket, valid, {})
    with pytest.raises(PocketIntegrityError):
        grade_frozen_tasks(pocket, valid * 2, {"A":{"expected":"supported_composition"}})
    with pytest.raises(PocketIntegrityError):
        grade_frozen_tasks(pocket, valid, {"A":{"expected":"wrong label"}})


def test_native_cli_without_teacher_bridge_respects_original_memory_scope(composed_case, tmp_path):
    kernel, family, qid, names, bridge, pocket, query = composed_case
    vdk = tmp_path / "controlled_native.vdk"
    save_checkpoint(vdk, kernel.snapshot())
    original = vdk.read_bytes()
    out = tmp_path / "inspect.json"
    summary = inspect_native_task(vdk, out, q_index=0,
                                  source_label="a1", target_label="b4")
    assert summary["result"] == "supported_composition"
    assert summary["original_memory_unchanged"] is True
    report = json.loads(out.read_text(encoding="utf8"))
    assert report["experiment"]["selected_p_ids"] == list(family[:2])
    assert report["teacher_testimony_added"] is False
    assert report["source_checkpoint_sha256"] == hashlib.sha256(original).hexdigest()
    assert vdk.read_bytes() == original
    with pytest.raises(FileExistsError):
        inspect_native_task(vdk, out, q_index=0,
                            source_label="a1", target_label="b4")
    with pytest.raises(PocketIntegrityError):
        inspect_native_task(vdk, vdk, q_index=0,
                            source_label="a1", target_label="b4")
    assert vdk.read_bytes() == original


def test_native_cli_no_fake_labels_or_wrong_q_allowed(composed_case, tmp_path):
    kernel, family, qid, names, bridge, pocket, query = composed_case
    vdk = tmp_path / "original.vdk"
    save_checkpoint(vdk, kernel.snapshot())
    with pytest.raises(PocketIntegrityError):
        inspect_native_task(vdk, tmp_path / "bad.json", q_index=0,
                            source_label="bad", target_label="b4")
    with pytest.raises(PocketIntegrityError):
        inspect_native_task(vdk, tmp_path / "bad.json", q_index=90,
                            source_label="a1", target_label="b4")
    assert not (tmp_path / "bad.json").exists()
