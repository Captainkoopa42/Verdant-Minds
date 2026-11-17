"""Opt-in pytest plugin: run an existing suite with every byte-exact long-life accelerator.

    VERDANT_FINGERPRINT_VERIFY=1 python -m pytest -p sidecar_acceleration.pytest_long_life_plugin tests/...

With ``VERDANT_FINGERPRINT_VERIFY=1`` every accelerated digest is recomputed through the
reference definition, and every developmental beat is followed by a check that the state
it superseded still has its original reference fingerprint (nothing reached back through a
shared record and changed it).
"""
from __future__ import annotations

import os

from sidecar_acceleration import install_long_life_acceleration, uninstall_long_life_acceleration

_ORIGINAL = {}


class SupersededStateMutated(RuntimeError):
    pass


def pytest_configure(config) -> None:  # noqa: ARG001
    install_long_life_acceleration()
    if os.environ.get("VERDANT_FINGERPRINT_VERIFY") == "1":
        from verdant_development import VerdantDevelopmentPipeline

        _ORIGINAL["advance"] = VerdantDevelopmentPipeline.advance

        def advance(self, kernel, command):
            superseded = kernel.state
            before = superseded.fingerprint()            # reference definition
            result = _ORIGINAL["advance"](self, kernel, command)
            if superseded is not kernel.state and superseded.fingerprint() != before:
                raise SupersededStateMutated("A beat changed the state it replaced through a shared record.")
            return result

        VerdantDevelopmentPipeline.advance = advance


def pytest_unconfigure(config) -> None:  # noqa: ARG001
    if "advance" in _ORIGINAL:
        from verdant_development import VerdantDevelopmentPipeline

        VerdantDevelopmentPipeline.advance = _ORIGINAL.pop("advance")
    uninstall_long_life_acceleration()
