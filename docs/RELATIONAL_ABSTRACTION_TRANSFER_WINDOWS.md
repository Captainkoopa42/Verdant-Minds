# Windows: Relational Abstraction and Q Transfer v0

This is an isolated TEST branch. It does not replace the working Auto-PQ, Q-subfamily or relation-lens checkouts and must NOT be used to resume older source-frozen VAST experiment directories. Checkpoints stay in the old directory, untouched.

## One-time clone/install and focused test

Open PowerShell and paste the entire block:

~~~powershell
$Work = "$env:USERPROFILE\Verdant-Relational-Transfer-Test"

if (Test-Path $Work) { throw "Experiment folder already exists. Preserve it." }
git clone --branch test/relational-abstraction-transfer-v0 --single-branch https://github.com/Captainkoopa42/Verdant-Minds.git "$Work"
if ($LASTEXITCODE -ne 0) { throw "Clone failed." }

Set-Location $Work
py -3.11 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Python 3.11 virtual environment failed." }
$Py = ".\.venv\Scripts\python.exe"
& $Py -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

& $Py -m pytest -q tests/test_relational_abstraction_transfer.py tests/test_structural_relation_lens.py tests/test_structure_interaction_phase.py tests/test_hierarchy_phase.py tests/test_q_subfamilies.py tests/test_vast_integrated.py
if ($LASTEXITCODE -ne 0) { throw "Focused native test suite failed. STOP." }

git branch --show-current
git rev-parse --short HEAD
~~~

No user curriculum is run by this script. The tests create short-lived, synthetic native kernels with actual P/Q Council promotion on disposable test fixtures.

## Run read-only audit against YOUR completed 12-P / 2-Q Section 3

~~~powershell
Set-Location "$env:USERPROFILE\Verdant-Relational-Transfer-Test"
$Py = ".\.venv\Scripts\python.exe"
$Original = "$env:USERPROFILE\Verdant-Vast-AutoPQ-Test\vast-auto-pq-three-sections\stages\seed-81001\v5x_auto_pq\003.vdk"
if (-not (Test-Path $Original)) { throw "Historical checkpoint not found." }

$Output = Join-Path (Get-Location).Path "relational-transfer-12p-audit.json"
if (Test-Path $Output) { throw "Read-only audit output already exists. Preserve it." }

& $Py -m verdant_integrated.relational_transfer_audit $Original --max-queries 12 |
    Tee-Object -FilePath $Output
if ($LASTEXITCODE -ne 0) { throw "Audit failed; do NOT trust incomplete output." }

Write-Host "New audit report saved to:" $Output
~~~

The report file is an OPTIONAL NEW output file in the NEW experiment directory, never an overwrite of the original .vdk. The tool checks both checkpoint bytes and native kernel fingerprint remain identical.

### Reading the report

- all_query_verdicts_preserved: must be true. If false, treat as a regression and stop.
- exact_typed_matches: count of exact type-and-direction P matches on the CURRENT final checkpoint, not independent semantic truth.
- exhaustive_exact_verifications: exact typed P comparisons on the reference exhaustive path.
- p_keyed_exact_verifications and q_overlay_exact_verifications: heavyweight verifications not skipped unless a strict role key can safely rule out a pair.
- p_keyed_key_comparisons: one typed-role key check per P in the P-only INDEX control.
- q_overlay_key_comparisons: one key check per native Q subgroup, plus uncovered Ps.
- native_q_older_than_query: number of existing Qs that predate the P. This is contextual only; the audit DOES NOT restrict itself to those historical Qs. Do not count a later Q as a prospective Q-recognition success.
- construction_role_keys: how many role keys are rebuilt for this diagnostic query. This computational work IS NOT free or amortized here, so lower lookup key comparisons cannot be called a wall-clock speedup.

A native Q consisting of dissimilar typed relation patterns may produce as many separate role subgroups as member Ps. In that case the Q overlay may show zero or negative indexing benefit; this is an evidence-driven negative result, NOT license to force synonyms.

The canonical typed-role equivalence rule is deliberately exact F1=1.0. No human-taught relation strings are silently declared synonymous or interchangeable. The OLD native P/Q governance and structure similarity remain untouched, and no training is performed.
