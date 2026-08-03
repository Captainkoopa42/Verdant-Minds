from __future__ import annotations

import pytest

from verdant_workbench.worker import EngineWorkerSupervisor


class _AliveProcess:
    def is_alive(self) -> bool:
        return True


class _NoReplyConnection:
    def __init__(self) -> None:
        self.last_timeout: float | None = None
        self.sent = None

    def send(self, payload) -> None:
        self.sent = payload

    def poll(self, timeout: float) -> bool:
        self.last_timeout = timeout
        return False


def _supervisor() -> tuple[EngineWorkerSupervisor, _NoReplyConnection]:
    connection = _NoReplyConnection()
    worker = EngineWorkerSupervisor(_AliveProcess(), connection, run_id="run_test", organism_id="org_test")
    return worker, connection


def test_living_explorer_timeline_gets_long_timeout_and_controlled_error():
    worker, connection = _supervisor()
    with pytest.raises(RuntimeError, match="Living Explorer is temporarily busy"):
        worker.request("living_explorer_timeline")
    assert connection.last_timeout == 60.0


def test_living_explorer_frame_gets_intermediate_timeout():
    worker, connection = _supervisor()
    with pytest.raises(RuntimeError, match="Living Explorer is temporarily busy"):
        worker.request("living_explorer_frame")
    assert connection.last_timeout == 30.0


def test_non_explorer_worker_requests_keep_normal_timeout_behavior():
    worker, connection = _supervisor()
    with pytest.raises(TimeoutError, match="timed out handling metrics"):
        worker.request("metrics")
    assert connection.last_timeout == 20.0
