"""Structure-sharing state copy: same value as ``model_copy(deep=True)``, without re-copying history.

Containers (dict, list) are copied so the two states can diverge. Frozen records inside
them are shared, because a committed frozen record is never changed again. Anything that
is not a frozen record, a primitive or a plain container is deep-copied as before.

This relies on one invariant the engine already states by using frozen records: nothing
mutates a dict or list nested inside a committed record. The pytest plugin and
``tests/test_long_life_acceleration.py`` check it by confirming that a superseded state
still fingerprints the same after later beats.
"""
from __future__ import annotations

import copy
from enum import Enum

from pydantic import BaseModel

KERNEL_INIT_SHA256 = "93971ecd0f8df732b071a7f9bd893cab4575a4c65ed9450d5c267ee2057fef8a"
KERNEL_SNAPSHOT_SHA256 = "9a871c1fd66996e14058827ae76bb105f0d653e2df445d775435c134abd8198a"
_PRIMITIVES = (str, int, float, bool, type(None), bytes)


def _share(value):
    kind = type(value)
    if kind in _PRIMITIVES or isinstance(value, Enum):
        return value
    if isinstance(value, BaseModel):
        return value if kind.model_config.get("frozen") else copy.deepcopy(value)
    if kind is dict:
        return {key: _share(item) for key, item in value.items()}
    if kind is list:
        return [_share(item) for item in value]
    if kind is tuple:
        return tuple(_share(item) for item in value)
    if kind in (set, frozenset):
        return kind(_share(item) for item in value)
    return copy.deepcopy(value)


def structural_copy(state: BaseModel) -> BaseModel:
    clone = state.model_copy()                      # new model object, shared field values
    data = clone.__dict__
    for name in type(state).model_fields:
        data[name] = _share(data[name])             # direct write: a copy is not re-validated, as with deep copy
    return clone


__all__ = ["structural_copy", "KERNEL_INIT_SHA256", "KERNEL_SNAPSHOT_SHA256"]
