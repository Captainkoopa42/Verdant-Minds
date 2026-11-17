"""Opt-in pytest plugin: run an existing suite with the fingerprint accelerator.

    VERDANT_FINGERPRINT_VERIFY=1 python -m pytest -p sidecar_acceleration.pytest_plugin tests/...

No test file is edited and nothing is installed unless this plugin is named
on the command line. With ``VERDANT_FINGERPRINT_VERIFY=1`` every accelerated
digest is recomputed through the reference definition and any difference
raises ``FingerprintCacheMismatch``.
"""
from __future__ import annotations

from sidecar_acceleration import install_fingerprint_cache, uninstall_fingerprint_cache


def pytest_configure(config) -> None:  # noqa: ARG001
    install_fingerprint_cache()


def pytest_unconfigure(config) -> None:  # noqa: ARG001
    uninstall_fingerprint_cache()
