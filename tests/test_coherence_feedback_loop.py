from usm import UnifiedSyntheticMind


def test_coherence_feedback_loop_carries_forward_and_adjusts_threshold():
    mind = UnifiedSyntheticMind(config={"initialize_knowledge": False})

    def fake_coherence(_chunk):
        return {
            "triangle_valid_at_alpha1": False,
            "alpha_crit_estimate": 0.5,
            "alpha_grid_used": [1.0],
            "violation_rate": 0.45,
            "housed_contradiction_index": 0.9,
            "triple_pqr": {"p": 0.6, "q": 0.4, "r": 0.7},
            "sampled_triplets": 4,
        }

    mind._compute_coherence_invariants = fake_coherence

    first_chunk = mind.process_input("First input to produce coherence telemetry")
    first_coherence = first_chunk.get_section_content("coherence_invariants_section")
    assert first_coherence["housed_contradiction_index"] == 0.9

    second_chunk = mind.process_input("Second input should consume previous coherence")
    forefront = second_chunk.get_section_content("forefront_king_section")
    assert isinstance(forefront, dict)

    coherence_influence = forefront.get("coherence_influence", {})
    assert coherence_influence.get("housed_contradiction_index") == 0.9
    assert coherence_influence.get("triangle_valid_at_alpha1") is False
    assert coherence_influence.get("violation_rate") == 0.45
    assert coherence_influence.get("threshold_adjustment") == 0.05

    assert forefront.get("phase_state") == "coherence_strained"
    assert forefront.get("high_geometric_tension") is True
