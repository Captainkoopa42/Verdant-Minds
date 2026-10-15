# Windows PowerShell — Cognitive Pocket v2.1 Evidence Acquisition and Retention

This is a fresh, isolated experiment. It does **not** edit the previous v2 directory or the original Verdant VDK.

## Step 1 — Clone in a new folder and validate

Paste in Windows PowerShell:

~~~powershell
$Work = "$env:USERPROFILE\Verdant-Pocket-Evidence-V21"
$Branch = "test/cognitive-pocket-evidence-retention-v2-1"

if (Test-Path $Work) {
    throw "Folder already exists. Preserve it and STOP."
}

git clone --branch $Branch --single-branch https://github.com/Captainkoopa42/Verdant-Minds.git "$Work"
if ($LASTEXITCODE -ne 0) { throw "Clone failed." }

Set-Location $Work
py -3.11 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Python 3.11 environment setup failed." }

$Py = ".\.venv\Scripts\python.exe"
& $Py -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw "Locked dependency install failed." }

& $Py -m pytest -q tests/test_cognitive_pocket_evidence_retention.py tests/test_cognitive_pocket_composition.py tests/test_cognitive_pocket_curriculum.py tests/test_cognitive_pocket_cultivation.py tests/test_cognitive_pocket_lifecycle.py tests/test_cognitive_pocket_integration.py tests/test_hierarchy_phase.py tests/test_structure_interaction_phase.py tests/test_obligation_substrate.py tests/test_counterfactual_runtime.py
if ($LASTEXITCODE -ne 0) { throw "Focused native regression tests failed. STOP." }

git branch --show-current
git rev-parse --short HEAD
~~~

## Step 2 — Run a NEW disposable native evidence acquisition

It creates three genuine Council-promoted P structures and one Q in a NEW controlled kernel. There are 9 taught primitive relations inside the native memories, with NO native cross-P bridge. The program asks its first cross-P query and expects a gap. It then receives an explicit independently staged **teacher testimony** (not verified world evidence) as an experimental observation r4 PRECEDES s1. No target answer is supplied.

~~~powershell
Set-Location "$env:USERPROFILE\Verdant-Pocket-Evidence-V21"
$Py = ".\.venv\Scripts\python.exe"

$Folder = Join-Path (Get-Location).Path ("evidence-v21-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Path $Folder -ErrorAction Stop | Out-Null

$Report = Join-Path $Folder "controlled-acquisition.json"
$Journal = Join-Path $Folder "retained-evidence.vpel.json"

& $Py -m verdant_pockets.research_acquisition_demo --out $Report --ledger $Journal
if ($LASTEXITCODE -ne 0) {
    throw "Controlled acquisition experiment failed. STOP."
}
~~~

Expected: The pre-observation query abstains; after the external observation a *conditional experimental composition* becomes supported; a different held-out query is also supported using the same primitive; negative controls abstain; the flat graph given the same evidence also supports the outcome. Original user checkpoint untouched.

## Step 3 — Independent replay from freshly reconstructed native memory

The following starts a separate invocation, recreates the original controlled *pre-bridge* native source, verifies the saved journal against its exact checkpoint-derived identity, and repeats a held-out query.

~~~powershell
& $Py -m verdant_pockets.research_acquisition_demo --verify $Journal
if ($LASTEXITCODE -ne 0) {
    throw "Fresh-process retained-journal verification failed."
}
Write-Host "Ready to inspect:" $Folder
Invoke-Item $Folder
~~~

Please upload controlled-acquisition.json and retained-evidence.vpel.json, plus console output. Both are text JSON and contain explicit source identities, proof provenance, controls and no native writeback.

## Scientific boundary

The observed bridge is source-attested by our controlled harness. It is **not** independently verified truth; its digest proves bytes, not source authenticity. The conditional answer does not become canonical. The fresh held-out query is from the same small corpus, and the transitive PRECEDES rule is hard-coded externally. The flat baseline should find the same answer. True sensor evidence, endogenous bridge discovery, cost improvement, independent daughter learning, and Council promotion remain unproven future milestones.

Reference: docs/COGNITIVE_POCKET_EVIDENCE_RETENTION_V21.md
