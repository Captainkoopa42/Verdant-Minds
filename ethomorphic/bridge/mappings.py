"""Concept-dimension mapping logic with optional semantic embeddings.

Provides PCA-projected semantic embeddings for concept-to-dimension mapping
when ``sentence-transformers`` and ``scikit-learn`` are available.  Falls back
gracefully to random mapping otherwise.
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Optional dependencies -------------------------------------------------------
try:
    from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    _HAS_SENTENCE_TRANSFORMERS = False

try:
    from sklearn.decomposition import PCA  # type: ignore[import-untyped]

    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False


# ---------------------------------------------------------------------------
# Concept descriptions (used for richer embedding signal)
# ---------------------------------------------------------------------------

CONCEPT_DESCRIPTIONS: Dict[str, str] = {
    "identity": "the persistent sense of self and personal continuity",
    "continuity": "unbroken connection across time and change",
    "selfhood": "the quality constituting one's individual nature and identity",
    "persistence": "enduring existence despite transformation",
    "transformation": "fundamental change in structure, state, or identity",
    "boundary": "the limit that separates self from environment or others",
    "reflection": "introspective examination of thought, action, and self",
    "consciousness": "subjective awareness of self, world, and mental activity",
    "emergence": "novel properties arising from component interactions",
    "complexity": "rich interdependence among many interacting elements",
    "ethics": "principles guiding right action and moral judgment",
    "justice": "fairness and equitable treatment of all parties",
    "autonomy": "self-directed agency and independent choice",
    "beneficence": "commitment to promote well-being and prevent harm",
    "harm": "damage or suffering imposed on persons or systems",
    "integrity": "consistency between values, commitments, and behavior",
    "trust": "confidence in reliability, honesty, and good intent",
    "responsibility": "accountability for choices, impacts, and obligations",
    "reasoning": "structured thinking that derives conclusions from premises",
    "coherence": "internal consistency and mutual support among beliefs",
    "entropy": "the degree of disorder or uncertainty in a cognitive system",
    "meaning": "significance assigned to symbols, events, or experiences",
}


def _concept_to_encoding_phrase(concept: str) -> str:
    """Return a context-rich phrase for semantic embedding."""
    description = CONCEPT_DESCRIPTIONS.get(concept)
    if description:
        return f"{concept.replace('_', ' ')}: {description}"

    concept_words = concept.replace("_", " ")
    if concept.startswith("Emergent_"):
        emergent_terms = concept[len("Emergent_"):].split("_")
        if emergent_terms:
            if len(emergent_terms) == 1:
                combo = emergent_terms[0]
            elif len(emergent_terms) == 2:
                combo = f"{emergent_terms[0]} and {emergent_terms[1]}"
            else:
                combo = ", ".join(emergent_terms[:-1]) + f", and {emergent_terms[-1]}"
            return f"{concept_words}: emergent concept combining {combo}"

    return concept_words


# ---------------------------------------------------------------------------
# Semantic mapper
# ---------------------------------------------------------------------------

class SemanticMapper:
    """Builds and manages semantic concept-dimension mappings.

    Uses ``sentence-transformers`` to embed concept labels and ``PCA`` to
    project them into the ECWF dimension space.  When either optional
    dependency is missing, :meth:`build` returns an empty dict and callers
    should fall back to random assignment.
    """

    def __init__(self, num_cognitive_dims: int, num_ethical_dims: int) -> None:
        """Initialise the mapper.

        Args:
            num_cognitive_dims: Number of cognitive ECWF dimensions.
            num_ethical_dims: Number of ethical ECWF dimensions.
        """
        self.num_cognitive_dims = num_cognitive_dims
        self.num_ethical_dims = num_ethical_dims

        self._encoder: Any = None
        self._pca_model: Any = None
        self._embedding_cache: Dict[str, np.ndarray] = {}
        self.available: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self, concepts: List[str]
    ) -> Dict[str, List[Tuple[str, int, float]]]:
        """Build semantic mappings for a list of concept labels.

        Args:
            concepts: Concept name strings.

        Returns:
            Mapping dictionary.  Empty if semantic infrastructure is
            unavailable.
        """
        if not concepts:
            return {}

        if not (_HAS_SENTENCE_TRANSFORMERS and _HAS_SKLEARN):
            if not _HAS_SENTENCE_TRANSFORMERS:
                warnings.warn(
                    "sentence-transformers not available; "
                    "falling back to random concept-dimension mapping.",
                    stacklevel=2,
                )
            if not _HAS_SKLEARN:
                warnings.warn(
                    "scikit-learn not available for PCA; "
                    "falling back to random concept-dimension mapping.",
                    stacklevel=2,
                )
            self.available = False
            return {}

        try:
            if self._encoder is None:
                self._encoder = SentenceTransformer("all-MiniLM-L6-v2")

            texts = [_concept_to_encoding_phrase(c) for c in concepts]
            embeddings = np.array(
                self._encoder.encode(texts, show_progress_bar=False),
                dtype=np.float64,
            )

            for i, concept in enumerate(concepts):
                self._embedding_cache[concept] = embeddings[i]

            total_dims = self.num_cognitive_dims + self.num_ethical_dims
            n_components = min(total_dims, len(concepts), embeddings.shape[1])
            self._pca_model = PCA(n_components=n_components)
            projected = self._pca_model.fit_transform(embeddings)

            if projected.shape[1] < total_dims:
                pad = total_dims - projected.shape[1]
                projected = np.hstack([projected, np.zeros((projected.shape[0], pad))])

            mapping: Dict[str, List[Tuple[str, int, float]]] = {}
            for i, concept in enumerate(concepts):
                cog_w = projected[i][: self.num_cognitive_dims]
                eth_w = projected[i][self.num_cognitive_dims : self.num_cognitive_dims + self.num_ethical_dims]
                mapping[concept] = _weights_to_mappings(cog_w, eth_w)

            self.available = True
            return mapping

        except Exception as exc:
            warnings.warn(
                f"Semantic embedding mapping failed ({exc}); "
                "falling back to random mapping.",
                stacklevel=2,
            )
            self.available = False
            return {}

    def project_single(self, concept: str) -> Optional[List[Tuple[str, int, float]]]:
        """Project a single concept through the stored PCA model.

        Args:
            concept: Concept label.

        Returns:
            Dimension mappings or ``None`` if the PCA model is not fitted.
        """
        if not self.available or self._pca_model is None or self._encoder is None:
            return None

        try:
            if concept not in self._embedding_cache:
                emb = np.array(
                    self._encoder.encode([concept], show_progress_bar=False)[0],
                    dtype=np.float64,
                )
                self._embedding_cache[concept] = emb

            embedding = self._embedding_cache[concept]
            projected = self._pca_model.transform(embedding.reshape(1, -1))[0]

            total_dims = self.num_cognitive_dims + self.num_ethical_dims
            if len(projected) < total_dims:
                projected = np.concatenate([projected, np.zeros(total_dims - len(projected))])

            cog_w = projected[: self.num_cognitive_dims]
            eth_w = projected[self.num_cognitive_dims : self.num_cognitive_dims + self.num_ethical_dims]
            return _weights_to_mappings(cog_w, eth_w)
        except Exception:
            return None

    def get_similarity(self, concept_a: str, concept_b: str) -> float:
        """Compute cosine similarity between two concept embeddings.

        Args:
            concept_a: First concept.
            concept_b: Second concept.

        Returns:
            Cosine similarity in ``[-1, 1]`` or ``0.0`` if unavailable.
        """
        emb_a = self._embedding_cache.get(concept_a)
        emb_b = self._embedding_cache.get(concept_b)

        if emb_a is None or emb_b is None:
            return 0.0

        norm_a = np.linalg.norm(emb_a)
        norm_b = np.linalg.norm(emb_b)
        if norm_a < 1e-10 or norm_b < 1e-10:
            return 0.0

        return float(np.dot(emb_a, emb_b) / (norm_a * norm_b))


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _weights_to_mappings(
    cog_weights: np.ndarray, eth_weights: np.ndarray
) -> List[Tuple[str, int, float]]:
    """Convert raw PCA weight vectors to ``(type, dim_idx, weight)`` tuples.

    Normalises absolute values to the ``[0.1, 1.0]`` range.

    Args:
        cog_weights: Cognitive dimension weights.
        eth_weights: Ethical dimension weights.

    Returns:
        List of mapping tuples.
    """
    dimensions: List[Tuple[str, int, float]] = []
    for idx, w in enumerate(cog_weights):
        dimensions.append(("cognitive", int(idx), float(w)))
    for idx, w in enumerate(eth_weights):
        dimensions.append(("ethical", int(idx), float(w)))

    abs_w = [abs(d[2]) for d in dimensions]
    max_w = max(abs_w) if abs_w else 1.0
    min_w = min(abs_w) if abs_w else 0.0

    if max_w - min_w > 1e-10:
        dimensions = [
            (dtype, idx, 0.1 + 0.9 * (abs(w) - min_w) / (max_w - min_w))
            for dtype, idx, w in dimensions
        ]
    else:
        dimensions = [(dtype, idx, 0.5) for dtype, idx, w in dimensions]

    return dimensions
