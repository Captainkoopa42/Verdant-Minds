"""Opt-in, checkpointed structural-transfer trial on Verdant's native claim substrate.

A bounded, handwritten path interpreter composes separately taught opaque
successor claims; its destination is never supplied as a lesson. This tests
scaffolded path composition, NOT independent rule discovery or general agency.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
from pathlib import Path

from verdant_claims import ClaimLearningPipeline
from verdant_kernel import ClaimPolarity, ClaimSourceClass, VerdantKernel, checkpoint_bytes
from verdant_kernel.checkpoint import load_checkpoint_bytes
from verdant_math.counting import pilot as native_count
from verdant_math.long_horizon_preflight import __main__ as util
from verdant_math.long_horizon_preflight import resumable as persistence

VERSION = "verdant_structural_transfer_v0.1"
ROLES = ("progressive", "exact_null", "no_rule", "incomplete", "wrong_link")
SEEDS = (79101, 79102, 79103)
MILESTONES = (0, 250, 500, 750, 1000)
EDGE_CYCLES = tuple(75 + 50 * n for n in range(12))
RULE_CYCLE = 25
PROCEDURE = "route:procedure:follow"
PREDICATE = "route_next"
RULE_PREDICATE = "route_uses_walk_rule"
RULE = "route:rule:one_per_step"
# Interim diagnostics (not final examination) are intentionally disjoint.
DIAGNOSTICS = ((0, 1), (3, 1), (6, 1), (9, 1),
               (0, 2), (3, 2), (6, 2), (8, 2))
FINAL = (
    ("direct", (1, 1)), ("direct", (2, 1)),
    ("direct", (4, 1)), ("direct", (7, 1)),
    ("short", (1, 2)), ("short", (2, 2)),
    ("short", (4, 2)), ("short", (7, 2)),
    ("transfer", (0, 3)), ("transfer", (1, 3)),
    ("transfer", (2, 3)), ("transfer", (3, 3)),
    ("transfer", (0, 4)), ("transfer", (2, 4)),
    ("transfer", (4, 4)), ("transfer", (6, 4)),
    ("boundary", (10, 3)), ("boundary", (11, 2)),
    ("boundary", (12, 1)), ("boundary", (9, 4)),
)
_MISSING = frozenset((5, 8))
_BAD_EDGE = 5
_BAD_TARGET = 9
_CODE_PATHS = (
    "requirements-lock.txt",
    "verdant_math/structural_transfer/experiment.py",
    "verdant_math/counting/pilot.py",
    "verdant_math/long_horizon_preflight/__main__.py",
    "verdant_math/long_horizon_preflight/resumable.py",
    "verdant_claims/pipeline.py",
    "verdant_kernel/kernel.py",
    "verdant_kernel/models.py",
    "verdant_kernel/checkpoint.py",
    "cognitive_chunk_v2/pipeline.py",
)
_ROOT = Path(__file__).resolve().parents[2]
_LABEL = re.compile(r"route:node:[0-9a-f]{24}\Z")


class TransferIntegrityError(util.PreflightError):
    """Native learning, staging, provenance or response contract is invalid."""


def _fail(message):
    raise TransferIntegrityError(message)


def _nodes(seed):
    """Opaque deterministic references; never decode an answer from an ID."""
    return tuple("route:node:" + hashlib.sha256(
        f"structural-transfer:v0.1:{seed}:node:{i}".encode()).hexdigest()[:24]
        for i in range(13))


def _case_spec(seed, final):
    nodes = _nodes(seed)
    cases = FINAL if final else tuple(("diagnostic", p) for p in DIAGNOSTICS)
    return tuple(dict(split=split, start=nodes[a], steps=b,
                      expected=nodes[a + b] if a + b <= 12 else None)
                 for split, (a, b) in cases)


def _request(spec):
    # Expected endpoint is NEVER passed to the native responder.
    return dict(start=spec["start"], steps=spec["steps"])


def _validate_design():
    pairs = [(a, b) for _, (a, b) in FINAL]
    assert len(pairs) == 20 and len(set(pairs)) == len(pairs)
    assert not set(pairs).intersection(DIAGNOSTICS)
    assert all(b in (1, 2, 3, 4) for _, b in pairs)
    assert all(a+b <= 12 for name, (a, b) in FINAL if name != "boundary")
    assert all(a+b > 12 for name, (a, b) in FINAL if name == "boundary")


def _manifest(cycles, seeds):
    if (type(cycles) is not int or not 0 <= cycles <= 1000 or not seeds
        or len(set(seeds)) != len(seeds)
        or any(type(s) is not int or s < 0 for s in seeds)):
        raise ValueError("Invalid cycles or unique nonnegative seed set")
    _validate_design()
    checkpoints = tuple(sorted({0, cycles, *(n for n in MILESTONES if n <= cycles)}))
    return dict(version=VERSION, cycles_per_arm=cycles,
                seeds=list(seeds), roles=list(ROLES), checkpoints=list(checkpoints),
                edge_schedule=list(EDGE_CYCLES), rule_cycle=RULE_CYCLE,
                diagnostic_cases=[dict(a=a, b=b) for a, b in DIAGNOSTICS],
                final_cases=[dict(split=group, a=a, b=b) for group, (a, b) in FINAL],
                native_sources={p: util.digest((_ROOT / p).read_bytes()) for p in _CODE_PATHS},
                experiment_scope="private_native_claim_and_scaffolded_path_composition_only",
                expected_answer_available_to_responder=False,
                canonical_promotion=False, grading_during_execution=False)


def _key(seed, cycle):
    # Identical source keys across independent copies make exact-null equality testable.
    return f"st-v01:seed:{seed}:cycle:{cycle}"


def _teach(kernel, seed, role, cycle):
    key = _key(seed, cycle)
    pipeline = ClaimLearningPipeline()
    if cycle == RULE_CYCLE:
        rule_supplied = role != "no_rule"
        if rule_supplied:
            result = pipeline.record_claim(
                kernel, event_key=key,
                native_description="Teacher supplies one native next-link traversal for each requested step.",
                subject_label=PROCEDURE, predicate=RULE_PREDICATE, object_label=RULE,
                polarity=ClaimPolarity.AFFIRMED,
                source_class=ClaimSourceClass.HUMAN_TESTIMONY,
                source_ref="structural-transfer-teacher://v01",
                rationale="Supplied execution scaffold; not discovered by Verdant.",
            ).kernel_result
        else:
            result = util._unrelated_experience(kernel, key=key, cycle=cycle)
        return (result.transition_id if rule_supplied else result), rule_supplied, "rule"
    if cycle in EDGE_CYCLES:
        index = EDGE_CYCLES.index(cycle)
        target = (_BAD_TARGET if role == "wrong_link" and index == _BAD_EDGE
                  else index + 1)
        supplied = not (role == "incomplete" and index in _MISSING)
        if supplied:
            names = _nodes(seed)
            result = pipeline.record_claim(
                kernel, event_key=key,
                native_description="Teacher states one opaque directed next relation.",
                subject_label=names[index], predicate=PREDICATE,
                object_label=names[target], polarity=ClaimPolarity.AFFIRMED,
                source_class=ClaimSourceClass.HUMAN_TESTIMONY,
                source_ref="structural-transfer-teacher://v01",
                rationale="Individual provided relation only; no path target supplied.",
            ).kernel_result
            return result.transition_id, True, f"edge:{index}"
        return util._unrelated_experience(kernel, key=key, cycle=cycle), False, f"edge:{index}"
    return util._unrelated_experience(kernel, key=key, cycle=cycle), False, "interference"


def _respond(kernel, request):
    # No arithmetic grader, edge schedule, expected endpoint or training table.
    start, steps = request["start"], request["steps"]
    if not isinstance(start, str) or _LABEL.fullmatch(start) is None:
        raise TransferIntegrityError("Invalid opaque node reference")
    if type(steps) is not int or not 1 <= steps <= 4:
        raise TransferIntegrityError("Invalid bounded path request")
    before = kernel.fingerprint()
    rule = native_count._lookup(kernel, PROCEDURE, RULE_PREDICATE)
    path = []
    current = start
    seen = {start}
    blocked = None
    status = "abstained"
    reason = "missing_rule" if rule.status == "missing" else "blocked_rule"
    if rule.status == "found" and rule.label == RULE:
        reason = "missing_edge"
        for hop in range(steps):
            link = native_count._lookup(kernel, current, PREDICATE)
            if link.status != "found":
                reason = link.status + "_edge"
                blocked = dict(claim_refs=list(link.claim_refs),
                               evidence_refs=list(link.evidence_refs))
                break
            if not isinstance(link.label, str) or _LABEL.fullmatch(link.label) is None:
                reason = "invalid_target"
                break
            if link.label in seen:
                reason = "cyclic_path"
                break
            path.append(dict(hop=hop, source=current, target=link.label,
                             claim_ref=link.claim_refs[0],
                             evidence_refs=list(link.evidence_refs)))
            current = link.label
            seen.add(current)
        else:
            status, reason = "derived", "native_path_completed"
    elif rule.status == "found":
        reason = "unsupported_rule"
    if kernel.fingerprint() != before:
        _fail("Read-only native response mutated kernel state")
    return dict(status=status, reason=reason,
                endpoint=current if status == "derived" else None,
                rule_claim_refs=list(rule.claim_refs),
                rule_evidence_refs=list(rule.evidence_refs),
                steps=path, blocked=blocked)


def _probe(kernel, seed, cycle, *, final=False):
    specs = _case_spec(seed, final=final)
    before = kernel.fingerprint()
    responses = [dict(request=_request(spec),
                      response=_respond(kernel, _request(spec))) for spec in specs]
    if kernel.fingerprint() != before:
        _fail("Native probe modified private state")
    return dict(cycle=cycle, evaluation="final" if final else "diagnostic",
                kernel_fingerprint=before, records=responses)


def _recompute_chain(kernel, seed, cycle):
    if (kernel.state.cycle != cycle or len(kernel.state.transitions) != cycle
        or len(kernel.state.processed_event_keys) != cycle
        or any(_key(seed, n) not in kernel.state.processed_event_keys
               for n in range(1, cycle + 1))):
        _fail("Native cycle or processed-event lineage mismatch")
    chain = util.digest(b"empty-structural-transfer-native-history")
    for transition in kernel.state.transitions:
        chain = util.digest((chain + ":" + transition.transition_id).encode())
    return chain


def _stage_path(root, seed, role, cycle):
    return root / "stages" / f"seed-{seed}" / role / f"{cycle:05d}.vst"


def _load_stage(path, seed, role, cycle, predecessor):
    wrapper = persistence._parse(path)
    data = wrapper.get("data")
    if not isinstance(data, dict) or wrapper.get("digest") != util.digest(util._json(data)):
        _fail("Noncanonical or changed stage")
    if any((data.get("version") != VERSION, data.get("seed") != seed,
            data.get("role") != role, data.get("cycle") != cycle,
            data.get("predecessor") != predecessor)):
        _fail("Foreign stage or broken predecessor lineage")
    try:
        checkpoint = base64.b64decode(data["checkpoint"], validate=True)
        if util.digest(checkpoint) != data["checkpoint_sha256"]:
            _fail("Changed checkpoint bytes")
        kernel = VerdantKernel.from_state(load_checkpoint_bytes(checkpoint))
        if (checkpoint_bytes(kernel.snapshot()) != checkpoint
            or kernel.fingerprint() != data["fingerprint"]):
            _fail("Checkpoint reload mismatch")
        if _recompute_chain(kernel, seed, cycle) != data["transition_chain"]:
            _fail("Transition lineage changed")
        actual_teaching = data["teaching"]
        expected_teaching = [(n, "rule" if n == RULE_CYCLE else
                              f"edge:{EDGE_CYCLES.index(n)}")
                             for n in range(1, cycle+1)
                             if n == RULE_CYCLE or n in EDGE_CYCLES]
        if [(x["cycle"], x["kind"]) for x in actual_teaching] != expected_teaching:
            _fail("Teaching schedule was altered")
        for n, kind in expected_teaching:
            item = next(x for x in actual_teaching if x["cycle"] == n)
            expected_supplied = not (
                (role == "no_rule" and n == RULE_CYCLE)
                or (role == "incomplete" and n in EDGE_CYCLES
                    and EDGE_CYCLES.index(n) in _MISSING))
            if item["supplied"] != expected_supplied:
                _fail("Teaching inclusion differs from frozen role")
        expected_probe_cycles = [n for n in MILESTONES if n <= cycle]
        if cycle not in expected_probe_cycles:
            expected_probe_cycles.append(cycle)
        if [p["cycle"] for p in data["probes"]] != expected_probe_cycles:
            _fail("Stage probe schedule mismatch")
        if data["probes"][-1] != _probe(kernel, seed, cycle,
                                     final=cycle == 1000):
            _fail("Stage probe no longer reproduces")
        if data["probes"][-1]["kernel_fingerprint"] != data["fingerprint"]:
            _fail("Stage probe checkpoint differs")
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise TransferIntegrityError("Invalid stage payload") from exc
    return kernel, data, util.digest(util._json(wrapper))


def _save_stage(path, kernel, seed, role, cycle, predecessor, history, teaching, probes):
    raw = checkpoint_bytes(kernel.snapshot())
    if (checkpoint_bytes(VerdantKernel.from_state(
            load_checkpoint_bytes(raw)).snapshot()) != raw):
        _fail("Native checkpoint is not exactly reloadable")
    payload = dict(version=VERSION, seed=seed, role=role,
                   cycle=cycle, predecessor=predecessor,
                   checkpoint=base64.b64encode(raw).decode("ascii"),
                   checkpoint_sha256=util.digest(raw),
                   fingerprint=kernel.fingerprint(),
                   transition_chain=history, teaching=list(teaching),
                   probes=list(probes))
    wrapper = dict(data=payload, digest=util.digest(util._json(payload)))
    persistence._write(path, util._json(wrapper))
    return util.digest(util._json(wrapper))


def _run_arm(root, manifest, seed, role):
    checkpoints = manifest["checkpoints"]
    latest, previous = None, None
    missing = False
    for step in checkpoints:
        path = _stage_path(root, seed, role, step)
        if not path.is_file():
            missing = True
            continue
        if missing:
            _fail("Later stage exists without predecessor")
        latest = _load_stage(path, seed, role, step, previous)
        previous = latest[2]
    if latest is None:
        kernel = VerdantKernel(seed=seed, state_dim=16,
                               run_label=f"transfer-seed-{seed}")
        stage = [_probe(kernel, seed, 0)]
        history = _recompute_chain(kernel, seed, 0)
        previous = _save_stage(_stage_path(root, seed, role, 0),
                               kernel, seed, role, 0, None, history, [], stage)
        latest = (kernel, dict(cycle=0, transition_chain=history,
                              teaching=[], probes=stage), previous)
    kernel, data, previous = latest
    start = data["cycle"]
    history, teaching, probes = data["transition_chain"], data["teaching"], data["probes"]
    for checkpoint in checkpoints:
        if checkpoint <= start:
            continue
        for cycle in range(kernel.state.cycle + 1, checkpoint + 1):
            before = kernel.state.cycle
            transition, supplied, kind = _teach(kernel, seed, role, cycle)
            if kernel.state.cycle != before + 1:
                _fail("Native operation did not advance precisely one cycle")
            history = util.digest((history + ":" + transition).encode())
            if kind != "interference":
                teaching.append(dict(cycle=cycle, kind=kind,
                                     supplied=supplied, transition_id=transition))
        if _recompute_chain(kernel, seed, checkpoint) != history:
            _fail("Native transitions differ from recorded history")
        probes.append(_probe(kernel, seed, checkpoint,
                             final=checkpoint == 1000))
        previous = _save_stage(_stage_path(root, seed, role, checkpoint),
                               kernel, seed, role, checkpoint, previous,
                               history, teaching, probes)
        print(f"Saved: seed={seed} role={role} cycle={checkpoint}", flush=True)
    if kernel.state.cycle != manifest["cycles_per_arm"]:
        _fail("Arm ended before frozen limit")
    return dict(seed=seed, role=role, native_cycles=kernel.state.cycle,
                final_fingerprint=kernel.fingerprint(),
                teaching=teaching, probes=probes, final_stage_sha256=previous)


def _run(root):
    manifest = persistence._parse(root / "manifest.json")
    if manifest != _manifest(manifest["cycles_per_arm"], tuple(manifest["seeds"])):
        _fail("Manifest or source file digest differs from frozen trial")
    results = []
    for seed in manifest["seeds"]:
        arms = {}
        for role in manifest["roles"]:
            arm = _run_arm(root, manifest, seed, role)
            arms[role] = arm
            results.append(arm)
        if arms["progressive"]["final_fingerprint"] != arms["exact_null"]["final_fingerprint"]:
            _fail("Independent exact-null copies diverged")
        if arms["progressive"]["probes"] != arms["exact_null"]["probes"]:
            _fail("Exact-null native response traces diverged")
    output = dict(version=VERSION, cycles_per_arm=manifest["cycles_per_arm"],
                  seeds=manifest["seeds"], roles=manifest["roles"],
                  checkpoints=manifest["checkpoints"], grading_performed=False,
                  immutable_manifest_sha256=util.digest(util._json(manifest)),
                  arms=results, interpretation="scaffolded_composition_only",
                  canonical_promotion=False)
    raw = util._json(output)
    destination = root / "responses.json"
    if destination.exists():
        if destination.read_bytes() != raw:
            _fail("Existing responses differ from verified stages")
        return destination
    persistence._write(destination, raw)
    return destination


def start(path, *, cycles=1000, seeds=SEEDS):
    root = Path(path)
    root.mkdir(parents=True, exist_ok=False)
    with persistence._exclusive(root):
        persistence._write(root / "manifest.json", util._json(_manifest(cycles, seeds)))
        return _run(root)


def resume(path):
    root = Path(path)
    if not (root / "manifest.json").is_file():
        _fail("No frozen manifest at this path")
    with persistence._exclusive(root):
        return _run(root)


def status(path):
    root = Path(path)
    with persistence._exclusive(root):
        manifest = persistence._parse(root / "manifest.json")
        if manifest != _manifest(manifest["cycles_per_arm"], tuple(manifest["seeds"])):
            _fail("Frozen manifest changed")
        for seed in manifest["seeds"]:
            for role in manifest["roles"]:
                last, previous, gap = None, None, False
                for n in manifest["checkpoints"]:
                    path = _stage_path(root, seed, role, n)
                    if not path.exists():
                        gap = True
                        continue
                    if gap:
                        _fail("Stage ordering hole")
                    _, _, previous = _load_stage(path, seed, role, n, previous)
                    last = n
                print(f"seed={seed} role={role} durable_cycle={last} / {manifest['cycles_per_arm']}")
        print("complete_response_batch=" + str((root / "responses.json").is_file()))


def grade(path):
    root = Path(path)
    # Validate all previous stage identities and response batch before grading.
    with persistence._exclusive(root):
        responses = _run(root)
        raw = responses.read_bytes()
        data = json.loads(raw)
        manifest = persistence._parse(root / "manifest.json")
        graded = []
        for arm in data["arms"]:
            records = []
            for probe in arm["probes"]:
                final = probe["evaluation"] == "final"
                specs = _case_spec(arm["seed"], final)
                if len(specs) != len(probe["records"]):
                    _fail("Missing or additional evaluation cases")
                cases = []
                for candidate, spec in zip(probe["records"], specs):
                    if candidate["request"] != _request(spec):
                        _fail("Response case or order altered")
                    reply = candidate["response"]
                    actual = reply["endpoint"]
                    grade_value = ("abstained" if actual is None else
                                   "correct" if actual == spec["expected"]
                                   else "incorrect")
                    cases.append(dict(split=spec["split"], grade=grade_value,
                                      reason=reply["reason"]))
                records.append(dict(cycle=probe["cycle"], assessment=probe["evaluation"],
                                    correct=sum(c["grade"]=="correct" for c in cases),
                                    incorrect=sum(c["grade"]=="incorrect" for c in cases),
                                    abstained=sum(c["grade"]=="abstained" for c in cases),
                                    total=len(cases), by_case=cases))
            graded.append(dict(seed=arm["seed"], role=arm["role"], probes=records))
        receipt = dict(version=VERSION, response_sha256=util.digest(raw),
                       manifest_sha256=util.digest(util._json(manifest)),
                       grader="external_exact_declared_endpoint",
                       computed_after_durable_responses=True, grading=graded,
                       claims={"independent_rule_discovery":False,
                               "unscaffolded_transfer":False,
                               "policy_rewrite_authority":False})
        result = root / "grades.json"
        contents = util._json(receipt)
        if result.exists():
            if result.read_bytes() != contents:
                _fail("Previously committed grade differs")
            return result
        persistence._write(result, contents)
        return result



def report(path):
    """Print validated stage/checkpoint scores, including held-out category totals."""
    destination = grade(path)
    receipt = persistence._parse(destination)
    print("Verified response SHA-256:", receipt["response_sha256"])
    rows = receipt["grading"]
    print("seed role cycle assessment correct incorrect abstained total")
    for row in rows:
        final = row["probes"][-1]
        print(row["seed"], row["role"], final["cycle"], final["assessment"],
              final["correct"], final["incorrect"], final["abstained"], final["total"])
    print("Group by question split (all three seeds)")
    for role in ROLES:
        by_split = {}
        for row in rows:
            if row["role"] != role:
                continue
            final = row["probes"][-1]
            for case in final["by_case"]:
                group = case["split"]
                if group not in by_split:
                    by_split[group] = dict(correct=0, incorrect=0, abstained=0)
                by_split[group][case["grade"]] += 1
        for group, counts in sorted(by_split.items()):
            print(role, group, "correct", counts["correct"],
                  "incorrect", counts["incorrect"],
                  "abstained", counts["abstained"],
                  "total", sum(counts.values()))
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    new = sub.add_parser("start")
    new.add_argument("directory")
    new.add_argument("--cycles", type=int, default=1000)
    for name in ("resume", "status", "grade", "report"):
        sub.add_parser(name).add_argument("directory")
    args = parser.parse_args(argv)
    if args.cmd == "start":
        result = start(args.directory, cycles=args.cycles)
    elif args.cmd == "resume":
        result = resume(args.directory)
    elif args.cmd == "grade":
        result = grade(args.directory)
    elif args.cmd == "report":
        result = report(args.directory)
    else:
        status(args.directory)
        return
    print(result, flush=True)


if __name__ == "__main__":
    main()
