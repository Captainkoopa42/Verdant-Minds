"""Opt-in V5/V5-X developmental VCpack experiment with passive obligation inspection.

Runs the genuine Verdant developmental heartbeat; never invokes authoritative
obligation mutations, Council promotion, simulation, refolding or external acts.
Each arm lives in a separate checkpointed kernel. All observations are sidecars.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
_WORKBENCH = _ROOT / "workbench" / "backend"
if str(_WORKBENCH) not in sys.path:
    sys.path.insert(0, str(_WORKBENCH))

from verdant_workbench.curriculum import (  # noqa: E402
    CurriculumCompileRequest, CurriculumCompiler, curriculum_pack_bundle_source,
    parse_curriculum_pack,
)
from verdant_compilation import VerdantCompilationPipeline  # noqa: E402
from verdant_development import VerdantDevelopmentPipeline  # noqa: E402
from verdant_development.v5x import V5XDevelopmentPipeline  # noqa: E402
from verdant_kernel import ExperienceCommand, VerdantKernel, checkpoint_bytes  # noqa: E402
from verdant_kernel.checkpoint import load_checkpoint_bytes  # noqa: E402
from verdant_obligations.detection import DependencyGapDetector  # noqa: E402
from verdant_obligations.contradictions import ContradictionObligationDetector  # noqa: E402
from verdant_thermodynamics.models import ThermodynamicState  # noqa: E402

VERSION = "vast_full_heartbeat_preflight_v0.1"
ARMS = ("v5", "v5x_observe", "kernel_only")
DEFAULT_SEEDS = (81001, 81002, 81003)
_SOURCE_FILES = (
    "requirements-lock.txt",
    "verdant_integrated/vast.py",
    "workbench/backend/verdant_workbench/curriculum.py",
    "verdant_kernel/kernel.py",
    "verdant_kernel/models.py",
    "verdant_kernel/checkpoint.py",
    "verdant_development/pipeline.py",
    "verdant_development/v5x.py",
    "verdant_workspace/pipeline.py",
    "verdant_plasticity/pipeline.py",
    "verdant_structures/pipeline.py",
    "verdant_compilation/pipeline.py",
    "verdant_obligations/detection.py",
    "verdant_obligations/contradictions.py",
    "verdant_thermodynamics/observer.py",
    "verdant_thermodynamics/models.py",
)


class StudyIntegrityError(RuntimeError):
    pass


def _fail(message):
    raise StudyIntegrityError(message)


def _json(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _load_json(path):
    raw = Path(path).read_bytes()
    try:
        obj = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise StudyIntegrityError(f"Invalid JSON receipt: {path}") from exc
    if not isinstance(obj, dict) or _json(obj) != raw:
        _fail(f"Noncanonical receipt: {path}")
    return obj


def _write_new(path, contents):
    """Atomic immutable publication; never replace an existing member."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        _fail(f"Immutable output already exists: {target}")
    temp = target.with_name(target.name + ".part")
    if temp.exists():
        _fail(f"Orphan temporary file requires inspection: {temp}")
    with open(temp, "xb") as writer:
        writer.write(contents)
        writer.flush()
        os.fsync(writer.fileno())
    if target.exists():
        _fail(f"Output appeared concurrently: {target}")
    os.replace(temp, target)


@contextmanager
def _lock(root):
    """Single local publisher on both Windows and POSIX."""
    lock_path = Path(root) / ".run.lock"
    with open(lock_path, "a+b") as handle:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            if not handle.read(1):
                handle.seek(0)
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise StudyIntegrityError("This study already has an active writer") from exc
        else:
            import fcntl
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise StudyIntegrityError("This study already has an active writer") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def _plan(pack_bytes, limit_sections):
    if not isinstance(limit_sections, int) or isinstance(limit_sections, bool) or limit_sections < 1:
        raise ValueError("At least one section must be selected")
    try:
        pack_text = pack_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StudyIntegrityError("VCpack must be UTF-8 JSON") from exc
    pack = parse_curriculum_pack(pack_text)
    active = [section for section in pack.sections if section.enabled]
    if not active or limit_sections > len(active):
        raise ValueError("Requested section count exceeds the enabled curriculum")
    if pack.language_scaffold.grammar_rules or pack.language_scaffold.lexicon or any(
        s.language_scaffold.grammar_rules or s.language_scaffold.lexicon
        for s in active[:limit_sections]
    ):
        _fail("V0.1 rejects separately executed grammar scaffolds; no silent omission")
    compiler = CurriculumCompiler()
    sections = []
    for section in active[:limit_sections]:
        _, bundle, chosen, probes, source = curriculum_pack_bundle_source(
            pack_text, (section.section_id,)
        )
        if len(chosen) != 1 or chosen[0].section_id != section.section_id:
            _fail("Pack section selection changed")
        compiled = compiler.compile(CurriculumCompileRequest(
            project_id="isolated-vast-study", title=section.title,
            source_format="teaching_bundle_json", source_text=source,
            state_dim=pack.state_dim,
        ))
        commands = tuple(ExperienceCommand.model_validate(c) for c in compiled.compiled_commands)
        if len(commands) != len(section.items):
            _fail("Compiler dropped or duplicated teaching items")
        sections.append(dict(
            id=section.section_id, title=section.title,
            commands=commands, tests=probes, compiled_sha256=compiled.compiled_sha256,
            warnings=compiled.warnings,
        ))
    keys = [command.event_key for section in sections for command in section["commands"]]
    if len(keys) != len(set(keys)):
        _fail("Duplicate experience event keys across selected sections")
    return pack, tuple(sections)


def _manifest(pack_bytes, sections, seeds, state_dim):
    if not seeds or any(type(n) is not int or n < 0 for n in seeds) or len(set(seeds)) != len(seeds):
        raise ValueError("Seeds must be nonnegative unique integers")
    return dict(
        schema=VERSION,
        pack_sha256=_digest(pack_bytes),
        state_dim=state_dim,
        seeds=list(seeds), arms=list(ARMS),
        section_ids=[s["id"] for s in sections],
        sections=[dict(id=s["id"], title=s["title"],
                       commands=len(s["commands"]),
                       compiled_sha256=s["compiled_sha256"],
                       probe_count=len(s["tests"]),
                       warning_count=len(s["warnings"])) for s in sections],
        source_sha256={path: _digest((_ROOT / path).read_bytes())
                       for path in _SOURCE_FILES},
        claims=dict(
            full_v5_heartbeat=True,
            v5x_thermodynamic_control=False,
            obligation_detectors_inspection_only=True,
            obligation_inquiry_executed=False,
            governed_p_q_promotion_executed=False,
            autonomous_learning_demonstrated=False,
            canonical_simulation_promotion=False,
            automatic_grading=False,
        ),
    )


def _stage_path(root, seed, arm, number):
    return root / "stages" / f"seed-{seed}" / arm / f"{number:03d}"


def _metrics(kernel):
    state = kernel.state
    return dict(
        cycle=state.cycle, concepts=len(state.concepts),
        relations=len(state.relations), claims=len(state.claims),
        contradictions=len(state.contradictions), evidence=len(state.evidence),
        plasticity_associations=len(state.plasticity_associations),
        structures=len(state.structures),
        structure_candidates=len(state.structure_candidates),
        layered_structures=len(state.layered_structures),
        workspace_items=len(state.workspace_items),
        obligation_kernels=len(state.obligation_kernels),
        transitions=len(state.transitions),
    )


def _inspect(kernel, section):
    """Read-only, source-identifiable observations; never treat a cue as a score."""
    before = kernel.fingerprint()
    by_label = {c.normalized_label: cid for cid, c in kernel.state.concepts.items()}
    compilation = VerdantCompilationPipeline()
    probes = []
    for test in section["tests"]:
        names = tuple(str(label).strip().lower() for label in test.cue_labels)
        missing = tuple(name for name in names if name not in by_label)
        if missing:
            probes.append(dict(test_id=test.test_id, status="unknown_cue",
                               unknown_labels=list(missing)))
            continue
        report = compilation.inspect(kernel, tuple(by_label[name] for name in names))
        probes.append(dict(test_id=test.test_id, status="inspected_not_graded",
                           report=report.model_dump(mode="json")))
    inspected_dependency, gaps = DependencyGapDetector().inspect(kernel)
    inspected_contradiction, conflicts = ContradictionObligationDetector().inspect(kernel)
    if kernel.fingerprint() != before:
        _fail("Observation changed canonical state")
    return dict(
        probe_type="read_only_compilation_inspection",
        diagnostic_probes=probes,
        dependency_detector_policy="default_requires_with_action_or_outcome_evidence",
        dependency_relations_inspected=len(inspected_dependency),
        dependency_gap_candidates=len(gaps),
        contradiction_records_inspected=len(inspected_contradiction),
        contradiction_candidates=len(conflicts),
        raw_depends_on_relations=sum(1 for r in kernel.state.relations.values()
                                     if r.relation_type == "depends_on"),
        observer_not_authorized_to_create_obligations=True,
        no_grading_claim=True,
    )


def _load_stage(root, seed, arm, number, predecessor, expected_cycle, expected_keys, section=None):
    base = _stage_path(root, seed, arm, number)
    receipt = _load_json(base.with_suffix(".json"))
    expected = dict(schema=VERSION, seed=seed, arm=arm, section_number=number,
                    predecessor_sha256=predecessor)
    if any(receipt.get(k) != v for k, v in expected.items()):
        _fail("Foreign stage, changed role, or broken chain")
    if receipt.get("section_compiled_sha256") != (
        section["compiled_sha256"] if section is not None else None
    ):
        _fail("Stage compiled-curriculum identity diverged")
    try:
        raw = base.with_suffix(".vdk").read_bytes()
        if _digest(raw) != receipt["checkpoint_sha256"]:
            _fail("Checkpoint digest does not match receipt")
        kernel = VerdantKernel.from_state(load_checkpoint_bytes(raw))
        if checkpoint_bytes(kernel.snapshot()) != raw:
            _fail("Checkpoint bytes do not roundtrip")
        if kernel.fingerprint() != receipt["fingerprint"]:
            _fail("Canonical checkpoint fingerprint mismatch")
        if (kernel.state.cycle < expected_cycle or
            (number == 0 and kernel.state.cycle != 0)):
            _fail("Checkpoint engine cycle count is below teaching-experience count")
        for key in expected_keys:
            if key not in kernel.state.processed_event_keys:
                _fail("A declared teaching event is missing")
        if len(kernel.state.processed_event_keys) != expected_cycle:
            _fail("Unexpected or duplicated teaching-event history")
        if _metrics(kernel) != receipt["metrics"]:
            _fail("Checkpoint metrics do not agree with saved receipt")
        if receipt.get("observations") != (
            _inspect(kernel, section) if section is not None else None
        ):
            _fail("Read-only stage inspection differs from checkpoint")
    except (KeyError, ValueError, AttributeError, TypeError) as exc:
        raise StudyIntegrityError("Stage could not be validated") from exc
    return kernel, receipt, _digest(_json(receipt))


def _save_stage(root, kernel, seed, arm, number, predecessor, observation,
                compiled_sha256, thermodynamic_state):
    path = _stage_path(root, seed, arm, number)
    snap = checkpoint_bytes(kernel.snapshot())
    if checkpoint_bytes(VerdantKernel.from_state(load_checkpoint_bytes(snap)).snapshot()) != snap:
        _fail("Native checkpoint serialization is not deterministic")
    receipt = dict(schema=VERSION, seed=seed, arm=arm,
                   section_number=number, predecessor_sha256=predecessor,
                   checkpoint_sha256=_digest(snap), fingerprint=kernel.fingerprint(),
                   metrics=_metrics(kernel), section_compiled_sha256=compiled_sha256,
                   observations=observation, last_thermodynamics=thermodynamic_state)
    # Fail closed if a power loss occurs between the immutable VDK and its receipt.
    _write_new(path.with_suffix(".vdk"), snap)
    _write_new(path.with_suffix(".json"), _json(receipt))
    return _digest(_json(receipt))


def _new_pipeline(arm, kernel, prior):
    if arm == "kernel_only":
        return None
    if arm == "v5":
        return VerdantDevelopmentPipeline()
    pipeline = V5XDevelopmentPipeline(
        enable_access_pressure_observation=True,
        enable_thermodynamic_observation=True,
        enable_thermodynamic_control=False,
    )
    if prior:
        pipeline._last_thermodynamics[kernel.state.identity.kernel_id] = (
            ThermodynamicState.model_validate(prior)
        )
    return pipeline


def _arm(root, seed, arm, sections, state_dim):
    kernel = None
    last_stage = -1
    last_receipt = None
    prior_hash = None
    keys = ()
    cycle = 0
    missing = False
    for number in range(len(sections) + 1):
        if number:
            sec = sections[number - 1]
            keys += tuple(c.event_key for c in sec["commands"])
            cycle += len(sec["commands"])
        base = _stage_path(root, seed, arm, number)
        if base.with_suffix(".vdk").exists() != base.with_suffix(".json").exists():
            _fail("Incomplete committed stage; preserve files for recovery")
        if not base.with_suffix(".vdk").exists():
            missing = True
            continue
        if missing:
            _fail("Future stage exists after missing stage")
        kernel, last_receipt, prior_hash = _load_stage(
            root, seed, arm, number, prior_hash, cycle, keys,
            sections[number - 1] if number else None,
        )
        last_stage = number
    if kernel is None:
        kernel = VerdantKernel(
            seed=seed, state_dim=state_dim, run_label=f"vast-integrated-seed-{seed}"
        )
        prior_hash = _save_stage(root, kernel, seed, arm, 0, None, None, None, None)
        last_stage = 0
        last_receipt = _load_json(_stage_path(root, seed, arm, 0).with_suffix(".json"))
    pipeline = _new_pipeline(arm, kernel, last_receipt.get("last_thermodynamics"))
    for number in range(last_stage + 1, len(sections) + 1):
        section = sections[number - 1]
        for command in section["commands"]:
            before_cycle = kernel.state.cycle
            before_events = len(kernel.state.processed_event_keys)
            if arm == "kernel_only":
                result = kernel.apply_experience(command)
            else:
                result = pipeline.advance(kernel, command)
                if not result.semantic_firewall_held:
                    _fail("Native developmental semantic firewall failed")
                if arm == "v5x_observe" and result.thermodynamic_control is not None:
                    _fail("Behavioral thermodynamic control must remain disabled")
            if (result.replayed or kernel.state.cycle <= before_cycle
                or len(kernel.state.processed_event_keys) != before_events + 1
                or command.event_key not in kernel.state.processed_event_keys):
                _fail(f"Expected fresh charged teaching: arm={arm} event={command.event_key} "
                      f"replayed={result.replayed} before={before_cycle} "
                      f"after={kernel.state.cycle} "
                      f"processed_before={before_events} "
                      f"processed_after={len(kernel.state.processed_event_keys)}")
        observation = _inspect(kernel, section)
        thermo = None
        if arm == "v5x_observe":
            latest = pipeline._last_thermodynamics.get(kernel.state.identity.kernel_id)
            thermo = latest.model_dump(mode="json") if latest is not None else None
        prior_hash = _save_stage(root, kernel, seed, arm, number, prior_hash,
                                 observation, section["compiled_sha256"], thermo)
        print(f"Saved: seed={seed} arm={arm} section={number}/{len(sections)} "
              f"cycle={kernel.state.cycle}", flush=True)
    return dict(seed=seed, arm=arm, sections=len(sections),
                teaching_experiences=len(kernel.state.processed_event_keys),
                native_engine_cycles=kernel.state.cycle, fingerprint=kernel.fingerprint(),
                semantic=dict(
                    concepts=tuple(sorted(kernel.state.concepts)),
                    relations=tuple(sorted(kernel.state.relations)),
                    claims=tuple(sorted(kernel.state.claims)),
                    contradictions=tuple(sorted(kernel.state.contradictions)),
                ),
                final_stage_sha256=prior_hash)


def _run(root):
    manifest = _load_json(root / "manifest.json")
    pack_bytes = (root / "curriculum.vcpack").read_bytes()
    pack, sections = _plan(pack_bytes, len(manifest["section_ids"]))
    expected = _manifest(pack_bytes, sections, tuple(manifest["seeds"]), pack.state_dim)
    if expected != manifest:
        _fail("Curriculum, source code, protocol or manifest changed after freezing")
    result = []
    for seed in manifest["seeds"]:
        by_arm = {}
        for arm in ARMS:
            by_arm[arm] = _arm(root, seed, arm, sections, pack.state_dim)
            result.append(by_arm[arm])
        if by_arm["v5"]["fingerprint"] != by_arm["v5x_observe"]["fingerprint"]:
            _fail("Observer-only V5-X changed canonical developmental state")
        if by_arm["v5"]["semantic"] != by_arm["kernel_only"]["semantic"]:
            _fail("Developmental heartbeat changed canonical semantic identities")
    data = dict(schema=VERSION, manifest_sha256=_digest(_json(manifest)),
                pack_sha256=_digest(pack_bytes), arms=result,
                conclusion="ungraded_staged_developmental_integrity_only")
    path = root / "results.json"
    raw = _json(data)
    if path.exists():
        if path.read_bytes() != raw:
            _fail("Existing final result differs")
    else:
        _write_new(path, raw)
    return path


def start(directory, pack_path, *, limit_sections=1, seeds=DEFAULT_SEEDS):
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=False)
    pack_bytes = Path(pack_path).read_bytes()
    pack, sections = _plan(pack_bytes, limit_sections)
    with _lock(root):
        _write_new(root / "curriculum.vcpack", pack_bytes)
        _write_new(root / "manifest.json",
                   _json(_manifest(pack_bytes, sections, seeds, pack.state_dim)))
        return _run(root)


def resume(directory):
    root = Path(directory)
    if not (root / "manifest.json").exists():
        _fail("No frozen manifest; cannot resume")
    with _lock(root):
        return _run(root)


def status(directory):
    root = Path(directory)
    manifest = _load_json(root / "manifest.json")
    pack_bytes = (root / "curriculum.vcpack").read_bytes()
    pack, sections = _plan(pack_bytes, len(manifest["section_ids"]))
    if manifest != _manifest(pack_bytes, sections, tuple(manifest["seeds"]), pack.state_dim):
        _fail("Frozen source or curriculum changed")
    with _lock(root):
        for seed in manifest["seeds"]:
            for arm in ARMS:
                previous, keys, cycle, last = None, (), 0, None
                for number in range(len(sections) + 1):
                    if number:
                        s = sections[number - 1]
                        keys += tuple(x.event_key for x in s["commands"])
                        cycle += len(s["commands"])
                    base = _stage_path(root, seed, arm, number)
                    if base.with_suffix(".vdk").exists() != base.with_suffix(".json").exists():
                        _fail("Incomplete stage pair")
                    if not base.with_suffix(".vdk").exists():
                        if any(_stage_path(root, seed, arm, later).with_suffix(".vdk").exists()
                               for later in range(number + 1, len(sections) + 1)):
                            _fail("Stage lineage contains a gap")
                        break
                    _, _, previous = _load_stage(root, seed, arm, number,
                                                 previous, cycle, keys,
                                                 sections[number - 1] if number else None)
                    last = number
                print(f"seed={seed} arm={arm} durable_section={last}/{len(sections)}")
        print(f"complete_result={ (root / 'results.json').exists() }")



def preview(pack_path, *, limit_sections=1):
    """Read-only preview; does not create an organism or change the pack."""
    raw = Path(pack_path).read_bytes()
    pack, selected = _plan(raw, limit_sections)
    print("Pack:", pack.title)
    print("Pack SHA-256:", _digest(raw))
    print("Field dimension:", pack.state_dim)
    print("Selected sections:", len(selected),
          "Teaching experiences:", sum(len(s["commands"]) for s in selected),
          "Diagnostic probes:", sum(len(s["tests"]) for s in selected))
    for index, section in enumerate(selected, 1):
        print(index, section["id"],
              "experiences", len(section["commands"]),
              "diagnostics", len(section["tests"]),
              "compiler_warnings", len(section["warnings"]))


def report(directory):
    """Validate recorded sections; report measured counts, not fabricated scores."""
    root = Path(directory)
    status(root)
    if not (root / "results.json").is_file():
        _fail("No complete results batch; reporting cannot finish a run")
    result = _load_json(root / "results.json")
    manifest = _load_json(root / "manifest.json")
    if result["manifest_sha256"] != _digest(_json(manifest)):
        _fail("Results do not bind the immutable manifest")
    print("seed arm experiences native_cycles concepts relations claims "
          "plasticity P_candidates P_structures Q_structures "
          "dependency_gaps contradictions")
    for entry in result["arms"]:
        stage = _load_json(_stage_path(
            root, entry["seed"], entry["arm"], entry["sections"]
        ).with_suffix(".json"))
        m = stage["metrics"]
        obs = stage["observations"]
        if (entry["fingerprint"] != stage["fingerprint"] or
            entry["native_engine_cycles"] != m["cycle"] or
            entry["teaching_experiences"] !=
            sum(x["commands"] for x in manifest["sections"])):
            _fail("Reported arm summary diverges from staged native history")
        print(entry["seed"], entry["arm"], entry["teaching_experiences"],
              m["cycle"], m["concepts"], m["relations"], m["claims"],
              m["plasticity_associations"], m["structure_candidates"],
              m["structures"], m["layered_structures"],
              obs["dependency_gap_candidates"], obs["contradiction_candidates"])
    print("DIAGNOSTICS ARE NOT GRADES. Obligation findings are read-only.")
    return root / "results.json"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    peek = sub.add_parser("preview")
    peek.add_argument("curriculum")
    peek.add_argument("--sections", type=int, default=1)
    new = sub.add_parser("start")
    new.add_argument("directory")
    new.add_argument("curriculum")
    new.add_argument("--sections", type=int, default=1)
    new.add_argument("--seeds", type=int, nargs="+", default=list(DEFAULT_SEEDS))
    for action in ("resume", "status", "report"):
        sub.add_parser(action).add_argument("directory")
    args = parser.parse_args(argv)
    if args.action == "preview":
        preview(args.curriculum, limit_sections=args.sections)
    elif args.action == "start":
        result = start(args.directory, args.curriculum,
                       limit_sections=args.sections, seeds=tuple(args.seeds))
        print(result)
    elif args.action == "resume":
        print(resume(args.directory))
    elif args.action == "report":
        print(report(args.directory))
    else:
        status(args.directory)


if __name__ == "__main__":
    main()
