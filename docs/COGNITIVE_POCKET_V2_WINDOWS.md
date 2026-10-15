# Windows walkthrough: run Verdant's selective compositional pocket v2

Branch: test/cognitive-pocket-selective-composition-v2.

This is a NEW isolated research clone. Do NOT switch an older working clone of V5, the Obligation Substrate, or the prior pocket v1 to this branch. Original VDKs are never overwritten. No seed runs on push.

## Step 1: Fresh isolated clone

Open PowerShell and paste this entire block:

~~~powershell
$Work = "$env:USERPROFILE\Verdant-Pocket-Composition-V2"
if (Test-Path $Work) { throw "Folder already exists. Preserve it and STOP." }
git clone --branch test/cognitive-pocket-selective-composition-v2 --single-branch https://github.com/Captainkoopa42/Verdant-Minds.git "$Work"
if ($LASTEXITCODE -ne 0) { throw "Clone failed." }

Set-Location $Work
py -3.11 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Python 3.11 environment failed." }

$Py = ".\.venv\Scripts\python.exe"
& $Py -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw "Dependencies failed." }

& $Py -m pytest -q tests/test_cognitive_pocket_composition.py tests/test_cognitive_pocket_curriculum.py tests/test_cognitive_pocket_cultivation.py tests/test_cognitive_pocket_lifecycle.py tests/test_cognitive_pocket_integration.py tests/test_hierarchy_phase.py tests/test_structure_interaction_phase.py tests/test_obligation_substrate.py tests/test_counterfactual_runtime.py
if ($LASTEXITCODE -ne 0) { throw "Focused research tests failed. STOP." }

git rev-parse --short HEAD
~~~

## Step 2: Run the POSITIVE controlled native training demonstration

A disposable native kernel earns three P structures and one Q. The teaching harness provides individual directed primitive relation testimony, including exactly one cross-P bridge, and predeclares the limited PRECEDES transitive rule. The *final composed answer is not taught*. This is not proof Verdant learned transitivity by itself.

~~~powershell
Set-Location "$env:USERPROFILE\Verdant-Pocket-Composition-V2"
$Py = ".\.venv\Scripts\python.exe"
$Folder = Join-Path (Get-Location).Path ("composition-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Path $Folder -ErrorAction Stop | Out-Null

& $Py -m verdant_pockets.research_demo --out (Join-Path $Folder "teacher-controlled-composition.json")
if ($LASTEXITCODE -ne 0) { throw "Controlled native v2 demonstration failed. STOP." }
~~~

Successful controlled demo should show a supported primitive-relation witness for the untaught conclusion and a separately graded six-task controlled curriculum. The result also includes missing, reversed, wrong-P, predicate mismatch and analogy-only ablations. No original VDK is accessed.

## Step 3: Run the NEGATIVE original 336-cycle native checkpoint check

This asks whether one event preceded a different kind of point across previously distinct Ps in the genuine 8-P Q. The source memory is not taught any new bridge. Because that original corpus has no canonical cross-P typed relation, correct behavior is *abstain_missing_supported_path*.

~~~powershell
Set-Location "$env:USERPROFILE\Verdant-Pocket-Composition-V2"
$Py = ".\.venv\Scripts\python.exe"
$Original = "$env:USERPROFILE\Verdant-Vast-AutoPQ-Test\vast-auto-pq-three-sections\stages\seed-81001\v5x_auto_pq\003.vdk"
if (-not (Test-Path $Original)) { throw "Original VDK not found. STOP." }

$Before = (Get-FileHash $Original -Algorithm SHA256).Hash

& $Py -m verdant_pockets.composition_cli $Original --q-index 1 --source-label first_event --target-label target_point --predicate precedes --out (Join-Path $Folder "original-native-abstention.json")
if ($LASTEXITCODE -ne 0) { throw "Original-memory negative control failed. STOP." }

$After = (Get-FileHash $Original -Algorithm SHA256).Hash
if ($Before -ne $After) { throw "Original VDK byte hash unexpectedly changed. STOP." }

Write-Host "Original VDK unchanged: True"
Write-Host "Outputs:" $Folder
Invoke-Item $Folder
~~~

### What to share for evaluation

Upload teacher-controlled-composition.json and original-native-abstention.json, plus the PowerShell test result if it did not pass.

The positive demo shows bounded explicit rule application to genuine P/Q native structures plus teacher-supplied primitive canonical edges. The negative original demonstrates safe abstention with no canonical bridge. Neither alone shows a learned semantic rule, independent discovery, consciousness, or measured advantage over flat native graph traversal.

Technical contract: docs/COGNITIVE_POCKET_SELECTIVE_COMPOSITION_V2.md.
