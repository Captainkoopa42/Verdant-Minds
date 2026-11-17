"""Byte-exact acceleration for the kernel's ``*_structural_fingerprint`` methods.

Those methods build a payload by calling ``record.model_dump(mode="json")`` on every
record in several histories and then hash ``canonical_json_bytes(payload)``. The stock
method body is run unchanged. While it runs, a shareable record's ``model_dump`` returns
a short token instead of its dump, and ``canonical_json_bytes`` splices each token with
that record's cached canonical bytes. A record's canonical JSON is the same bytes whether
it is encoded alone or nested, so the digest is identical.
"""
from __future__ import annotations

import os
import re

from pydantic import BaseModel

import verdant_kernel.kernel as _kernel_module
from verdant_kernel.models import FrozenRecord, canonical_json_bytes

from . import fingerprint_cache as _fc

_TOKEN = re.compile(rb'"\\u0000VP(\d+)\\u0000"')
_ACTIVE: list | None = None
_CACHE: dict | None = None


def _patched_model_dump(self, *args, **kwargs):
    if _ACTIVE is not None and not args and kwargs == {"mode": "json"} and _fc._shareable(type(self)):
        _ACTIVE.append(_fc._record_bytes(self, _CACHE))
        return f"\x00VP{len(_ACTIVE) - 1}\x00"
    return BaseModel.model_dump(self, *args, **kwargs)


def _splicing_canonical_json_bytes(value):
    encoded = canonical_json_bytes(value)
    parts = _ACTIVE
    if not parts:
        return encoded
    return _TOKEN.sub(lambda match: parts[int(match.group(1))], encoded)


def accelerated(original, cache_for):
    def method(self):
        global _ACTIVE, _CACHE
        if _ACTIVE is not None:                      # nested call: run the reference
            return original(self)
        _ACTIVE, _CACHE = [], cache_for(self)
        _kernel_module.canonical_json_bytes = _splicing_canonical_json_bytes
        try:
            digest = original(self)
        finally:
            _kernel_module.canonical_json_bytes = canonical_json_bytes
            _ACTIVE, _CACHE = None, None
        if os.environ.get("VERDANT_FINGERPRINT_VERIFY") == "1":
            reference = original(self)
            if reference != digest:
                raise _fc.FingerprintCacheMismatch(
                    f"Accelerated {original.__name__} differs from the reference "
                    f"(reference={reference}, accelerated={digest}).")
        return digest
    method.__name__ = original.__name__; method.__doc__ = original.__doc__
    return method


def install_model_dump_patch() -> None:
    FrozenRecord.model_dump = _patched_model_dump


def uninstall_model_dump_patch() -> None:
    if "model_dump" in FrozenRecord.__dict__:
        del FrozenRecord.model_dump
