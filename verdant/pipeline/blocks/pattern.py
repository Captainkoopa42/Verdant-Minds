"""PatternRecognitionBlock — keyword extraction, tension detection, entities.

Reads: ``sensory_input_section``
Writes: ``pattern_recognition_section``
"""

from __future__ import annotations

import keyword
import re
import time
from typing import Any, Dict, List, Set, Tuple

from verdant.pipeline.chunk import CognitiveChunk

_STOPWORDS: Set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "about", "it",
    "this", "that", "and", "or", "but", "if", "not", "no", "so", "than",
    "too", "very", "just", "i", "me", "my", "we", "our", "you", "your",
    "he", "she", "they", "them", "its", "what", "who", "where", "when", "why",
    "how", "which", "whom", "each", "every", "all", "any", "few", "more", "most",
    "other", "some", "such", "only", "own", "same", "these", "those", "both",
    "either", "neither", "during", "before", "after", "between", "through", "also",
}

# Opposition pairs → base tension strength
_OPPOSITION_PAIRS: Dict[Tuple[str, str], float] = {
    ("true", "false"): 1.0,
    ("good", "evil"): 0.95,
    ("good", "bad"): 0.9,
    ("benefit", "harm"): 0.85,
    ("fair", "unfair"): 0.9,
    ("privacy", "transparency"): 0.75,
    ("liberty", "security"): 0.7,
    ("rational", "emotional"): 0.5,
    ("certain", "uncertain"): 0.7,
    ("order", "chaos"): 0.8,
    ("self", "other"): 0.6,
    ("individual", "collective"): 0.65,
    ("freedom", "constraint"): 0.7,
    ("change", "stability"): 0.6,
}

_QUESTION_PATTERNS: Dict[str, List[str]] = {
    "factual": [r"\bwhat\b", r"\bwho\b", r"\bwhere\b", r"\bwhen\b"],
    "ethical": [r"\bshould\b", r"\bright\b.*\bwrong\b", r"\bethic"],
    "hypothetical": [r"\bwhat if\b", r"\bimagine\b", r"\bsuppose\b"],
    "causal": [r"\bwhy\b", r"\bbecause\b", r"\bcause\b"],
    "comparative": [r"\bcompare\b", r"\bbetter\b", r"\bworse\b", r"\bdifference\b"],
}

_PROGRAMMING_TERMS: Set[str] = {
    "class", "method", "function", "lambda", "dict", "list", "tuple", "object", "module",
    "import", "return", "yield", "while", "strict", "managed", "marker", "update", "linked",
    "metadata", "state", "cycle", "timestamp", "config", "parameter", "variable", "args", "kwargs",
}


class PatternRecognitionBlock:
    """Extracts keywords, concepts, oppositions, entities, and question type."""

    name: str = "PatternRecognition"

    def process(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Process patterns from sensory data."""
        sensory = chunk.get_section_content("sensory_input_section") or {}
        text: str = sensory.get("input_text", "")
        tokens: List[str] = sensory.get("tokens", [])
        metadata: Dict[str, Any] = sensory.get("metadata", {})

        is_self_reflection = bool(metadata.get("is_self_reflection"))
        keywords = self._extract_keywords(tokens, is_self_reflection=is_self_reflection)
        concepts = list(dict.fromkeys(keywords))  # dedup preserving order
        oppositions = self._detect_oppositions(concepts, tokens)
        tensions = self._compute_tensions(oppositions, text)
        question = self._classify_question(text)
        sentiment = sensory.get("sentiment_indicators", {})
        entities = self._extract_entities(text)

        chunk.update_section("pattern_recognition_section", {
            "keywords": keywords,
            "concepts": concepts,
            "concept_count": len(concepts),
            "oppositions": oppositions,
            "tension_coefficients": tensions,
            "max_tension": max(tensions.values()) if tensions else 0.0,
            "question_type": question.get("type", "statement"),
            "question_confidence": question.get("confidence", 0.0),
            "question_features": question.get("features", []),
            "sentiment": sentiment,
            "entities": entities,
            "timestamp": time.time(),
        })
        chunk.add_processing_step(self.name, "pattern_extraction", {
            "concept_count": len(concepts),
            "tension_count": len(tensions),
        })
        return chunk

    # ------------------------------------------------------------------

    @staticmethod
    def _is_noise_token(token: str, *, is_self_reflection: bool) -> bool:
        if not token:
            return True
        if token in _STOPWORDS:
            return True
        if len(token) <= 2:
            return True
        if token.isdigit():
            return True

        if not is_self_reflection:
            return False

        if token in _PROGRAMMING_TERMS:
            return True
        if keyword.iskeyword(token):
            return True
        if "_" in token and token.count("_") >= 1:
            return True
        if any(ch.isupper() for ch in token):
            return True
        return False

    @classmethod
    def _extract_keywords(cls, tokens: List[str], *, is_self_reflection: bool = False) -> List[str]:
        seen: set[str] = set()
        out: List[str] = []
        for raw_token in tokens:
            t = str(raw_token).strip().lower()
            if cls._is_noise_token(t, is_self_reflection=is_self_reflection):
                continue
            if t in seen:
                continue
            seen.add(t)
            out.append(t)
        return out

    @staticmethod
    def _detect_oppositions(concepts: List[str], tokens: List[str]) -> List[Dict[str, Any]]:
        all_words = set(concepts) | set(tokens)
        found: List[Dict[str, Any]] = []
        for (a, b), strength in _OPPOSITION_PAIRS.items():
            if a in all_words and b in all_words:
                found.append({"pair": (a, b), "base_strength": strength})
        # Negation-prefix detection
        for c in concepts:
            neg = f"not_{c}"
            if neg in all_words or f"non{c}" in all_words:
                found.append({"pair": (c, neg), "base_strength": 0.8})
        return found

    @staticmethod
    def _compute_tensions(oppositions: List[Dict[str, Any]], text: str) -> Dict[str, float]:
        tensions: Dict[str, float] = {}
        words = text.lower().split()
        for opp in oppositions:
            a, b = opp["pair"]
            base = opp["base_strength"]
            # Proximity factor
            a_positions = [i for i, w in enumerate(words) if a in w]
            b_positions = [i for i, w in enumerate(words) if b in w]
            proximity = 1.0
            if a_positions and b_positions:
                min_dist = min(abs(ai - bi) for ai in a_positions for bi in b_positions)
                proximity = min(1.0, 5.0 / max(min_dist, 1))
            # Contrastive markers
            contrastive = 1.0
            if re.search(r"\bbut\b|\bhowever\b|\byet\b|\balthough\b", text, re.I):
                contrastive = 1.2
            tensions[f"{a}_vs_{b}"] = min(1.0, base * proximity * contrastive)
        return tensions

    @staticmethod
    def _classify_question(text: str) -> Dict[str, Any]:
        if "?" not in text:
            return {"type": "statement", "confidence": 0.0, "features": []}
        best_type = "factual"
        best_score = 0.0
        features: List[str] = []
        for qtype, patterns in _QUESTION_PATTERNS.items():
            score = 0.0
            for pat in patterns:
                if re.search(pat, text, re.I):
                    score += 1.0
                    features.append(f"{qtype}:{pat}")
            score /= len(patterns)
            if score > best_score:
                best_score = score
                best_type = qtype
        return {"type": best_type, "confidence": min(1.0, best_score), "features": features}

    @staticmethod
    def _extract_entities(text: str) -> List[Dict[str, str]]:
        entities: List[Dict[str, str]] = []
        # Capitalised words heuristic
        for match in re.finditer(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text):
            entities.append({"text": match.group(), "type": "PROPER_NOUN"})
        return entities
