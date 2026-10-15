# Cognitive Pocket v2.2 — Windows evidence revision experiment

Research branch: test/cognitive-pocket-evidence-reconciliation-v2-2.

The original 336-cycle user VDK, previous v2.1 checkout and v2.1 observation sidecar MUST remain unchanged. This v2.2 run uses a NEW isolated native experimental clone, can import the existing v2.1 sidecar read-only, and writes entirely separate v2.2 sidecar and report.

## Step 1 — Create isolated checkout and run regression

PowerShell:

~~~powershell
$Work = "$env:USERPROFILE\Verdant-Pocket-Reconciliation-V22"
$Branch = "test/cognitive-pocket-evidence-reconciliation-v2-2"

if (Test-Path $Work) {
    throw "Research folder already exists. STOP without modifying it."
}

git clone --branch $Branch --single-branch https://github.com/Captainkoopa42/Verdant-Minds.git "$Work"
if ($LASTEXITCODE -ne 0) { throw "Clone failed." }
Set-Location $Work

py -3.11 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Python 3.11 virtual environment failed." }
$Py = ".\.venv\Scripts\python.exe"
& $Py -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw "Pinned dependency install failed." }

& $Py -m pytest -q tests/test_cognitive_pocket_reconciliation.py tests/test_cognitive_pocket_evidence_retention.py tests/test_cognitive_pocket_composition.py tests/test_cognitive_pocket_curriculum.py tests/test_cognitive_pocket_cultivation.py tests/test_cognitive_pocket_lifecycle.py tests/test_cognitive_pocket_integration.py tests/test_hierarchy_phase.py tests/test_structure_interaction_phase.py tests/test_obligation_substrate.py tests/test_counterfactual_runtime.py
if ($LASTEXITCODE -ne 0) { throw "Focused native tests failed. STOP." }

git branch --show-current
git rev-parse --short HEAD
~~~

## Step 2 — Migrate your actual v2.1 evidence sidecar (read-only)

The previous result should still be at this path, from the last experiment:

C:\Users\Owner\Verdant-Pocket-Evidence-V21\evidence-v21-20261015-115658\retained-evidence.vpel.json

Run:

~~~powershell
Set-Location "$env:USERPROFILE\Verdant-Pocket-Reconciliation-V22"
$Py = ".\.venv\Scripts\python.exe"

$Old = "$env:USERPROFILE\Verdant-Pocket-Evidence-V21\evidence-v21-20261015-115658\retained-evidence.vpel.json"
if (-not (Test-Path $Old)) { throw "Old v2.1 sidecar not found. STOP." }
$OldHash = (Get-FileHash $Old -Algorithm SHA256).Hash

$Folder = Join-Path (Get-Location).Path ("revision-v22-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Path $Folder -ErrorAction Stop | Out-Null
$Report = Join-Path $Folder "controlled-reconciliation.json"
$New = Join-Path $Folder "retained-revision.vpr.json"

& $Py -m verdant_pockets.research_reconciliation_demo --from-v21 $Old --out $Report --journal $New
if ($LASTEXITCODE -ne 0) { throw "Revision experiment failed. STOP." }

$OldAfter = (Get-FileHash $Old -Algorithm SHA256).Hash
if ($OldHash -ne $OldAfter) { throw "Original v2.1 journal unexpectedly changed. STOP." }

Write-Host "Prior v2.1 sidecar remains byte-identical: True"
Write-Host "New independent v2.2 journal:" $New
~~~

If you cannot find the old journal, the command may be run without --from-v21; this instead creates the same teacher-staged observation from scratch in a disposable controlled kernel. Do NOT overwrite an occupied output.

## Step 3 — Start a FRESH Python process and replay the retained revised state

~~~powershell
& $Py -m verdant_pockets.research_reconciliation_demo --verify $New
if ($LASTEXITCODE -ne 0) { throw "Restart replay verification failed." }
Write-Host "Completed controlled revision run:" $Folder
Invoke-Item $Folder
~~~

The primary report should show this sequence:

- supported_experimental_composition
- suspended_contested_evidence
- suspended_contested_evidence
- supported_experimental_composition
- suspended_withdrawn_evidence
- supported_experimental_composition

The flat-graph baseline should agree on the underlying eligibility-conditioned result. No native VDK or canonical obligation is modified.

## Send back for scientific interpretation

Upload controlled-reconciliation.json and retained-revision.vpr.json alongside any PowerShell errors. We will inspect how exactly the external observation statuses changed and whether the journal's retained proof dependencies are correct.

This experiment uses controlled, source-*declared* testimony, not authenticated or independently verified sensory observations. A matching hash chain detects unexpected corruption, not malicious resubmission. A restored composition still depends on externally supplied transitivity; it is not proof of autonomously learned cognition or pocket superiority over a flat graph.
