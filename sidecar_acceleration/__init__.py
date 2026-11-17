"""Opt-in, byte-exact performance sidecar for the Verdant kernel.

Nothing in this package runs unless a caller explicitly installs it. The
canonical kernel sources under ``verdant_kernel/`` are not edited, so every
frozen code manifest that pins those files continues to verify.

``install_fingerprint_cache()`` replaces ``VerdantKernel.fingerprint`` and
``VerdantKernel.semantic_fingerprint`` for the current process with an
implementation that returns exactly the same digests (see
``fingerprint_cache.py``). ``uninstall_fingerprint_cache()`` restores the
originals. The accelerator has no semantic or governance authority.
"""
from __future__ import annotations

from verdant_kernel import VerdantKernel

from .fingerprint_cache import FingerprintCacheMismatch, cached_state_fingerprint
from .structural_copy import structural_copy

_ORIGINALS: dict[str, object] = {}
_LONG_LIFE: dict[str, object] = {}


_SHARED_CACHE: dict = {}
_SWEEP = {"calls": 0, "seen": set()}


def _sweep_shared_cache(state) -> None:
    """Every 256 fingerprints, drop cached bytes for records no live fingerprint has touched since."""
    _SWEEP["calls"] += 1
    if _SWEEP["calls"] % 256:
        return
    from . import fingerprint_cache as fc
    live = set()
    for value in state.__dict__.values():
        items = value.values() if type(value) is dict else value if type(value) is list else (value,)
        live.update(id(item) for item in items)
    for key in [key for key in _SHARED_CACHE if key not in live and key not in _SWEEP["seen"]]:
        del _SHARED_CACHE[key]
    for key in [key for key, entry in fc._LIST_PREFIX.items() if key not in live]:
        del fc._LIST_PREFIX[key]
    _SWEEP["seen"] = live


def _record_cache(kernel: VerdantKernel) -> dict:
    if _LONG_LIFE:
        # Records are shared between successive states, so their bytes stay valid
        # across beats; every entry is still identity-checked before use.
        _sweep_shared_cache(kernel.state)
        return _SHARED_CACHE
    # The cache belongs to one exact state object. If the kernel's state is
    # replaced (staged commit, reload, branch), old entries are dropped
    # rather than trusted.
    if getattr(kernel, "_fingerprint_cache_owner", None) is not kernel.state:
        kernel._fingerprint_cache_owner = kernel.state
        kernel._fingerprint_cache = {}
    return kernel._fingerprint_cache


def _fingerprint(self: VerdantKernel, *, include_transitions: bool = True) -> str:
    return cached_state_fingerprint(
        self.state, include_transitions=include_transitions, cache=_record_cache(self)
    )


def _semantic_fingerprint(self: VerdantKernel) -> str:
    return cached_state_fingerprint(
        self.state, include_transitions=False, cache=_record_cache(self)
    )


def fingerprint_cache_installed() -> bool:
    return bool(_ORIGINALS)


def install_fingerprint_cache() -> None:
    """Explicitly enable the byte-exact fingerprint accelerator in this process."""
    if _ORIGINALS:
        return
    _ORIGINALS["fingerprint"] = VerdantKernel.__dict__["fingerprint"]
    _ORIGINALS["semantic_fingerprint"] = VerdantKernel.__dict__["semantic_fingerprint"]
    VerdantKernel.fingerprint = _fingerprint
    VerdantKernel.semantic_fingerprint = _semantic_fingerprint


def uninstall_fingerprint_cache() -> None:
    """Restore the reference kernel fingerprint methods."""
    if not _ORIGINALS:
        return
    VerdantKernel.fingerprint = _ORIGINALS.pop("fingerprint")
    VerdantKernel.semantic_fingerprint = _ORIGINALS.pop("semantic_fingerprint")


def _long_life_init(self, *, seed: int = 7741, state_dim: int = 128,
                    run_label: str = "independent-rebuild", state=None) -> None:
    if state is None:
        _LONG_LIFE["__init__"](self, seed=seed, state_dim=state_dim, run_label=run_label)
        return
    # Mirrors the stock constructor's state branch with the deep copy replaced.
    self.state = structural_copy(state)
    self._migrate_ecwf_state()
    self._migrate_shard_state()
    self._validate_state()


def _long_life_snapshot(self):
    return structural_copy(self.state)


def long_life_acceleration_installed() -> bool:
    return bool(_LONG_LIFE)


def install_long_life_acceleration() -> None:
    """Opt in to every byte-exact accelerator: fingerprints, structural fingerprints, state copies.

    Canonical identity is unchanged: every digest equals the reference digest
    (``VERDANT_FINGERPRINT_VERIFY=1`` re-checks each one). Trusts the frozen-record invariant.
    """
    if _LONG_LIFE:
        return
    from . import fingerprint_cache, structural_fingerprints
    install_fingerprint_cache()
    fingerprint_cache.TRUST_FROZEN_RECORDS = True
    _LONG_LIFE["__init__"] = VerdantKernel.__dict__["__init__"]
    _LONG_LIFE["snapshot"] = VerdantKernel.__dict__["snapshot"]
    VerdantKernel.__init__ = _long_life_init
    VerdantKernel.snapshot = _long_life_snapshot
    structural_fingerprints.install_model_dump_patch()
    for name in [n for n in vars(VerdantKernel) if n.endswith("_structural_fingerprint")]:
        _LONG_LIFE[name] = VerdantKernel.__dict__[name]
        setattr(VerdantKernel, name, structural_fingerprints.accelerated(_LONG_LIFE[name], _record_cache))


def uninstall_long_life_acceleration() -> None:
    if not _LONG_LIFE:
        return
    from . import fingerprint_cache, structural_fingerprints
    for name, original in list(_LONG_LIFE.items()):
        setattr(VerdantKernel, name, original)
    _LONG_LIFE.clear(); _SHARED_CACHE.clear(); fingerprint_cache._LIST_PREFIX.clear(); fingerprint_cache._DIGEST_MEMO.clear()
    fingerprint_cache.TRUST_FROZEN_RECORDS = False
    structural_fingerprints.uninstall_model_dump_patch()
    uninstall_fingerprint_cache()


__all__ = [
    "install_long_life_acceleration",
    "uninstall_long_life_acceleration",
    "long_life_acceleration_installed",
    "structural_copy",
    "FingerprintCacheMismatch",
    "cached_state_fingerprint",
    "fingerprint_cache_installed",
    "install_fingerprint_cache",
    "uninstall_fingerprint_cache",
]
