from __future__ import annotations

import pytest

from verdant_workbench.models import WorkerResponse
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


class _LateExplorerConnection:
    """First request times out, then its late response arrives before the next response."""

    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.poll_timeouts: list[float] = []
        self.poll_results = [False, True, True]
        self.recv_count = 0

    def send(self, payload) -> None:
        self.sent.append(payload)

    def poll(self, timeout: float) -> bool:
        self.poll_timeouts.append(timeout)
        return self.poll_results.pop(0)

    def recv(self):
        if self.recv_count == 0:
            request_id = self.sent[0]["request_id"]
            payload = {"late_explorer": True}
        else:
            request_id = self.sent[1]["request_id"]
            payload = {"metrics": "current"}
        self.recv_count += 1
        return WorkerResponse(request_id=request_id, ok=True, payload=payload).model_dump(mode="json")


class _MismatchedResponseConnection:
    def __init__(self) -> None:
        self.sent = None

    def send(self, payload) -> None:
        self.sent = payload

    def poll(self, timeout: float) -> bool:
        return True

    def recv(self):
        return WorkerResponse(request_id="wrong_request_id", ok=True, payload={"bad": True}).model_dump(mode="json")


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


def test_late_explorer_response_is_drained_before_next_request_is_sent():
    connection = _LateExplorerConnection()
    worker = EngineWorkerSupervisor(_AliveProcess(), connection, run_id="run_test", organism_id="org_test")

    with pytest.raises(RuntimeError, match="Living Explorer is temporarily busy"):
        worker.request("living_explorer_timeline")

    result = worker.request("metrics")

    assert result == {"metrics": "current"}
    assert len(connection.sent) == 2
    assert connection.poll_timeouts == [60.0, 300.0, 20.0]
    assert connection.recv_count == 2


def test_response_request_id_mismatch_is_rejected():
    connection = _MismatchedResponseConnection()
    worker = EngineWorkerSupervisor(_AliveProcess(), connection, run_id="run_test", organism_id="org_test")

    with pytest.raises(RuntimeError, match="protocol response mismatch"):
        worker.request("metrics")
