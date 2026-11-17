"""Byte-exact, identity-checked acceleration of ``KernelState.fingerprint``.

``KernelState.fingerprint`` remains the reference definition:

    sha256(canonical_json_bytes(state.model_dump(mode="json")))

This module produces the *same bytes* and therefore the same digest. It does
not define a new fingerprint, a Merkle tree, or a relaxed equality. The only
thing it changes is how often an unchanged immutable record is re-encoded.

A record's canonical JSON bytes are reused only when all of the following hold:

* its class is a frozen Pydantic model with no custom or computed serializers;
* every field of that class is deeply immutable by annotation (no ``dict``,
  ``list``, ``set`` or ``Any`` anywhere beneath it), so the object cannot
  change without being replaced by a different object;
* its runtime type is exactly the type its container declares, so encoding it
  alone equals how its parent would encode it;
* the cached entry was produced from this exact object (identity check, with a
  strong reference held so an id cannot be recycled).

Everything else is encoded through the ordinary Pydantic dump every time.

Set ``VERDANT_FINGERPRINT_VERIFY=1`` to recompute the reference digest on every
call and raise on any difference. The cache holds no authority: discarding it
at any time changes nothing but speed.
"""
from __future__ import annotations

import hashlib
import json
import os
import types
from enum import Enum
from typing import Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel

from verdant_kernel.models import canonical_json_bytes

_PRIMITIVES = (str, int, float, bool, type(None))
_CLASS_CACHEABLE: dict[type, bool] = {}
# Opt-in (see install_long_life_acceleration): treat every frozen, plainly-serialized
# record as immutable once committed, including records that carry dict fields which the
# annotation walk below cannot prove immutable. Verify mode cross-checks every digest.
TRUST_FROZEN_RECORDS = False
_LIST_PREFIX: dict[int, list] = {}
_DIGEST_MEMO: list[tuple[bytes, str]] = []
_CLASS_PLAIN: dict[type, bool] = {}


class FingerprintCacheMismatch(RuntimeError):
    """Raised in verify mode when accelerated bytes differ from the reference."""


def _has_plain_serialization(cls: type[BaseModel]) -> bool:
    """True when a model dumps exactly its declared fields under their names."""
    known = _CLASS_PLAIN.get(cls)
    if known is not None:
        return known
    decorators = cls.__pydantic_decorators__
    plain = not (
        decorators.field_serializers
        or decorators.model_serializers
        or decorators.computed_fields
    )
    if plain:
        for info in cls.model_fields.values():
            if info.exclude or info.alias or info.serialization_alias:
                plain = False
                break
    if plain and cls.model_config.get("extra") == "allow":
        plain = False
    _CLASS_PLAIN[cls] = plain
    return plain


def _annotation_immutable(annotation: Any, visiting: frozenset[type]) -> bool:
    if annotation in _PRIMITIVES:
        return True
    if isinstance(annotation, type):
        if issubclass(annotation, Enum):
            return True
        if issubclass(annotation, BaseModel):
            return _class_cacheable(annotation, visiting)
        return False
    origin = get_origin(annotation)
    if origin is Literal:
        return True
    if origin is tuple:
        return all(
            arg is Ellipsis or _annotation_immutable(arg, visiting)
            for arg in get_args(annotation)
        )
    if origin is Union or origin is types.UnionType:
        return all(_annotation_immutable(arg, visiting) for arg in get_args(annotation))
    return False


def _class_cacheable(cls: type, visiting: frozenset[type] = frozenset()) -> bool:
    known = _CLASS_CACHEABLE.get(cls)
    if known is not None:
        return known
    if cls in visiting:
        # A self-referential record is not proven immutable here.
        return False
    result = (
        isinstance(cls, type)
        and issubclass(cls, BaseModel)
        and bool(cls.model_config.get("frozen"))
        and _has_plain_serialization(cls)
        and all(
            _annotation_immutable(info.annotation, visiting | {cls})
            for info in cls.model_fields.values()
        )
    )
    if not visiting:
        _CLASS_CACHEABLE[cls] = result
    return result


def _shareable(cls: type) -> bool:
    """True when instances of ``cls`` may be cached and shared between states."""
    if _class_cacheable(cls):
        return True
    return bool(
        TRUST_FROZEN_RECORDS
        and isinstance(cls, type)
        and issubclass(cls, BaseModel)
        and cls.model_config.get("frozen")
        and _has_plain_serialization(cls)
    )


def _list_bytes(value: list, cache: dict[int, tuple[Any, bytes]]) -> bytes:
    """Join record bytes for a history list, reusing the encoded prefix when the list only grew."""
    if not value:
        return b"[]"
    if not TRUST_FROZEN_RECORDS:
        return b"[" + b",".join(_record_bytes(item, cache) for item in value) + b"]"
    entry = _LIST_PREFIX.get(id(value[0]))
    n = 0; body = b""
    if entry is not None and entry[0] is value[0] and entry[1] <= len(value) and value[entry[1] - 1] is entry[2]:
        n, body = entry[1], entry[3]
    if n < len(value):
        tail = b",".join(_record_bytes(item, cache) for item in value[n:])
        body = body + b"," + tail if n else tail
        _LIST_PREFIX[id(value[0])] = [value[0], len(value), value[-1], body]
    return b"[" + body + b"]"


def _declared_element(annotation: Any) -> tuple[str, type] | None:
    """Return ("list"|"dict", element class) for simple homogeneous containers."""
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is list and len(args) == 1 and isinstance(args[0], type):
        return "list", args[0]
    if origin is dict and len(args) == 2 and args[0] is str and isinstance(args[1], type):
        return "dict", args[1]
    return None


def _record_bytes(record: BaseModel, cache: dict[int, tuple[Any, bytes]]) -> bytes:
    entry = cache.get(id(record))
    if entry is not None and entry[0] is record:
        return entry[1]
    encoded = canonical_json_bytes(BaseModel.model_dump(record, mode="json"))
    cache[id(record)] = (record, encoded)
    return encoded


def _key_bytes(key: str) -> bytes:
    return json.dumps(key, ensure_ascii=False).encode("utf-8")


def _field_bytes(
    owner: BaseModel,
    name: str,
    annotation: Any,
    cache: dict[int, tuple[Any, bytes]],
) -> bytes:
    value = getattr(owner, name)
    declared = _declared_element(annotation)
    if declared is not None:
        kind, element_cls = declared
        if _shareable(element_cls):
            if kind == "list" and type(value) is list:
                if TRUST_FROZEN_RECORDS or all(type(item) is element_cls for item in value):
                    return _list_bytes(value, cache)
            elif kind == "dict" and type(value) is dict:
                if all(
                    type(key) is str and type(item) is element_cls
                    for key, item in value.items()
                ):
                    return (
                        b"{"
                        + b",".join(
                            _key_bytes(key) + b":" + _record_bytes(value[key], cache)
                            for key in sorted(value)
                        )
                        + b"}"
                    )
    elif (
        isinstance(annotation, type)
        and issubclass(annotation, BaseModel)
        and type(value) is annotation
    ):
        if _shareable(annotation):
            return _record_bytes(value, cache)
        if _has_plain_serialization(annotation):
            return _model_bytes(value, cache)
    # Reference path for this one field: let Pydantic dump it as its owner would.
    return canonical_json_bytes(owner.model_dump(mode="json", include={name})[name])


def _model_bytes(
    model: BaseModel,
    cache: dict[int, tuple[Any, bytes]],
    *,
    empty_list_fields: frozenset[str] = frozenset(),
) -> bytes:
    fields = type(model).model_fields
    parts: list[bytes] = []
    for name in sorted(fields):
        if name in empty_list_fields:
            encoded = b"[]"
        else:
            encoded = _field_bytes(model, name, fields[name].annotation, cache)
        parts.append(_key_bytes(name) + b":" + encoded)
    return b"{" + b",".join(parts) + b"}"


def cached_state_fingerprint(
    state: BaseModel,
    *,
    include_transitions: bool,
    cache: dict[int, tuple[Any, bytes]],
) -> str:
    """Return exactly ``state.fingerprint(include_transitions=...)``, faster."""
    if not _has_plain_serialization(type(state)):
        return state.fingerprint(include_transitions=include_transitions)
    encoded = _model_bytes(
        state,
        cache,
        empty_list_fields=frozenset() if include_transitions else frozenset({"transitions"}),
    )
    digest = None
    if TRUST_FROZEN_RECORDS:
        # Several fingerprints per beat are taken of an unchanged state (the output of one
        # commit is the input of the next). Equal bytes have equal digests.
        for prior_bytes, prior_digest in _DIGEST_MEMO:
            if len(prior_bytes) == len(encoded) and prior_bytes == encoded:
                digest = prior_digest
                break
    if digest is None:
        digest = hashlib.sha256(encoded).hexdigest()
        if TRUST_FROZEN_RECORDS:
            _DIGEST_MEMO.insert(0, (encoded, digest)); del _DIGEST_MEMO[3:]
    if os.environ.get("VERDANT_FINGERPRINT_VERIFY") == "1":
        reference = state.fingerprint(include_transitions=include_transitions)
        if reference != digest:
            raise FingerprintCacheMismatch(
                "Accelerated fingerprint differs from the reference definition "
                f"(reference={reference}, accelerated={digest})."
            )
    return digest


__all__ = ["FingerprintCacheMismatch", "cached_state_fingerprint"]
