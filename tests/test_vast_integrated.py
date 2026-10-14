"""Tiny controlled tests; never run the user curriculum or background experiments."""
import json
import pytest

from verdant_integrated import vast as v


def _pack(two=False):
    def section(n):
        a, b, c = ("alpha", "beta", "gamma") if n == 1 else ("gamma", "delta", "epsilon")
        items = []
        for i, (x, y) in enumerate(((a, b), (b, c)), 1):
            items.append(dict(
                item_id=f"item_{n}_{i}", context_id=f"context_{n}_{i}",
                source_text=f"Teacher states {x} supports {y}.",
                modality="text", concepts=[dict(label=x), dict(label=y)],
                relations=[dict(source=x, target=y, relation="depends_on",
                                directed=True, weight=0.8, confidence=0.9)],
                claims=[], event_key=f"tiny-{n}-{i}",
                semantic_evidence_kind="testimony",
                provenance={"truth_status":"synthetic_teacher_testimony","direct_observation":False},
            ))
        return dict(section_id=f"section_{n}", title=f"Section {n}",
                    description="Test only", enabled=True, items=items,
                    tests=[dict(test_id=f"probe_{n}", cue_labels=[a,b])])
    return json.dumps(dict(schema="verdant.curriculum.pack.v1",
                           title="Synthetic preflight", description="No semantic truth",
                           state_dim=16,
                           sections=[section(1), section(2)] if two else [section(1)]),
                      ensure_ascii=False).encode("utf-8")


def test_one_section_full_v5_and_v5x_observer_equivalent(tmp_path):
    pack = tmp_path / "input.vcpack"
    pack.write_bytes(_pack())
    root = tmp_path / "cohort"
    output = v.start(root, pack, limit_sections=1, seeds=(81001,))
    original = output.read_bytes()
    assert v.resume(root).read_bytes() == original
    assert len(json.loads(original)["arms"]) == 3
    assert [x["arm"] for x in json.loads(original)["arms"]] == list(v.ARMS)
    assert all(x["teaching_experiences"] == 2 for x in json.loads(original)["arms"])
    assert json.loads(original)["arms"][0]["native_engine_cycles"] > 2
    assert json.loads(original)["arms"][2]["native_engine_cycles"] == 2
    canonical = json.loads((root / "stages" / "seed-81001" / "v5" / "001.json").read_bytes())
    diagnostics = canonical["observations"]
    assert diagnostics["probe_type"] == "read_only_compilation_inspection"
    assert len(diagnostics["diagnostic_probes"]) == 1
    assert diagnostics["dependency_gap_candidates"] == 0
    assert diagnostics["raw_depends_on_relations"] >= 1
    assert canonical["metrics"]["obligation_kernels"] == 0
    assert v.status(root) is None
    assert (root / "curriculum.vcpack").read_bytes() == pack.read_bytes()


def test_resumption_after_section_checkpoint(tmp_path, monkeypatch):
    pack = tmp_path / "input.vcpack"
    pack.write_bytes(_pack(two=True))
    root = tmp_path / "interrupted"
    original_advance = v.VerdantDevelopmentPipeline.advance
    interrupted = [False]

    def stop_in_second_section(self, kernel, command):
        if (not interrupted[0] and
            len(kernel.state.processed_event_keys) == 2 and
            command.event_key == "tiny-2-1"):
            interrupted[0] = True
            raise InterruptedError("Intentional fault")
        return original_advance(self, kernel, command)

    monkeypatch.setattr(v.VerdantDevelopmentPipeline, "advance",
                        stop_in_second_section)
    with pytest.raises(InterruptedError, match="Intentional"):
        v.start(root, pack, limit_sections=2, seeds=(81001,))
    assert (root / "stages" / "seed-81001" / "v5" / "001.vdk").exists()
    assert not (root / "results.json").exists()
    monkeypatch.setattr(v.VerdantDevelopmentPipeline, "advance", original_advance)
    resumed = v.resume(root)
    fresh = v.start(tmp_path / "fresh", pack, limit_sections=2, seeds=(81001,))
    assert resumed.read_bytes() == fresh.read_bytes()
    assert v.resume(root).read_bytes() == resumed.read_bytes()


def test_detects_stage_tampering_and_source_changes(tmp_path, monkeypatch):
    pack = tmp_path / "input.vcpack"
    pack.write_bytes(_pack())
    root = tmp_path / "studied"
    v.start(root, pack, limit_sections=1, seeds=(81001,))
    receipt = root / "stages" / "seed-81001" / "v5" / "001.json"
    original = receipt.read_bytes()
    data = json.loads(original)
    data["metrics"]["cycle"] = 100
    receipt.write_bytes(v._json(data))
    with pytest.raises(v.StudyIntegrityError, match="Checkpoint metrics"):
        v.resume(root)
    receipt.write_bytes(original)
    old = v._manifest

    def drift(*args, **kwargs):
        result = old(*args, **kwargs)
        result["source_sha256"]["requirements-lock.txt"] = "0" * 64
        return result
    monkeypatch.setattr(v, "_manifest", drift)
    with pytest.raises(v.StudyIntegrityError, match="source code"):
        v.resume(root)


def test_rejects_grammar_scaffold_and_duplicated_event_keys(tmp_path):
    raw = json.loads(_pack())
    raw["language_scaffold"] = dict(grammar_rules=["S_V_O"], lexicon=[])
    with pytest.raises(v.StudyIntegrityError, match="grammar"):
        v._plan(v._json(raw), 1)
    raw = json.loads(_pack())
    raw["sections"][0]["items"][1]["event_key"] = raw["sections"][0]["items"][0]["event_key"]
    with pytest.raises(ValueError, match="Duplicate"):
        v._plan(v._json(raw), 1)
    with pytest.raises(ValueError, match="exceeds"):
        v._plan(_pack(), 2)


def test_no_reuse_of_output_directory(tmp_path):
    pack = tmp_path / "input.vcpack"
    pack.write_bytes(_pack())
    root = tmp_path / "cohort"
    v.start(root, pack, limit_sections=1, seeds=(81001,))
    with pytest.raises(FileExistsError):
        v.start(root, pack, limit_sections=1, seeds=(81001,))
    # All three arms contain independent native checkpoints.
    for arm in v.ARMS:
        assert (root / "stages" / "seed-81001" / arm / "001.vdk").is_file()
        assert (root / "stages" / "seed-81001" / arm / "001.json").is_file()



def test_preview_and_verified_report(tmp_path, capsys):
    pack = tmp_path / "input.vcpack"
    pack.write_bytes(_pack())
    v.preview(pack, limit_sections=1)
    preview_output = capsys.readouterr().out
    assert "Teaching experiences: 2" in preview_output
    root = tmp_path / "cohort"
    v.start(root, pack, limit_sections=1, seeds=(81001,))
    v.report(root)
    message = capsys.readouterr().out
    assert "experiences native_cycles" in message
    assert "v5x_observe" in message
    assert "DIAGNOSTICS ARE NOT GRADES" in message
