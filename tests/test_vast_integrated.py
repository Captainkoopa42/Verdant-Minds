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
    assert len(json.loads(original)["arms"]) == 5
    assert [x["arm"] for x in json.loads(original)["arms"]] == list(v.ARMS)
    assert all(x["teaching_experiences"] == 2 for x in json.loads(original)["arms"])
    assert json.loads(original)["arms"][0]["native_engine_cycles"] > 2
    assert json.loads(original)["arms"][4]["native_engine_cycles"] == 2
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
    # All five arms contain independent native checkpoints.
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
    assert "v5x_auto_p" in message
    assert "v5x_auto_pq" in message
    assert "DIAGNOSTICS ARE NOT GRADES" in message


def test_auto_p_respects_gates_and_uses_native_council(tmp_path):
    import hashlib
    from verdant_development import VerdantDevelopmentPipeline
    from verdant_kernel import EvidenceKind, ExperienceCommand, VerdantKernel
    from verdant_integrated.p_promotion import promote_eligible_p

    kernel = VerdantKernel(seed=1403, state_dim=48, run_label="automatic-p-test")
    development = VerdantDevelopmentPipeline()

    def command(i):
        return ExperienceCommand(
            event_key=f"auto-triad-{i}",
            source_ref="auto-p:supplied-testimony",
            modality="text",
            payload_sha256=hashlib.sha256(str(i).encode()).hexdigest(),
            feature_vector=(1.0, 0.0, 0.0),
            concept_labels=("kren", "tar", "vel"),
            confidence=1.0,
            semantic_evidence_kind=EvidenceKind.TESTIMONY,
            semantic_evidence_details={"author_supplied": True},
            metadata={"context_id": f"context-{i % 2}"},
        )

    for i in range(3):
        development.advance(kernel, command(i))
    before = kernel.fingerprint()
    refused = promote_eligible_p(kernel, maximum=4)
    assert refused["promoted"] == []
    assert kernel.fingerprint() == before
    for i in range(3, 6):
        development.advance(kernel, command(i))
    assert any(c.status.value == "eligible"
               for c in kernel.state.structure_candidates.values())
    original_semantics = (
        tuple(sorted(kernel.state.concepts)),
        tuple(sorted(kernel.state.relations)),
        tuple(sorted(kernel.state.claims)),
        tuple(sorted(kernel.state.evidence)),
    )
    result = promote_eligible_p(kernel, maximum=4)
    assert len(result["promoted"]) == 1
    assert len(kernel.state.structures) == 1
    assert len(kernel.state.structure_promotion_events) == 1
    assert result["promoted"][0]["council_decision_event_id"]
    after_semantics = (
        tuple(sorted(kernel.state.concepts)),
        tuple(sorted(kernel.state.relations)),
        tuple(sorted(kernel.state.claims)),
        tuple(sorted(kernel.state.evidence)),
    )
    assert after_semantics == original_semantics
    again = promote_eligible_p(kernel, maximum=4)
    assert not again["promoted"]
    with pytest.raises(ValueError):
        promote_eligible_p(kernel, maximum=9)


def test_real_five_arm_pack_promotes_only_gated_treatment(tmp_path):
    raw = json.loads(_pack())
    items = []
    for i in range(7):
        items.append(dict(
            item_id=f"triad-{i}", context_id=f"ctx-{i%2}",
            source_text="The instructor presents three related symbolic objects.",
            modality="text",
            concepts=[{"label": x} for x in ("kren", "tar", "vel")],
            relations=[], claims=[],
            feature_vector=[1.0] + [0.0] * 15,
            confidence=1.0,
            event_key=f"integrated-triad-{i}",
            semantic_evidence_kind="testimony",
            provenance={"synthetic": True},
        ))
    raw["sections"][0]["items"] = items
    pack = tmp_path / "triad.vcpack"
    pack.write_bytes(v._json(raw))
    root = tmp_path / "auto-comparison"
    v.start(root, pack, limit_sections=1, seeds=(81001,))
    results = json.loads((root / "results.json").read_bytes())
    arms = {entry["arm"]: entry for entry in results["arms"]}
    assert set(arms) == set(v.ARMS)
    for arm in ("v5", "v5x_observe", "kernel_only"):
        receipt = v._load_json(v._stage_path(root, 81001, arm, 1).with_suffix(".json"))
        assert receipt["metrics"]["structures"] == 0
        assert receipt["p_promotion"] is None
    receipt = v._load_json(v._stage_path(root, 81001, "v5x_auto_p", 1).with_suffix(".json"))
    assert receipt["metrics"]["structures"] >= 1
    assert receipt["metrics"]["structure_promotion_events"] >= 1
    assert len(receipt["p_promotion"]["promoted"]) >= 1
    assert receipt["p_promotion"]["native_quality_and_council_required"] is True
    assert arms["v5"]["semantic"] == arms["v5x_auto_p"]["semantic"]
    assert arms["v5"]["semantic"] == arms["v5x_auto_pq"]["semantic"]
    pq_receipt = v._load_json(v._stage_path(root, 81001, "v5x_auto_pq", 1).with_suffix(".json"))
    assert pq_receipt["metrics"]["structures"] >= 1
    assert pq_receipt["q_promotion"]["native_p_available"] >= 1
    assert pq_receipt["q_promotion"]["promoted"] == []
    assert pq_receipt["metrics"]["layered_structures"] == 0
    assert arms["v5"]["fingerprint"] != arms["v5x_auto_p"]["fingerprint"]
    assert v.resume(root).read_bytes() == (root / "results.json").read_bytes()
    tampered = receipt["p_promotion"]["promoted"][0]
    tampered["council_decision_event_id"] = "bogus"
    stage = v._stage_path(root, 81001, "v5x_auto_p", 1).with_suffix(".json")
    stage.write_bytes(v._json(receipt))
    with pytest.raises(v.StudyIntegrityError, match="Council provenance mismatch"):
        v.resume(root)



def test_q_waits_for_three_native_p_and_uses_native_council():
    import hashlib
    from verdant_development import VerdantDevelopmentPipeline
    from verdant_integrated.q_promotion import advance_q_from_new_p
    from verdant_kernel import EvidenceKind, ExperienceCommand, VerdantKernel
    from verdant_structures import VerdantStructurePipeline

    kernel = VerdantKernel(seed=1701, state_dim=16, run_label="native-q-auto-test")
    kernel.update_plasticity_policy(decay_rate=0.0, learning_rate=0.40)
    kernel.update_structure_policy(
        minimum_members=4, maximum_members=4,
        maximum_neighbors_per_seed=3,
        minimum_member_association_strength=0.20,
        minimum_reconstructability=0.25,
        minimum_internal_cohesion=0.20,
        minimum_recurrence_events=2, minimum_evidence_events=2,
    )
    kernel.update_hierarchy_policy(
        minimum_interaction_events=3,
        minimum_evidence_events=6,
        layered_probe_similarity=0.985,
    )
    dev = VerdantDevelopmentPipeline()
    structure = VerdantStructurePipeline()
    family = []
    for prefix in ("world-a", "world-b", "world-c"):
        letter = prefix[-1]
        edges = (
            (f"{letter}1", f"{letter}2"),
            (f"{letter}2", f"{letter}3"),
            (f"{letter}3", f"{letter}4"),
        )
        for repeat in range(2):
            for index, edge in enumerate(edges):
                key = f"{prefix}-{repeat}-{index}"
                dev.advance(kernel, ExperienceCommand(
                    event_key=key,
                    source_ref="user-independent-test-fixture",
                    modality="text",
                    payload_sha256=hashlib.sha256(key.encode()).hexdigest(),
                    feature_vector=(1.0, 0.0, 0.0),
                    concept_labels=edge,
                    confidence=1.0,
                    semantic_evidence_kind=EvidenceKind.TESTIMONY,
                    semantic_evidence_details={"synthetic_fixture": True},
                    metadata={"context_id": f"{prefix}-context-{repeat % 2}"},
                ))
        wanted = set(v for edge in edges for v in edge)
        candidate = max(
            (c for c in kernel.state.structure_candidates.values()
             if {kernel.state.concepts[cid].normalized_label
                 for cid in c.member_concept_ids} == wanted),
            key=lambda c: c.occurrence_count,
        )
        sid = structure.promote(kernel, candidate.candidate_id).event.structure_id
        family.append(sid)
        before_semantic = (
            tuple(sorted(kernel.state.concepts)),
            tuple(sorted(kernel.state.relations)),
            tuple(sorted(kernel.state.claims)),
            tuple(sorted(kernel.state.evidence)),
        )
        result = advance_q_from_new_p(kernel, newly_promoted_p_ids=(sid,))
        if len(family) < 3:
            assert result["interactions"] == []
            assert result["promoted"] == []
        else:
            assert len(result["interactions"]) == 3
            assert len(result["hierarchy_observations"]) >= 1
            assert len(result["promoted"]) == 1
            assert result["native_council_authorization_required"] is True
            assert result["promoted"][0]["council_decision_event_id"]
            assert len(kernel.state.layered_structures) == 1
        after_semantic = (
            tuple(sorted(kernel.state.concepts)),
            tuple(sorted(kernel.state.relations)),
            tuple(sorted(kernel.state.claims)),
            tuple(sorted(kernel.state.evidence)),
        )
        assert after_semantic == before_semantic

    fingerprint = kernel.fingerprint()
    once = advance_q_from_new_p(kernel, newly_promoted_p_ids=())
    assert not once["interactions"]
    assert not once["promoted"]
    assert kernel.fingerprint() == fingerprint
    with pytest.raises(ValueError, match="between"):
        advance_q_from_new_p(kernel, newly_promoted_p_ids=(), maximum_q_promotions=9)
    with pytest.raises(ValueError, match="distinct"):
        advance_q_from_new_p(kernel, newly_promoted_p_ids=(family[0], family[0]))
    with pytest.raises(ValueError, match="native P"):
        advance_q_from_new_p(kernel, newly_promoted_p_ids=("not-a-P",))



def test_five_arm_q_receipt_tamper_fails_closed(tmp_path):
    pack = tmp_path / "input.vcpack"
    pack.write_bytes(_pack())
    root = tmp_path / "q-integrity"
    v.start(root, pack, limit_sections=1, seeds=(81001,))
    target = v._stage_path(root, 81001, "v5x_auto_pq", 1).with_suffix(".json")
    receipt = v._load_json(target)
    assert receipt["q_promotion"] is not None
    receipt["q_promotion"]["native_p_sources"] = ["fabricated-p"]
    target.write_bytes(v._json(receipt))
    with pytest.raises(v.StudyIntegrityError, match="Q did not receive exactly"):
        v.resume(root)
