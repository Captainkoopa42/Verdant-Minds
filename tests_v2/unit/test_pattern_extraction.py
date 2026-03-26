from __future__ import annotations

from verdant_v2.pipeline.blocks.pattern import PatternRecognitionBlock


def test_extract_keywords_keeps_natural_language_content_words() -> None:
    tokens = ["water", "flows", "downhill", "and", "fire", "is", "hot"]

    keywords = PatternRecognitionBlock._extract_keywords(tokens)

    assert "water" in keywords
    assert "fire" in keywords
    assert "flows" in keywords
    assert "downhill" in keywords
    assert "and" not in keywords
    assert "is" not in keywords


def test_extract_keywords_filters_self_reflection_programming_noise() -> None:
    tokens = ["water", "strict", "while", "managed", "marker", "update", "linked", "coherence"]

    keywords = PatternRecognitionBlock._extract_keywords(tokens, is_self_reflection=True)

    assert "water" in keywords
    assert "coherence" in keywords
    for noise in ("strict", "while", "managed", "marker", "update", "linked"):
        assert noise not in keywords
