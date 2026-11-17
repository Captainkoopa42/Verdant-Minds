"""Bond clock and changes-only plasticity records, as an opt-in layer outside every pinned file.

Claim boundary: IMPLEMENTED-EXPERIMENTAL. No file under ``verdant_*`` is edited, so the frozen
math line's code manifests and the Workbench engine identity are untouched. Three engine methods
are wrapped (each derived from its stock source with one passage replaced, refused if the stock
source ever changes): ``VerdantPlasticityPipeline.inspect``, ``VerdantKernel.validate_plasticity_report``
and ``VerdantKernel.commit_plasticity_report``. Stock reports pass through the stock code unchanged.

Why: every beat faded every bond, so every plasticity event stored the whole bond table. In a
406-lesson life 97.6% of 74,588 stored bond records differed from the previous beat only by
that fading. History grew with lessons x bonds.

Changes-only record (``ChangesOnlyPlasticityPipeline``)
    The beat is computed exactly as before. The report then stores, in ``proposed_associations``,
    only bonds that changed for a reason other than fading, and in ``decayed_association_ids``
    exactly the bonds whose next record is the fade rule applied to the prior one. Every other
    prior bond that is not pruned carries over unchanged. The report names itself in its
    ``operation`` string, including its fade rule, so the kernel and any replay rebuild the
    table from the record alone:  bounded_local_plasticity|record=changes_only|fade={...}|suspended=0

Fade rules
    uniform     strength * (1 - decay_rate)                                  (stock)
    bond_clock  decay_rate / real exposures (OBSERVATION evidence, capped at 5); a bond met at
                least 3 times does not fade below 0.10; a bond met once fades exactly as stock.
                A rehearsal beat applies no time fade (sleep does not age the rest of memory).
"""
from __future__ import annotations

import hashlib
import inspect
import json
import textwrap
from typing import Any

import verdant_kernel.kernel as _kernel_module
import verdant_plasticity.pipeline as _pipeline_module
from verdant_kernel import VerdantKernel
from verdant_kernel.models import EvidenceKind
from verdant_plasticity import VerdantPlasticityPipeline

__all__ = ["ChangesOnlyPlasticityPipeline", "BondClockPlasticityPipeline", "install_changes_only", "changes_only_installed",
           "table_from_report", "replay_tables", "is_changes_only", "UNIFORM", "BOND_CLOCK"]

STOCK_INSPECT_SHA256 = "64a013f16ea2791d1ab040ff9bbffb20a2869530701ba95e0c3a4006f155d824"
STOCK_VALIDATE_SHA256 = "46cc5ddef4d23d371293527e9e4e6288bad9316939cda3713c465110dc320d91"
STOCK_COMMIT_SHA256 = "37ee6e81709534a13671383ac94b551fbde0f0f55a0a2bbf17821d4d47373a79"
MARK = "|record=changes_only|"
UNIFORM = {"decay_mode": "uniform"}
BOND_CLOCK = {"decay_mode": "bond_clock", "durability_cap": 5, "floor_after": 3, "floor": 0.10}


# ---- the record format -------------------------------------------------------------------
def encode_operation(base: str, rule: dict[str, Any], suspended: bool) -> str:
    return f"{base}{MARK}fade={json.dumps(rule, sort_keys=True, separators=(',', ':'))}|suspended={int(suspended)}"


def is_changes_only(report) -> bool:
    return MARK in report.operation


def decode_operation(operation: str) -> tuple[dict[str, Any], bool]:
    tail = operation.split(MARK, 1)[1]
    fade_part, suspended_part = tail.rsplit("|suspended=", 1)
    return json.loads(fade_part[len("fade="):]), suspended_part == "1"


def fade(kernel, record, rule: dict[str, Any], decay_rate: float, *, cycle: int, workspace_event_id: str, suspended: bool):
    """One un-reinforced bond, one beat older."""
    if suspended:
        strength = record.strength
    elif rule["decay_mode"] == "uniform":
        strength = record.strength * (1.0 - decay_rate)
    else:
        exposures = sum(1 for ref in record.evidence_refs
                        if ref in kernel.state.evidence and kernel.state.evidence[ref].kind == EvidenceKind.OBSERVATION)
        rate = decay_rate / max(1, min(rule["durability_cap"], exposures))
        floor = min(record.strength, rule["floor"]) if exposures >= rule["floor_after"] else 0.0
        strength = max(record.strength * (1.0 - rate), floor)
    return record.model_copy(update={"strength": strength, "updated_cycle": cycle, "last_workspace_event_id": workspace_event_id})


def table_from_report(kernel, report, prior: dict) -> dict:
    """The bond table a report leaves behind, given the table it was computed against."""
    if not is_changes_only(report):
        return {item.association_id: item for item in report.proposed_associations}
    rule, suspended = decode_operation(report.operation)
    changed = {item.association_id: item for item in report.proposed_associations}
    pruned = set(report.pruned_association_ids)
    integrity = _kernel_module.PlasticityIntegrityError
    if len(changed) != len(report.proposed_associations):
        raise integrity("Plasticity report contains duplicate associations.")
    if not set(report.decayed_association_ids) <= set(prior) or not pruned <= set(prior):
        raise integrity("Changes-only plasticity report fades or prunes unknown associations.")
    if set(report.decayed_association_ids) & (set(changed) | pruned) or pruned & set(changed):
        raise integrity("Changes-only plasticity report names an association twice.")
    table = {key: value for key, value in prior.items() if key not in pruned}
    for association_id in report.decayed_association_ids:
        table[association_id] = fade(kernel, prior[association_id], rule, rule["decay_rate"], cycle=report.cycle + 1,
                                     workspace_event_id=report.workspace_event_id, suspended=suspended)
    table.update(changed)
    return dict(sorted(table.items()))


def replay_tables(kernel):
    """Replay plasticity history: yields (event, bond table after that event)."""
    table: dict = {}
    for event in kernel.state.plasticity_events:
        table = table_from_report(kernel, event.report, table)
        yield event, table


# ---- deriving the three wrapped methods from stock source ---------------------------------
def _derive(owner, name: str, digest: str, replacements: list[tuple[str, str]], namespace: dict) -> Any:
    source = inspect.getsource(getattr(owner, name))
    if hashlib.sha256(source.encode()).hexdigest() != digest:
        raise RuntimeError(f"Stock {owner.__name__}.{name} changed; sidecar_bond_clock must be re-derived.")
    for old, new in replacements:
        if source.count(old) != 1:
            raise RuntimeError(f"Expected passage not found exactly once in {owner.__name__}.{name}.")
        source = source.replace(old, new)
    scope = dict(namespace)
    exec(compile(textwrap.dedent(source), f"<sidecar_bond_clock derived {name}>", "exec"), scope)
    return scope[name]


_TABLE_FROM_STOCK = '''        proposed = {item.association_id: item for item in report.proposed_associations}
        if len(proposed) != len(report.proposed_associations):
            raise PlasticityIntegrityError("Plasticity report contains duplicate associations.")
'''
_COMMIT_FROM_STOCK = '''        self.state.plasticity_associations = {
            item.association_id: item for item in report.proposed_associations
        }
'''
_DECAY_FROM_STOCK = '''            strength = record.strength * (1.0 - policy.decay_rate)
            next_associations[association_id] = record.model_copy(
                update={
                    "strength": strength,
                    "updated_cycle": prospective_cycle,
                    "last_workspace_event_id": workspace_event.event_id,
                }
            )
'''
_REPORT_FROM_STOCK = '''        proposed = tuple(next_associations[key] for key in sorted(next_associations))
        degree = self._degree_map(next_associations)
        max_degree_after = max(degree.values(), default=0)
        edge_ratio_after = len(proposed) / max(1, len(kernel.state.concepts))
        operation = "bounded_local_plasticity"
'''
_ORIGINAL: dict[str, Any] = {}


def install_changes_only() -> None:
    """Teach the kernel to check and commit changes-only reports. Stock reports are unaffected."""
    if _ORIGINAL:
        return
    namespace = {**vars(_kernel_module), "_bond_clock_table": table_from_report}
    validate = _derive(VerdantKernel, "validate_plasticity_report", STOCK_VALIDATE_SHA256, [(
        _TABLE_FROM_STOCK,
        "        proposed = _bond_clock_table(self, report, self.state.plasticity_associations)\n")], namespace)
    commit = _derive(VerdantKernel, "commit_plasticity_report", STOCK_COMMIT_SHA256, [(
        _COMMIT_FROM_STOCK,
        "        self.state.plasticity_associations = _bond_clock_table(self, report, self.state.plasticity_associations)\n")], namespace)
    _ORIGINAL["validate_plasticity_report"] = VerdantKernel.__dict__["validate_plasticity_report"]
    _ORIGINAL["commit_plasticity_report"] = VerdantKernel.__dict__["commit_plasticity_report"]
    VerdantKernel.validate_plasticity_report = validate
    VerdantKernel.commit_plasticity_report = commit


def uninstall_changes_only() -> None:
    for name, original in list(_ORIGINAL.items()):
        setattr(VerdantKernel, name, original)
    _ORIGINAL.clear()


def changes_only_installed() -> bool:
    return bool(_ORIGINAL)


_INSPECT: dict[str, Any] = {}


def _derived_inspect():
    if "inspect" not in _INSPECT:
        namespace = {**vars(_pipeline_module), "_bond_clock_fade": fade, "_bond_clock_encode": encode_operation}
        _INSPECT["inspect"] = _derive(VerdantPlasticityPipeline, "inspect", STOCK_INSPECT_SHA256, [
            (_DECAY_FROM_STOCK, '''            next_associations[association_id] = _bond_clock_fade(
                kernel, record, self.fade_rule, policy.decay_rate, cycle=prospective_cycle,
                workspace_event_id=workspace_event.event_id, suspended=self._fade_suspended(kernel, workspace_event))
'''),
            (_REPORT_FROM_STOCK, '''        full_table = tuple(next_associations[key] for key in sorted(next_associations))
        degree = self._degree_map(next_associations)
        max_degree_after = max(degree.values(), default=0)
        edge_ratio_after = len(full_table) / max(1, len(kernel.state.concepts))
        operation = "bounded_local_plasticity"
        proposed = full_table
        if self.changes_only:
            suspended = self._fade_suspended(kernel, workspace_event)
            rule = {**self.fade_rule, "decay_rate": policy.decay_rate}
            faded = tuple(
                key for key in sorted(set(before) & set(next_associations))
                if next_associations[key] == _bond_clock_fade(
                    kernel, before[key], rule, policy.decay_rate, cycle=prospective_cycle,
                    workspace_event_id=workspace_event.event_id, suspended=suspended))
            faded_set = set(faded)
            proposed = tuple(r for r in full_table if r.association_id not in faded_set and r != before.get(r.association_id))
            assessments = [a for a in assessments
                           if not (a.disposition == PlasticityUpdateKind.DECAY and a.association_id in faded_set)]
            decayed = faded
            operation = _bond_clock_encode(operation, rule, suspended)
'''),
            ("            len(proposed),\n            max_degree_after,", "            len(full_table),\n            max_degree_after,"),
            ("            edge_count_after=len(proposed),", "            edge_count_after=len(full_table),"),
        ], namespace)
    return _INSPECT["inspect"]


class ChangesOnlyPlasticityPipeline(VerdantPlasticityPipeline):
    """Plasticity whose events record only real change. ``fade_rule`` is UNIFORM (stock fading)
    or BOND_CLOCK; ``changes_only=False`` records the whole table, for comparison."""

    fade_rule: dict[str, Any] = UNIFORM

    def __init__(self, *, changes_only: bool = True, fade_rule: dict[str, Any] | None = None) -> None:
        super().__init__()
        self.changes_only = changes_only
        if fade_rule is not None:
            self.fade_rule = dict(fade_rule)
        install_changes_only()

    def _fade_suspended(self, kernel, workspace_event) -> bool:
        if self.fade_rule.get("decay_mode") != "bond_clock":
            return False
        items = kernel.state.workspace_items
        return any(items[i].metadata.get("developmental_stage") == "sidecar_rehearsal"
                   for i in workspace_event.active_item_ids if i in items)

    def inspect(self, *args, **kwargs):
        return _derived_inspect()(self, *args, **kwargs)


class BondClockPlasticityPipeline(ChangesOnlyPlasticityPipeline):
    """The bond clock, recorded changes-only (the arms used across this week's experiments)."""

    fade_rule = BOND_CLOCK
