"""Resumable, private native retention preflight.

Checkpoints are immutable, per-arm milestones. An interruption replays only
the uncommitted tail from the last verified milestone. No 12k learning claim.
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
import json
import os
from pathlib import Path

from verdant_kernel import VerdantKernel, checkpoint_bytes
from verdant_kernel.checkpoint import load_checkpoint_bytes
from verdant_math.long_horizon_preflight import __main__ as native

FORMAT = "long_horizon_resumable_v0.2"
_ROOT = Path(__file__).resolve().parents[2]
_SOURCES = (
    "requirements-lock.txt",
    "verdant_math/long_horizon_preflight/__main__.py",
    "verdant_math/long_horizon_preflight/resumable.py",
    "verdant_math/teaching_pilot.py",
    "verdant_claims/pipeline.py",
    "verdant_kernel/kernel.py",
    "verdant_kernel/models.py",
    "verdant_kernel/checkpoint.py",
    "cognitive_chunk_v2/pipeline.py",
)


def _error(message):
    raise native.PreflightError(message)


def _parse(path):
    raw = Path(path).read_bytes()
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise native.PreflightError("Malformed experiment receipt") from exc
    if not isinstance(data, dict) or native._json(data) != raw:
        _error("Noncanonical experiment receipt")
    return data


def _manifest(cycles, seeds):
    if (type(cycles) is not int or not 0 <= cycles <= 1000
        or not seeds or len(set(seeds)) != len(seeds)
        or any(type(s) is not int or s < 0 for s in seeds)):
        raise ValueError("Invalid frozen cycle count or unique seed set")
    milestones = sorted(set((0, cycles, *(p for p in native.PROBES if p <= cycles))))
    files = {p: native.digest((_ROOT / p).read_bytes()) for p in _SOURCES}
    return dict(version=FORMAT, cycles_per_arm=cycles, seeds=list(seeds),
                roles=list(native.ROLES), milestones=milestones,
                training_pairs=[list(p) for p in native.TRAIN],
                test_pairs=[dict(split=k, pair=list(v)) for k, v in native.PROBLEMS],
                code_sha256=files, grading_performed=False,
                purpose="native_private_retention_feasibility_only",
                authority_to_promote=False)


def _write(path, data):
    """Atomically publish one immutable member; discard only an orphan temporary."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        _error(f"Immutable member occupied: {path}")
    part = path.with_suffix(path.suffix + ".part")
    if part.exists():
        part.unlink()  # recovered under the exclusive run lock
    native._atomic_new(path, data)


@contextmanager
def _exclusive(root):
    """Advisory process lock for Windows and POSIX; no concurrent publishers."""
    lock_path = Path(root) / ".run.lock"
    with open(lock_path, "a+b") as f:
        if os.name == "nt":
            import msvcrt
            f.seek(0)
            if not f.read(1):
                f.seek(0)
                f.write(b"0")
                f.flush()
            f.seek(0)
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise native.PreflightError("Experiment already running") from exc
        else:
            import fcntl
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise native.PreflightError("Experiment already running") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f, fcntl.LOCK_UN)


def _stage_path(root, seed, role, cycle):
    return Path(root) / "stages" / f"seed-{seed}" / role / f"{cycle:05d}.vstage"


def _event_key(seed, role, cycle):
    return f"lh-v01:seed:{seed}:role:{role}:cycle:{cycle}"


def _chain(previous, transition):
    return native.digest((previous + ":" + transition).encode("ascii"))


def _save_stage(path, kernel, seed, role, cycle, prior, observations, teaching, chain):
    raw = checkpoint_bytes(kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint_bytes(raw))
    if (restored.fingerprint() != kernel.fingerprint()
        or checkpoint_bytes(restored.snapshot()) != raw
        or restored.state.cycle != cycle):
        _error("Native checkpoint reload is not exact")
    payload = dict(version=FORMAT, seed=seed, role=role, cycle=cycle,
                   previous_stage_sha256=prior,
                   checkpoint_sha256=native.digest(raw),
                   checkpoint_b64=base64.b64encode(raw).decode("ascii"),
                   kernel_fingerprint=kernel.fingerprint(),
                   teaching=teaching, transition_hash=chain,
                   probes=observations)
    raw_payload = native._json(payload)
    wrapper = dict(payload=payload, sha256=native.digest(raw_payload))
    _write(path, native._json(wrapper))
    return native.digest(native._json(wrapper))


def _load_stage(path, seed, role, cycle, previous_hash):
    wrapper = _parse(path)
    data = wrapper.get("payload")
    if not isinstance(data, dict) or wrapper.get("sha256") != native.digest(native._json(data)):
        _error("Checkpoint receipt digest mismatch")
    if any((data.get("version") != FORMAT, data.get("seed") != seed,
            data.get("role") != role, data.get("cycle") != cycle,
            data.get("previous_stage_sha256") != previous_hash)):
        _error("Checkpoint role/sequence/lineage mismatch")
    try:
        raw = base64.b64decode(data["checkpoint_b64"], validate=True)
        if native.digest(raw) != data["checkpoint_sha256"]:
            _error("Checkpoint bytes changed")
        kernel = VerdantKernel.from_state(load_checkpoint_bytes(raw))
        if (kernel.state.cycle != cycle
            or kernel.fingerprint() != data["kernel_fingerprint"]
            or checkpoint_bytes(kernel.snapshot()) != raw):
            _error("Checkpoint native state mismatch")
        expected_teaching = [
            (c, native.lesson_for(role, c)) for c in range(1, cycle + 1)
            if native.lesson_for(role, c) is not None
        ]
        actual_teaching = data["teaching"]
        if [(x["cycle"], tuple(x["pair"])) for x in actual_teaching] != expected_teaching:
            _error("Private teaching schedule diverged")
        if (len(kernel.state.processed_event_keys) != cycle
            or any(_event_key(seed, role, c) not in kernel.state.processed_event_keys
                   for c in range(1, cycle + 1))):
            _error("Checkpoint event lineage incomplete")
        transitions = {t.transition_id for t in kernel.state.transitions}
        if any(x["transition_id"] not in transitions for x in actual_teaching):
            _error("Checkpoint taught transition missing")
        if (not isinstance(data["transition_hash"], str)
            or len(data["transition_hash"]) != 64):
            _error("Invalid transition chain")
        if not data["probes"] or data["probes"][-1] != native._probe(kernel, cycle=cycle):
            _error("Saved probe does not match the native checkpoint")
        if [p["cycle"] for p in data["probes"]] != sorted(set(
            p for p in native.PROBES if p <= cycle
        ) | {cycle}):
            # Earlier nonstandard final milestones are allowed only in separate runs.
            _error("Saved probe milestone history mismatch")
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise native.PreflightError("Checkpoint stage is invalid") from exc
    return kernel, data, native.digest(native._json(wrapper))


def _resume_arm(root, manifest, seed, role):
    checkpoints = manifest["milestones"]
    previous_hash = None
    loaded = None
    found_gap = False
    for checkpoint in checkpoints:
        path = _stage_path(root, seed, role, checkpoint)
        if not path.exists():
            found_gap = True
            continue
        if found_gap:
            _error("Future milestone exists after missing checkpoint")
        loaded = _load_stage(path, seed, role, checkpoint, previous_hash)
        previous_hash = loaded[2]
    if loaded is None:
        kernel = VerdantKernel(
            seed=seed, state_dim=16, run_label=f"long-horizon-preflight-seed-{seed}")
        observations = [native._probe(kernel, cycle=0)]
        teaching = []
        chain = native.digest(b"empty-native-transition-history")
        h = _save_stage(_stage_path(root, seed, role, 0), kernel,
                        seed, role, 0, None, observations, teaching, chain)
        loaded = (kernel, dict(probes=observations, teaching=teaching,
                               transition_hash=chain), h)
        previous_hash = h
        current_cycle = 0
    else:
        current_cycle = loaded[1]["cycle"]
    kernel, data, previous_hash = loaded
    initial = VerdantKernel(
        seed=seed, state_dim=16, run_label=f"long-horizon-preflight-seed-{seed}"
    ).fingerprint()
    for milestone in checkpoints:
        if milestone <= current_cycle:
            continue
        for cycle in range(current_cycle + 1, milestone + 1):
            key = _event_key(seed, role, cycle)
            start = kernel.state.cycle
            pair = native.lesson_for(role, cycle)
            transition = (native._teach(kernel, key=key, pair=pair)
                          if pair is not None else
                          native._unrelated_experience(kernel, key=key, cycle=cycle))
            if kernel.state.cycle != start + 1:
                _error("Nonproductive native cycle")
            data["transition_hash"] = _chain(data["transition_hash"], transition)
            if pair is not None:
                data["teaching"].append(
                    dict(cycle=cycle, pair=list(pair), transition_id=transition))
        data["probes"].append(native._probe(kernel, cycle=milestone))
        previous_hash = _save_stage(_stage_path(root, seed, role, milestone),
                                    kernel, seed, role, milestone, previous_hash,
                                    data["probes"], data["teaching"], data["transition_hash"])
        current_cycle = milestone
        print(f"Checkpoint saved: seed={seed}, role={role}, cycle={milestone}", flush=True)
    if kernel.state.cycle != manifest["cycles_per_arm"]:
        _error("Arm ended before its frozen cycle limit")
    return dict(seed=seed, role=role, initial_fingerprint=initial,
                final_fingerprint=kernel.fingerprint(),
                native_cycles=kernel.state.cycle, teaching=data["teaching"],
                transition_ids_sha256=data["transition_hash"], probes=data["probes"])


def _run(root):
    manifest = _parse(root / "manifest.json")
    expected = _manifest(manifest["cycles_per_arm"], tuple(manifest["seeds"]))
    if manifest != expected:
        _error("Frozen trial, source code or runtime definition has changed")
    arms = []
    for seed in manifest["seeds"]:
        for role in native.ROLES:
            arms.append(_resume_arm(root, manifest, seed, role))
    output = dict(version=native.VERSION,
                  purpose="native_persistence_and_direct_recall_feasibility",
                  cycles_per_arm=manifest["cycles_per_arm"], seeds=manifest["seeds"],
                  roles=list(native.ROLES), probe_cycles=manifest["milestones"],
                  training_pairs=manifest["training_pairs"],
                  test_pairs=manifest["test_pairs"],
                  no_autonomous_learning_claim=True, canonical_commit_permitted=False,
                  grading_performed=False, arms=arms)
    path = root / "responses.json"
    exact = native._json(output)
    if path.exists():
        if path.read_bytes() != exact:
            _error("Existing completed response batch differs from checkpoint history")
        return path
    _write(path, exact)
    return path


def start(output_dir, *, cycles=1000, seeds=native.SEEDS):
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=False)
    with _exclusive(root):
        _write(root / "manifest.json", native._json(_manifest(cycles, seeds)))
        return _run(root)


def resume(output_dir):
    root = Path(output_dir)
    if not (root / "manifest.json").is_file():
        _error("No immutable experiment manifest to resume")
    with _exclusive(root):
        return _run(root)

def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    begin = sub.add_parser("start", help="Begin new immutable native cohort")
    begin.add_argument("output_dir")
    begin.add_argument("--cycles", type=int, default=1000)
    cont = sub.add_parser("resume", help="Validate and resume interrupted cohort")
    cont.add_argument("output_dir")
    progress = sub.add_parser("status", help="Read milestones without running cycles")
    progress.add_argument("output_dir")
    args = parser.parse_args(argv)
    if args.action == "start":
        print(start(args.output_dir, cycles=args.cycles), flush=True)
    elif args.action == "resume":
        print(resume(args.output_dir), flush=True)
    else:
        root = Path(args.output_dir)
        manifest = _parse(root / "manifest.json")
        if manifest != _manifest(manifest["cycles_per_arm"], tuple(manifest["seeds"])):
            _error("Frozen manifest or source code has changed")
        with _exclusive(root):
            for seed in manifest["seeds"]:
                for role in manifest["roles"]:
                    last = None
                    previous = None
                    missing = False
                    for n in manifest["milestones"]:
                        path = _stage_path(root, seed, role, n)
                        if path.exists():
                            if missing:
                                _error("Found later milestone after a missing predecessor")
                            _, _, previous = _load_stage(path, seed, role, n, previous)
                            last = n
                        else:
                            missing = True
                    print(f"seed={seed} role={role} durable_cycle={last} / {manifest['cycles_per_arm']}")
            print("complete_response_batch=" + str((root / "responses.json").is_file()))


if __name__ == "__main__":
    main()
