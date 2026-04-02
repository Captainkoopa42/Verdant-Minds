from __future__ import annotations

from verdant.system import VerdantConfig, VerdantSystem


def test_quick_extract_concepts_includes_unknown_words() -> None:
    system = VerdantSystem(VerdantConfig(seed=42, initialize_knowledge=False))
    system.memory_web.add_concept("water", stability=0.95)

    known, unknown = system._quick_extract_concepts("Water flows downhill and is inevitable.")

    assert "water" in known
    assert "flows" in unknown
    assert "downhill" in unknown
    assert "and" not in unknown


def test_activation_scales_with_novelty_and_familiarity() -> None:
    system = VerdantSystem(VerdantConfig(seed=42, initialize_knowledge=False))

    for _ in range(150):
        system.memory_web.add_concept("water", stability=0.99)
        system.memory_web.add_concept("flows", stability=0.98)
        system.memory_web.add_concept("downhill", stability=0.99)

    familiar_known, familiar_unknown = system._quick_extract_concepts("Water flows downhill.")
    familiar_novelty = system._compute_novelty(familiar_known, familiar_unknown)
    familiar_activation = system._compute_input_activation(
        familiar_known,
        familiar_unknown,
        familiar_novelty,
    )

    novel_known, novel_unknown = system._quick_extract_concepts(
        "Surrender is the strongest form of courage."
    )
    novel_novelty = system._compute_novelty(novel_known, novel_unknown)
    novel_activation = system._compute_input_activation(
        novel_known,
        novel_unknown,
        novel_novelty,
    )

    assert familiar_activation < 0.15
    assert novel_activation > 0.15
    assert novel_activation > familiar_activation
