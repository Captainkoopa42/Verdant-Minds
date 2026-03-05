"""SensoryInputBlock — entry point for raw input processing.

Reads: (creates new section)
Writes: ``sensory_input_section``
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List

from verdant_v2.pipeline.chunk import CognitiveChunk

# Simple lexicon-based sentiment
_POSITIVE_WORDS = {"good", "great", "excellent", "wonderful", "happy", "love", "best", "beautiful", "enjoy", "helpful"}
_NEGATIVE_WORDS = {"bad", "terrible", "awful", "horrible", "sad", "hate", "worst", "ugly", "pain", "harmful"}
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "about", "it",
    "this", "that", "and", "or", "but", "if", "not", "no", "so", "than",
    "too", "very", "just", "i", "me", "my", "we", "our", "you", "your",
    "he", "she", "they", "them", "its",
}


class SensoryInputBlock:
    """Tokenises, scores complexity, and detects sentiment for raw text input."""

    name: str = "SensoryInput"

    def process(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Process raw input text and write ``sensory_input_section``."""
        existing = chunk.get_section_content("sensory_input_section") or {}
        raw_text: str = existing.get("input_text", "")
        metadata: Dict[str, Any] = existing.get("metadata", {})

        tokens = self._tokenize(raw_text)
        sentiment = self._detect_sentiment(raw_text)
        input_type = self._detect_input_type(raw_text)
        sentences = [s.strip() for s in re.split(r"[.!?]+", raw_text) if s.strip()]

        chunk.update_section("sensory_input_section", {
            "input_text": raw_text,
            "input_timestamp": time.time(),
            "metadata": metadata,
            "tokens": tokens,
            "token_count": len(tokens),
            "character_count": len(raw_text),
            "sentence_count": len(sentences),
            "sentences": sentences,
            "sentiment_indicators": sentiment,
            "input_type": input_type,
            "complexity_score": self._complexity_score(tokens, sentences),
        })
        chunk.add_processing_step(self.name, "sensory_processing", {
            "token_count": len(tokens),
            "input_type": input_type,
        })
        return chunk

    # ------------------------------------------------------------------

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"\b\w+\b", text.lower())

    @staticmethod
    def _detect_sentiment(text: str) -> Dict[str, float]:
        words = set(text.lower().split())
        pos = len(words & _POSITIVE_WORDS)
        neg = len(words & _NEGATIVE_WORDS)
        total = pos + neg or 1
        return {
            "positive_score": pos / total if total else 0.0,
            "negative_score": neg / total if total else 0.0,
            "net_sentiment": (pos - neg) / total if total else 0.0,
        }

    @staticmethod
    def _detect_input_type(text: str) -> str:
        if re.search(r"[\[{]", text):
            return "structured_data"
        return "text"

    @staticmethod
    def _complexity_score(tokens: List[str], sentences: List[str]) -> float:
        if not tokens:
            return 0.0
        unique = len(set(tokens))
        ratio = unique / len(tokens)
        avg_len = sum(len(t) for t in tokens) / len(tokens)
        sentence_factor = min(1.0, len(sentences) / 5)
        return min(1.0, 0.3 * ratio + 0.3 * min(avg_len / 8, 1.0) + 0.4 * sentence_factor)
