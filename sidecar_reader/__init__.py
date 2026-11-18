"""A reader that sees words separately: objecthood for reading (opt-in; no verdant_* file edited).

The reading organ (text_features) hands the field one description of a whole sentence: counts of
hashed letter patterns. Nothing downstream can say which letters belong to which word, so a word
always taught with the same companions can never be learned as itself (docs/LOOKS_ACROSS_SENSES_V0.md).
Perception does this for sight: it separates objects before anything reaches the mind.

* word_glances(text, width): the organ's own description of each word on its own (" word ", with the
  spaces around it), in the same letter-pattern code as the sentence.
* attach(command, text): the command carries its word glances in metadata (the sentence description,
  and so the field, is unchanged).
* install_reader(): after each experience, every told concept whose label is one of the glanced
  words keeps that word's look (running mean of letter counts, OBSERVED) in its attributes under
  "look::reading". Nothing else changes: field, profiles, bonds and structures are exactly stock.
* reread_look(kernel, event_key, out, in): the reader also keeps the words in order ("read_in_order"),
  so a swap can be re-read through the reading organ itself: the reading counterpart of keeping
  what is where in sight. Exact by construction for the look; the test is what it does to imagination.
* word_shares(kernel, width): Shares for sidecar_looks.imagined_look built from these observed looks
  (no regression); the swap removes and adds whole word looks k times, with k estimated from the
  memory itself (least squares, rounded, 1..3; fixed before testing).
"""
from __future__ import annotations

import hashlib
import re

import numpy as np

LOOK_KEY = "look::reading"
_ORIGINAL: dict = {}


def _counts(text: str, width: int) -> np.ndarray:
    c = np.zeros(width); text = text.lower()
    for size in (1, 2, 3, 4):
        for s in range(len(text) - size + 1):
            c[int.from_bytes(hashlib.sha256(f"{size}:{text[s:s + size]}".encode()).digest()[:4], "big") % width] += 1
    return c


def word_glances(text: str, width: int) -> dict[str, list[float]]:
    return {w: [float(v) for v in _counts(f" {w} ", width)] for w in sorted(set(re.findall(r"[a-z]+", text.lower())))}


def attach(command, text: str):
    """The command carries what the reader saw: each word on its own, and the words in order."""
    width = len(command.feature_vector)
    return command.model_copy(update={"metadata": {**command.metadata, "word_glances": word_glances(text, width),
                                                   "read_in_order": text.lower()}})


def organ(text: str, width: int) -> list[float]:
    """The reading organ itself (identical to curriculum_packs text_features)."""
    v = np.log1p(_counts(text, width)); n = float(np.linalg.norm(v))
    return [round(float(x / n), 8) for x in v] if n else [0.0] * width


def reread_look(kernel, event_key: str, swap_out: str, swap_in: str) -> tuple[list[float], str]:
    """Re-read a remembered sentence with one word swapped, through the organism's own reading organ.
    IMAGINED: the changed sentence was never read; it is rebuilt from the words kept in order."""
    ev = next(e for e in kernel.state.evidence.values() if e.event_key == event_key and e.details.get("role") == "native_payload")
    text = ev.details.get("read_in_order")
    if text is None:
        raise KeyError("This memory was read without the reader keeping word order.")
    width = len(ev.details["word_glances"][next(iter(ev.details["word_glances"]))])
    new = re.sub(rf"\b{re.escape(swap_out.lower())}\b", swap_in.lower(), text)
    return organ(new, width), "text"


def _reader_apply_experience(self, command):
    out = _ORIGINAL["apply_experience"](self, command)
    glances = (command.metadata or {}).get("word_glances")
    if glances:
        for p in command.concept_proposals:
            g = glances.get(p.label.lower())
            cid = next((c for c, x in self.state.concepts.items() if x.label == p.label), None)
            if g is None or cid is None:
                continue
            c = self.state.concepts[cid]; old = c.attributes.get(LOOK_KEY); n = old["count"] if old else 0
            mean = (np.asarray(old["counts"]) * n + np.asarray(g)) / (n + 1) if old else np.asarray(g)
            self.state.concepts[cid] = c.model_copy(update={"attributes": {**c.attributes, LOOK_KEY: {
                "counts": [float(v) for v in mean], "count": n + 1, "provenance": "OBSERVED (seen as a separate word)"}}})
    return out


def install_reader() -> None:
    from verdant_kernel import VerdantKernel
    if not _ORIGINAL:
        _ORIGINAL["apply_experience"] = VerdantKernel.apply_experience
        VerdantKernel.apply_experience = _reader_apply_experience


def uninstall_reader() -> None:
    from verdant_kernel import VerdantKernel
    if _ORIGINAL:
        VerdantKernel.apply_experience = _ORIGINAL.pop("apply_experience")


def word_shares(kernel, width: int):
    """Shares (sidecar_looks) from observed word looks; concepts never seen as a word have none."""
    from sidecar_looks import Shares, reading
    share = {cid: np.asarray(c.attributes[LOOK_KEY]["counts"]) for cid, c in kernel.state.concepts.items() if LOOK_KEY in c.attributes}
    return Shares(reading(width), sorted(share), share, np.zeros(width), {}, 0, 0.0, word_looks=True)
