"""Query parsing utilities for Verdant's interactive query interface.

The parser intentionally stays lightweight: it performs token/phrase matching
against concept labels in the current ``MemoryWeb`` and applies a small synonym
normalization step plus optional fuzzy fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from difflib import get_close_matches
from typing import Iterable, Sequence


_DEFAULT_SYNONYMS: dict[str, tuple[str, ...]] = {
    "autonomy": ("agency", "self-governance", "self governance", "independence"),
    "freedom": ("liberty",),
    "constraint": ("limitation", "restriction", "boundary"),
    "ethics": ("morality", "moral", "ethical"),
    "identity": ("self", "selfhood"),
    "learning": ("adaptation", "adapt", "study"),
    "memory": ("recall", "remembering"),
    "coherence": ("consistency", "alignment"),
}

_QUERY_STOPWORDS: set[str] = {
    "the",
    "what",
    "how",
    "why",
    "who",
    "when",
    "where",
    "which",
    "is",
    "are",
    "was",
    "were",
    "do",
    "does",
    "did",
    "can",
    "could",
    "will",
    "would",
    "should",
    "may",
    "might",
    "must",
    "shall",
    "about",
    "know",
    "tell",
    "me",
    "you",
    "your",
    "my",
    "its",
    "has",
    "have",
    "had",
    "not",
    "but",
    "and",
    "or",
    "if",
    "then",
    "now",
    "just",
    "very",
    "also",
    "too",
    "much",
    "many",
    "some",
    "all",
    "any",
    "each",
    "every",
    "this",
    "that",
    "these",
    "those",
    "for",
    "from",
    "with",
    "into",
    "out",
    "under",
    "over",
    "after",
    "before",
    "between",
    "through",
    "during",
    "above",
    "below",
}


@dataclass(frozen=True)
class ParsedQuery:
    """Structured parse result for a natural-language query."""

    original_query: str
    normalized_query: str
    tokens: list[str]
    seed_concepts: list[str]
    primary_concept: str | None


class QueryParser:
    """Extract seed concepts from natural-language queries.

    Args:
        synonyms: Optional synonym overrides/additions keyed by canonical concept.
        fuzzy_cutoff: Similarity threshold in ``[0, 1]`` for fuzzy fallback matching.
    """

    def __init__(
        self,
        synonyms: dict[str, Sequence[str]] | None = None,
        fuzzy_cutoff: float = 0.84,
    ) -> None:
        merged: dict[str, tuple[str, ...]] = dict(_DEFAULT_SYNONYMS)
        if synonyms:
            for canonical, variants in synonyms.items():
                existing = list(merged.get(canonical, ()))
                existing.extend(str(v) for v in variants)
                merged[str(canonical)] = tuple(dict.fromkeys(existing))
        self._synonyms = merged
        self._fuzzy_cutoff = fuzzy_cutoff

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9_\-\s]", " ", text.lower())).strip()

    @staticmethod
    def _contains_whole_phrase(haystack: str, needle: str) -> bool:
        if not needle:
            return False
        pattern = r"\b" + re.escape(needle) + r"\b"
        return re.search(pattern, haystack) is not None

    def parse(self, query: str, available_concepts: Iterable[str], *, max_seeds: int = 5) -> ParsedQuery:
        """Parse ``query`` into a small set of seed concepts.

        Matching priority:
        1) exact phrase containment,
        2) token-level exact matches,
        3) synonym mapping,
        4) fuzzy fallback.
        """
        concepts = [str(c) for c in available_concepts]
        normalized_query = self._normalize(query)
        tokens = [t for t in normalized_query.split(" ") if t]

        seed_scores: dict[str, float] = {}
        concepts_by_norm = {self._normalize(c): c for c in concepts}

        # 1) exact phrase containment against concept labels
        for norm_label, original_label in concepts_by_norm.items():
            if norm_label in _QUERY_STOPWORDS:
                continue
            if self._contains_whole_phrase(normalized_query, norm_label):
                seed_scores[original_label] = max(seed_scores.get(original_label, 0.0), 1.0)

        # 2) direct token matches
        for token in tokens:
            if token in concepts_by_norm:
                concept = concepts_by_norm[token]
                if self._normalize(concept) in _QUERY_STOPWORDS:
                    continue
                seed_scores[concept] = max(seed_scores.get(concept, 0.0), 0.98)

        # 3) synonym-based mapping
        for canonical, variants in self._synonyms.items():
            canonical_norm = self._normalize(canonical)
            if canonical_norm not in concepts_by_norm or canonical_norm in _QUERY_STOPWORDS:
                continue
            if canonical_norm in tokens:
                seed_scores[concepts_by_norm[canonical_norm]] = max(
                    seed_scores.get(concepts_by_norm[canonical_norm], 0.0),
                    0.96,
                )
                continue
            for variant in variants:
                norm_variant = self._normalize(variant)
                if self._contains_whole_phrase(normalized_query, norm_variant):
                    concept = concepts_by_norm[canonical_norm]
                    seed_scores[concept] = max(seed_scores.get(concept, 0.0), 0.9)
                    break

        # 4) fuzzy fallback from tokens to known concepts
        if not seed_scores:
            norm_labels = list(concepts_by_norm.keys())
            for token in tokens:
                close = get_close_matches(token, norm_labels, n=2, cutoff=self._fuzzy_cutoff)
                for matched in close:
                    if matched in _QUERY_STOPWORDS:
                        continue
                    concept = concepts_by_norm[matched]
                    seed_scores[concept] = max(seed_scores.get(concept, 0.0), 0.75)

        ranked = sorted(seed_scores.items(), key=lambda item: item[1], reverse=True)
        seeds = [label for label, _ in ranked[:max_seeds]]
        primary = seeds[0] if seeds else None
        return ParsedQuery(
            original_query=query,
            normalized_query=normalized_query,
            tokens=tokens,
            seed_concepts=seeds,
            primary_concept=primary,
        )
