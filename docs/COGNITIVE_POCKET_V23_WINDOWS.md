# Windows — Cognitive Pocket v2.3 Source Corroboration

Fresh isolated project folder, read-only import from your actual completed v2.2 journal. Does NOT edit any earlier Verdant versions or native VDKs. There is no automatic seed run or background learning.

## Step 1 — Clone the isolated branch and run tests

In PowerShell:

~~~powershell
$Work = "$env:USERPROFILE\Verdant-Pocket-Corroboration-V23"
$Branch = "test/cognitive-pocket-source-corroboration-v2-3"

if (Test-Path $Work) {
    throw "v2.3 folder already exists; preserve it and STOP."
}

git clone --branch $Branch --single-branch https://github.com/Captainkoopa42/Verdant-Minds.git "$Work"
if ($LASTEXITCODE -ne 0) { throw "Git clone failed." }

Set-Location $Work
py -3.11 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Python virtual environment failed." }

$Py = ".\.venv\Scripts\python.exe"
& $Py -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency install failed." }

& $Py -m pytest -q tests/test_cognitive_pocket_corroboration.py tests/test_cognitive_pocket_reconciliation.py tests/test_cognitive_pocket_evidence_retention.py tests/test_cognitive_pocket_composition.py tests/test_cognitive_pocket_curriculum.py tests/test_cognitive_pocket_cultivation.py tests/test_cognitive_pocket_lifecycle.py tests/test_cognitive_pocket_integration.py tests/test_hierarchy_phase.py tests/test_structure_interaction_phase.py tests/test_obligation_substrate.py tests/test_counterfactual_runtime.py
if ($LASTEXITCODE -ne 0) { throw "Focused native tests FAILED; stop here." }

git branch --show-current
git rev-parse --short HEAD
~~~

## Step 2 — Import your real v2.2 experimental journal without modifying it

The previous local run reported the original path:

C:\Users\Owner\Verdant-Pocket-Reconciliation-V22\revision-v22-20261015-121415\retained-revision.vpr.json

Copy/paste:

~~~powershell
Set-Location "$env:USERPROFILE\Verdant-Pocket-Corroboration-V23"
$Py = ".\.venv\Scripts\python.exe"

$OriginalJournal = "$env:USERPROFILE\Verdant-Pocket-Reconciliation-V22\revision-v22-20261015-121415\retained-revision.vpr.json"
if (-not (Test-Path $OriginalJournal)) { throw "Original v2.2 revision journal missing; STOP." }
$OldBefore = (Get-FileHash $OriginalJournal -Algorithm SHA256).Hash

$Folder = Join-Path (Get-Location).Path ("corroboration-v23-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Path $Folder -ErrorAction Stop | Out-Null
$Report = Join-Path $Folder "controlled-corroboration.json"
$Journal = Join-Path $Folder "retained-provenance.vpc.json"

& $Py -m verdant_pockets.research_corroboration_demo --from-v22 $OriginalJournal --out $Report --journal $Journal
if ($LASTEXITCODE -ne 0) { throw "v2.3 provenance study failed; STOP." }

$OldAfter = (Get-FileHash $OriginalJournal -Algorithm SHA256).Hash
if ($OldBefore -ne $OldAfter) { throw "Your earlier v2.2 journal changed unexpectedly! STOP." }

Write-Host "Original v2.2 journal unchanged: True"
Write-Host "New v2.3 results:" $Folder
~~~

The new experiment imports the old six-stage journal, explicitly maps each old declared source to a lineage family, and tests:
- Single-family evidence: provisional, not accepted as a corroborated bridge.
- A copied citation with a new publisher: still provisional (inherits its original family).
- A second declared family: conditional composition supported.
- A contradictory reverse observation: quarantined.
- Withdrawal of the challenger: conditional support resumes.
- Withdrawal of the second family: provisional again.
- New separate family: conditional support resumes.

The benchmark also adds 0, 8, 16, 32 and 64 *well-formed but uncorroborated* distractor observations to a fixed 3-P native baseline, comparing identical eligible evidence in the pocket and flat graph. These are not new independently verified sensor observations.

## Step 3 — Verify the independently saved journal in a new process

~~~powershell
& $Py -m verdant_pockets.research_corroboration_demo --verify $Journal
if ($LASTEXITCODE -ne 0) { throw "Fresh-source replay verification failed." }

Write-Host "Original v2.2 journal remained byte-identical: True"
Write-Host "Ready for review:" $Folder
Invoke-Item $Folder
~~~

## Share results

Upload controlled-corroboration.json and retained-provenance.vpc.json plus the console output.

Scientific guardrail: In this study 'two independent families' means **two distinct externally declared ancestry groups** in the controlled input. There are no authenticated real-world identities or sensor provenance. The manifest and SHA hashes only preserve structured record consistency. No canonical facts are created, and no pocket-versus-flat computational advantage is assumed.
