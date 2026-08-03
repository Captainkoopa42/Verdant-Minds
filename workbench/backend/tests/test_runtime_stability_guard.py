from __future__ import annotations

from types import SimpleNamespace

from verdant_workbench.runtime_stability import run_queue_is_executing


class _Thread:
    def __init__(self, alive: bool) -> None:
        self._alive = alive

    def is_alive(self) -> bool:
        return self._alive


class _Service:
    def __init__(self, state: str, thread=None) -> None:
        self.control = SimpleNamespace(state=state, thread=thread)

    def _control(self, run_id: str):
        assert run_id == "run_test"
        return self.control


def test_running_queue_defers_historical_explorer_timeline():
    assert run_queue_is_executing(_Service("running"), "run_test") is True


def test_live_queue_thread_defers_timeline_even_during_state_transition():
    assert run_queue_is_executing(_Service("paused", _Thread(True)), "run_test") is True


def test_idle_run_allows_historical_explorer_timeline():
    assert run_queue_is_executing(_Service("idle", _Thread(False)), "run_test") is False
