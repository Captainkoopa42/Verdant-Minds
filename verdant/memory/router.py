"""Shard routing helpers for Verdant memory."""

from __future__ import annotations

import re
from typing import Any, List

STOP_WORDS: set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "about", "it",
    "this", "that", "and", "or", "but", "if", "not", "no", "so", "than",
    "too", "very", "just", "i", "me", "my", "we", "our", "you", "your",
    "he", "she", "they", "them", "its", "what", "who", "where", "when", "how",
}


class MemoryRouter:
    """Route text to shard homes using the manifest concept index."""

    def __init__(self, manifest: dict[str, Any]) -> None:
        self.manifest = manifest

    def _active_shard_id(self) -> str:
        active = self.manifest.get("active_shards") or []
        if active:
            return str(active[0])
        shards = self.manifest.get("shards") or {}
        for shard_id, meta in shards.items():
            if isinstance(meta, dict) and meta.get("state") == "active":
                return str(shard_id)
        return str(next(iter(shards), "basin_monolith_000000"))

    @staticmethod
    def _entry_shard_ids(entry: Any) -> list[str]:
        if entry is None:
            return []
        if isinstance(entry, str):
            return [entry]
        if isinstance(entry, dict):
            shard_id = entry.get("shard_id")
            return [str(shard_id)] if shard_id else []
        if isinstance(entry, list):
            out: list[str] = []
            for item in entry:
                out.extend(MemoryRouter._entry_shard_ids(item))
            return out
        return []

    def locate(self, text: str, top_n: int = 2) -> List[str]:
        if not self.manifest.get("concept_index"):
            return [self._active_shard_id()]
        tokens = set(re.split(r"[\s\W]+", text.lower())) - STOP_WORDS
        hits: dict[str, int] = {}
        for token in tokens:
            if not token:
                continue
            for shard_id in self._entry_shard_ids(self.manifest["concept_index"].get(token, [])):
                hits[shard_id] = hits.get(shard_id, 0) + 1
        if not hits:
            return [self._active_shard_id()]
        return sorted(hits, key=hits.get, reverse=True)[:top_n]

    def get_mandatory_bridges_for_shard(self, shard_id: str) -> List[dict[str, Any]]:
        """Return all mandatory bridge edges touching this shard."""
        return [
            e for e in self.manifest.get("weak_bridge_edges", [])
            if e.get("mandatory") and (
                e.get("source_shard") == shard_id or e.get("target_shard") == shard_id
            )
        ]
