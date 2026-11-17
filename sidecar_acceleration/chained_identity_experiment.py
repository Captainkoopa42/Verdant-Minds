"""EXPERIMENT, not canonical: a state identity that costs O(new records) per beat.

This CHANGES fingerprint values. It exists to measure what a piecewise identity would buy
before anyone decides to adopt one. Nothing here is installed by the byte-exact accelerators.

identity_v2(state) = sha256("verdant.identity.v2" + for each field in name order: name + field digest)
  history list   -> hash chain: d0 = sha256("list"), d_i = sha256(d_{i-1} + sha256(record bytes));
                    only records appended since the last call are hashed
  dict of records-> sha256 over (key + sha256(record bytes)) in key order
  anything else  -> sha256 of the field's canonical JSON bytes, exactly as today
A record's own bytes are still its canonical JSON, so record-level content is unchanged.
"""
from __future__ import annotations

import hashlib

from pydantic import BaseModel

from verdant_kernel import VerdantKernel

from . import fingerprint_cache as fc

_RECORD_DIGEST: dict[int, tuple] = {}
_CHAIN: dict[int, list] = {}
_ORIGINAL: dict[str, object] = {}
_EMPTY = hashlib.sha256(b"list").digest()


def _digest(record) -> bytes:
    entry = _RECORD_DIGEST.get(id(record))
    if entry is not None and entry[0] is record:
        return entry[1]
    value = hashlib.sha256(fc.canonical_json_bytes(BaseModel.model_dump(record, mode="json"))).digest()
    _RECORD_DIGEST[id(record)] = (record, value)
    return value


def _field_digest(state, name, annotation) -> bytes:
    value = getattr(state, name); declared = fc._declared_element(annotation)
    if declared is not None and fc._shareable(declared[1]):
        if declared[0] == "list" and type(value) is list:
            if not value:
                return _EMPTY
            entry = _CHAIN.get(id(value[0])); n, running = 0, _EMPTY
            if entry is not None and entry[0] is value[0] and entry[1] <= len(value) and value[entry[1] - 1] is entry[2]:
                n, running = entry[1], entry[3]
            for record in value[n:]:
                running = hashlib.sha256(running + _digest(record)).digest()
            _CHAIN[id(value[0])] = [value[0], len(value), value[-1], running]
            return running
        if declared[0] == "dict" and type(value) is dict:
            h = hashlib.sha256(b"dict")
            for key in sorted(value):
                h.update(key.encode("utf-8")); h.update(b"\x00"); h.update(_digest(value[key]))
            return h.digest()
    return hashlib.sha256(fc._field_bytes(state, name, annotation, {})).digest()


def identity_v2(state, *, include_transitions: bool = True) -> str:
    h = hashlib.sha256(b"verdant.identity.v2"); fields = type(state).model_fields
    for name in sorted(fields):
        h.update(name.encode("utf-8")); h.update(b"\x00")
        h.update(_EMPTY if (name == "transitions" and not include_transitions) else _field_digest(state, name, fields[name].annotation))
    return h.hexdigest()


def install_chained_identity_experiment() -> None:
    """Replace kernel fingerprints with identity_v2 for this process. Fingerprint values change."""
    if _ORIGINAL:
        return
    fc.TRUST_FROZEN_RECORDS = True
    _ORIGINAL["fingerprint"] = VerdantKernel.fingerprint; _ORIGINAL["semantic_fingerprint"] = VerdantKernel.semantic_fingerprint
    VerdantKernel.fingerprint = lambda self, *, include_transitions=True: identity_v2(self.state, include_transitions=include_transitions)
    VerdantKernel.semantic_fingerprint = lambda self: identity_v2(self.state, include_transitions=False)


def uninstall_chained_identity_experiment() -> None:
    if _ORIGINAL:
        VerdantKernel.fingerprint = _ORIGINAL.pop("fingerprint"); VerdantKernel.semantic_fingerprint = _ORIGINAL.pop("semantic_fingerprint")
        _RECORD_DIGEST.clear(); _CHAIN.clear()
