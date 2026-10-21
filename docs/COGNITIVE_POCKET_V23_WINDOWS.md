# Cognitive Pocket v2.3 — Windows runbook

This is a separate research checkout. Do not merge it into main or switch an existing experiment checkout. The v2.2 branch and native VDK remain unchanged.

## 1. Clone and install

~~~powershell
$Work = "$env:USERPROFILE\Verdant-Pocket-Corroboration-V23"
if (Test-Path $Work) { throw "Folder already exists; stop to preserve it." }
git clone --branch test/cognitive-pocket-corroboration-v2-3 --single-branch https://github.com/Captainkoopa42/Verdant-Minds.git $Work
if ($LASTEXITCODE -ne 0) { throw "Clone failed." }
Set-Location $Work
py -3.11 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Virtual environment failed." }
$Py = ".\.venv\Scripts\python.exe"
& $Py -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency install failed." }
~~~

## 2. Run focused regression

~~~powershell
& $Py -m pytest -q tests/test_cognitive_pocket_corroboration.py tests/test_cognitive_pocket_reconciliation.py tests/test_cognitive_pocket_evidence_retention.py tests/test_cognitive_pocket_composition.py tests/test_cognitive_pocket_curriculum.py tests/test_cognitive_pocket_cultivation.py tests/test_cognitive_pocket_lifecycle.py tests/test_cognitive_pocket_integration.py tests/test_hierarchy_phase.py tests/test_structure_interaction_phase.py tests/test_obligation_substrate.py tests/test_counterfactual_runtime.py
if ($LASTEXITCODE -ne 0) { throw "Tests failed; stop." }
~~~

## 3. Generate a report without touching native memory

~~~powershell
$Folder = Join-Path (Get-Location).Path ("corroboration-v23-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Path $Folder -ErrorAction Stop | Out-Null
$Report = Join-Path $Folder "corroboration-scaling.json"
& $Py -m verdant_pockets.corroboration_cli --out $Report --sizes 32,64,128,256 --irrelevant-per-node 4
if ($LASTEXITCODE -ne 0) { throw "Research report generation failed." }
Get-Content $Report
Invoke-Item $Folder
~~~

## 4. Optional custom observations

Prepare a separate JSON file containing a list of observation objects. Every object must have these nonempty string fields: observation_id, source_ref, source_family, source_record_id, subject, predicate, object, direction.

~~~powershell
& $Py -m verdant_pockets.corroboration_cli --observations "$env:USERPROFILE\Desktop\my-observations.json" --out (Join-Path $Folder "custom-observations.json") --sizes 32,64,128,256
if ($LASTEXITCODE -ne 0) { throw "Custom assessment failed." }
~~~

This only assesses declared provenance. It does not import claims into native Verdant memory or verify source authenticity.

## 5. Send results back

Upload corroboration-scaling.json and the test output. We will check claim-level source-family counts, reverse conflicts, edge-inspection growth, and equivalence of both graph baselines. The benchmark is synthetic; it cannot by itself establish an efficiency advantage for cognitive pockets.
