# Windows handoff: Structural Relation Lens v0.1

This is a NEW read-only research branch, NOT an upgrade to your working VAST-AutoPQ or Q-Subfamilies checkout. Preserve all existing native checkpoints and old study code.

## 1. Clone experimental repository to a new folder

Paste into PowerShell:

~~~powershell
$Work = "$env:USERPROFILE\Verdant-Relation-Lens-Test"
if (Test-Path $Work) { throw "Destination already exists; do not overwrite." }

git clone --branch test/structural-relation-lens-v0 --single-branch https://github.com/Captainkoopa42/Verdant-Minds.git "$Work"
if ($LASTEXITCODE -ne 0) { throw "Clone failed." }

Set-Location $Work

py -3.11 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Python 3.11 venv creation failed." }

$Py = ".\.venv\Scripts\python.exe"

& $Py -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw "Locked dependency installation failed." }

& $Py -m pytest -q tests/test_structural_relation_lens.py tests/test_structure_interaction_phase.py tests/test_hierarchy_phase.py tests/test_q_subfamilies.py tests/test_vast_integrated.py
if ($LASTEXITCODE -ne 0) { throw "Synthetic native P/Q controls FAILED; preserve logs and STOP." }

git rev-parse --short HEAD
~~~

These are small SYNTHETIC matched cases: no user curriculum, no 600-item training, no automatic native promotion outside the isolated test fixture. GitHub Actions workflow is intentionally manual-only after validation.

## 2. Examine your EXISTING 60-experience, 12-P/2-Q checkpoint (no rerun)

~~~powershell
Set-Location "$env:USERPROFILE\Verdant-Relation-Lens-Test"
$Py = ".\.venv\Scripts\python.exe"
$Checkpoint = "$env:USERPROFILE\Verdant-Vast-AutoPQ-Test\vast-auto-pq-three-sections\stages\seed-81001\v5x_auto_pq\003.vdk"
if (-not (Test-Path $Checkpoint)) { throw "Original experimental VDK not found; stop." }

$Path = Join-Path (Get-Location).Path "relation-lens-audit-12p.json"
if (Test-Path $Path) { throw "The audit output already exists; preserve it." }

& $Py -m verdant_integrated.structural_lens_audit $Checkpoint --max-pairs 66 |
    Tee-Object -FilePath $Path

if ($LASTEXITCODE -ne 0) { throw "Audit command failed; do not interpret output." }

Write-Host "Read-only diagnostic copy:" $Path
~~~

This writes a NEW JSON audit REPORT only. It never modifies the original native checkpoint or creates/promotes P/Q.

For a faster first pass, change --max-pairs 66 to --max-pairs 12 and choose a distinct new report filename. Pair order is deterministic sorted P-ID order, not a random sample; do not infer population rates from a prefix subset.

Inspect these JSON sections:
- pair_counts: native_topology_accept, typed_accept, typed_reject, typed_abstain, baseline_positive_typed_negative.
- pair_details: exact P identities, baseline scores, typed F1, provenance gaps and reasons.
- native_retrospective_q_work: native Q compared with full native baseline via read-only layered probe. The baseline includes all CURRENT P structures and some Qs that may have formed later; this is NOT a prospective time-isolated test.

### Safety and interpretation

The lens preserves the native P/Q pipeline exactly as it was. It compares *current checkpoint ledger* relations tied to native P member_relation_ids, not frozen verified physical relations at promotion time. It is strict about exact human-supplied relation names and directions; it knows no synonyms or causal equivalence.

Native Q still uses topology only. The read-only lens DOES NOT automatically repair a bad Q, authorize a new Q, or demonstrate independent semantic understanding. The synthetic test cases measure the difference between two explicit matching procedures with experimenter-specified positive and negative labels.

Do not run the 10- or 30-section user VCpack on this branch just to count Qs; read the existing audit first. Any eventual integration of relation-aware nomination must be a new, explicitly approved, source-locked experimental arm with separate controls and native Council safeguards.

Research specification: docs/STRUCTURAL_RELATION_LENS_EXPERIMENT.md.
