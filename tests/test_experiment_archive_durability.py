from __future__ import annotations

import os
import select
import signal
import threading
from pathlib import Path

import pytest

from verdant_kernel import VerdantKernel
from verdant_obligations import (
    SimulationLedger,
    experiment_archive_bytes,
    load_experiment_archive,
    save_experiment_archive,
)


pytestmark = pytest.mark.skipif(
    os.name != "posix" or not hasattr(os, "fork"),
    reason="controlled process termination requires POSIX fork semantics",
)


def _state(seed: int) -> tuple[VerdantKernel, SimulationLedger]:
    return (
        VerdantKernel(
            seed=seed,
            state_dim=16,
            run_label=f"archive-durability-{seed}",
        ),
        SimulationLedger(),
    )


def _read_marker(file_descriptor: int, *, timeout: float = 10.0) -> bytes:
    readable, _, _ = select.select([file_descriptor], [], [], timeout)
    if not readable:
        pytest.fail("child archive writer did not reach its durability gate")
    marker = os.read(file_descriptor, 1)
    if marker != b"R":
        pytest.fail(f"child archive writer failed before its gate: {marker!r}")
    return marker


def _phase_paused_writer(
    path: Path,
    seed: int,
    phase: str,
    ready_file_descriptor: int,
) -> None:
    import verdant_obligations.experiment_archive as archive_module

    try:
        if phase == "before_replace":

            def pause_before_replace(_source: Path, _target: Path) -> None:
                os.write(ready_file_descriptor, b"R")
                while True:
                    signal.pause()

            archive_module.os.replace = pause_before_replace
        elif phase == "after_replace":
            real_fsync = archive_module.os.fsync
            fsync_count = 0

            def pause_before_directory_sync(file_descriptor: int) -> None:
                nonlocal fsync_count
                fsync_count += 1
                if fsync_count == 2:
                    os.write(ready_file_descriptor, b"R")
                    while True:
                        signal.pause()
                real_fsync(file_descriptor)

            archive_module.os.fsync = pause_before_directory_sync
        else:  # pragma: no cover - helper misuse
            raise AssertionError(f"unknown durability phase: {phase}")

        kernel, ledger = _state(seed)
        save_experiment_archive(path, kernel, ledger)
    except BaseException:
        try:
            os.write(ready_file_descriptor, b"E")
        finally:
            os._exit(2)
    os._exit(3)


def _kill_at_phase(path: Path, seed: int, phase: str) -> None:
    read_file_descriptor, write_file_descriptor = os.pipe()
    process_id = os.fork()
    if process_id == 0:
        os.close(read_file_descriptor)
        _phase_paused_writer(path, seed, phase, write_file_descriptor)

    os.close(write_file_descriptor)
    reaped = False
    try:
        _read_marker(read_file_descriptor)
        os.kill(process_id, signal.SIGKILL)
        _, status = os.waitpid(process_id, 0)
        reaped = True
        assert os.WIFSIGNALED(status)
        assert os.WTERMSIG(status) == signal.SIGKILL
    finally:
        os.close(read_file_descriptor)
        if not reaped:
            try:
                os.kill(process_id, signal.SIGKILL)
            except ProcessLookupError:
                pass
            os.waitpid(process_id, 0)


def test_process_kill_exposes_old_or_new_archive_never_partial(
    tmp_path: Path,
) -> None:
    for phase, candidate_visible in (
        ("before_replace", False),
        ("after_replace", True),
    ):
        directory = tmp_path / phase
        directory.mkdir()
        path = directory / "experiment.vob"
        initial_kernel, initial_ledger = _state(9100)
        initial = experiment_archive_bytes(initial_kernel, initial_ledger)
        save_experiment_archive(path, initial_kernel, initial_ledger)

        candidate_kernel, candidate_ledger = _state(9101)
        candidate = experiment_archive_bytes(candidate_kernel, candidate_ledger)
        _kill_at_phase(path, 9101, phase)

        visible = candidate if candidate_visible else initial
        assert path.read_bytes() == visible
        restored_kernel, restored_ledger = load_experiment_archive(path)
        assert experiment_archive_bytes(restored_kernel, restored_ledger) == visible
        temporary_paths = list(directory.glob(".experiment.vob.*.tmp"))
        if candidate_visible:
            assert temporary_paths == []
        else:
            assert len(temporary_paths) == 1
            assert temporary_paths[0].read_bytes() == candidate

        later_kernel, later_ledger = _state(9102)
        later = experiment_archive_bytes(later_kernel, later_ledger)
        save_experiment_archive(path, later_kernel, later_ledger)
        assert path.read_bytes() == later
        restored_kernel, restored_ledger = load_experiment_archive(path)
        assert experiment_archive_bytes(restored_kernel, restored_ledger) == later


def _gated_writer(
    path: Path,
    seed: int,
    ready_file_descriptor: int,
    go_file_descriptor: int,
) -> None:
    import verdant_obligations.experiment_archive as archive_module

    real_replace = archive_module.os.replace

    def gated_replace(source: Path, target: Path) -> None:
        os.write(ready_file_descriptor, b"R")
        if os.read(go_file_descriptor, 1) != b"G":
            raise RuntimeError("parent did not release archive writer")
        real_replace(source, target)

    archive_module.os.replace = gated_replace
    try:
        kernel, ledger = _state(seed)
        save_experiment_archive(path, kernel, ledger)
    except BaseException:
        try:
            os.write(ready_file_descriptor, b"E")
        finally:
            os._exit(2)
    os._exit(0)


def test_competing_process_writers_never_expose_a_torn_archive(
    tmp_path: Path,
) -> None:
    path = tmp_path / "experiment.vob"
    initial_kernel, initial_ledger = _state(9200)
    initial = experiment_archive_bytes(initial_kernel, initial_ledger)
    save_experiment_archive(path, initial_kernel, initial_ledger)

    seeds = tuple(range(9201, 9207))
    candidates = {
        experiment_archive_bytes(*_state(seed))
        for seed in seeds
    }
    known_archives = {initial, *candidates}
    children: list[tuple[int, int, int]] = []
    for seed in seeds:
        ready_read, ready_write = os.pipe()
        go_read, go_write = os.pipe()
        process_id = os.fork()
        if process_id == 0:
            os.close(ready_read)
            os.close(go_write)
            _gated_writer(path, seed, ready_write, go_read)
        os.close(ready_write)
        os.close(go_read)
        children.append((process_id, ready_read, go_write))

    observed = [path.read_bytes()]
    reader_errors: list[BaseException] = []
    stop_reader = threading.Event()

    def sample_archive() -> None:
        try:
            while not stop_reader.is_set():
                observed.append(path.read_bytes())
        except BaseException as error:  # pragma: no cover - diagnostic guard
            reader_errors.append(error)

    reader: threading.Thread | None = None
    reaped_processes: set[int] = set()
    try:
        for _, ready_read, _ in children:
            _read_marker(ready_read)
            os.close(ready_read)
        reader = threading.Thread(target=sample_archive, daemon=True)
        reader.start()
        for _, _, go_write in children:
            os.write(go_write, b"G")
            os.close(go_write)
        for process_id, _, _ in children:
            _, status = os.waitpid(process_id, 0)
            reaped_processes.add(process_id)
            assert os.WIFEXITED(status)
            assert os.WEXITSTATUS(status) == 0
        children.clear()
    finally:
        stop_reader.set()
        if reader is not None:
            reader.join(timeout=5.0)
            assert not reader.is_alive()
        for process_id, ready_read, go_write in children:
            for file_descriptor in (ready_read, go_write):
                try:
                    os.close(file_descriptor)
                except OSError:
                    pass
            if process_id not in reaped_processes:
                try:
                    os.kill(process_id, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                os.waitpid(process_id, 0)

    observed.append(path.read_bytes())
    assert reader_errors == []
    assert set(observed) <= known_archives
    final = path.read_bytes()
    assert final in candidates
    restored_kernel, restored_ledger = load_experiment_archive(path)
    assert experiment_archive_bytes(restored_kernel, restored_ledger) == final
    assert list(tmp_path.glob(".experiment.vob.*.tmp")) == []
