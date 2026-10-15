# Windows: Run the full bounded Cognitive Pocket developmental experiment

This uses the exact existing 336-cycle, seed-81001 Section 3 native VDK and **does not** rerun training, edit native checkpoints, or modify V5. The new `.vcpl` files contain the *experimental* activity and evidence-preserving pockets.

Your existing checkout: `C:\Users\Owner\Verdant-Pocket-Cultivation-Test`. Keep it on `test/cognitive-pocket-cultivation-v0`.

## 1. Update and verify

Open PowerShell:

~~~powershell
$Work = "$env:USERPROFILE\Verdant-Pocket-Cultivation-Test"
Set-Location $Work
$Branch = "test/cognitive-pocket-cultivation-v0"

if ((git branch --show-current).Trim() -ne $Branch) {
    throw "Wrong branch. STOP without switching over other experiments."
}

git pull --ff-only origin $Branch
if ($LASTEXITCODE -ne 0) { throw "Pull failed: STOP." }

$Py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { throw "Existing experiment Python environment missing." }

& $Py -m pytest -q tests/test_cognitive_pocket_cultivation.py tests/test_cognitive_pocket_lifecycle.py tests/test_cognitive_pocket_integration.py tests/test_hierarchy_phase.py tests/test_structure_interaction_phase.py tests/test_obligation_substrate.py tests/test_counterfactual_runtime.py
if ($LASTEXITCODE -ne 0) { throw "Tests failed: STOP and share the error." }

git rev-parse --short HEAD
~~~

## 2. Read original native memory into both Q pockets

Paste another complete block:

~~~powershell
Set-Location "$env:USERPROFILE\Verdant-Pocket-Cultivation-Test"
$Py = ".\.venv\Scripts\python.exe"
$Original = "$env:USERPROFILE\Verdant-Vast-AutoPQ-Test\vast-auto-pq-three-sections\stages\seed-81001\v5x_auto_pq\003.vdk"
if (-not (Test-Path $Original)) { throw "Original VDK missing: STOP." }

$Before = (Get-FileHash $Original -Algorithm SHA256).Hash
$Folder = Join-Path (Get-Location).Path ("lifecycle-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Path $Folder -ErrorAction Stop | Out-Null

Write-Host "=== ORIGINAL Q #1 ==="
& $Py -m verdant_pockets.lifecycle_cli $Original --q-index 0 --rounds 8 --max-links 2 --out (Join-Path $Folder "pocket-a.vcpl")
if ($LASTEXITCODE -ne 0) { throw "Q pocket A failed: STOP." }

Write-Host "=== ORIGINAL Q #2 ==="
& $Py -m verdant_pockets.lifecycle_cli $Original --q-index 1 --rounds 8 --max-links 2 --out (Join-Path $Folder "pocket-b.vcpl")
if ($LASTEXITCODE -ne 0) { throw "Q pocket B failed: STOP." }

$After = (Get-FileHash $Original -Algorithm SHA256).Hash
if ($Before -ne $After) { throw "Source checkpoint hash changed: STOP." }

Write-Host "Original VDK unchanged: True"
Write-Host "Experimental results folder:" $Folder
~~~

These execute multiple **numeric** arms per original P member, local adaptive sessions, daughter partition construction, exact relation dictionary compression, and read-only native obligation inspection. A difference between arms is NOT automatically a better model or earned semantic composite.

## 3. Verify immutable local sidecars and create offline demos

~~~powershell
Set-Location "$env:USERPROFILE\Verdant-Pocket-Cultivation-Test"
$Py = ".\.venv\Scripts\python.exe"

foreach ($Name in @("pocket-a", "pocket-b")) {
    $Source = Join-Path $Folder "$Name.vcpl"
    $Viewer = Join-Path $Folder "$Name.html"

    & $Py -m verdant_pockets.lifecycle_cli --verify $Source
    if ($LASTEXITCODE -ne 0) { throw "Invalid pocket sidecar: $Name" }

    & $Py -m verdant_pockets.viewer $Source --out $Viewer
    if ($LASTEXITCODE -ne 0) { throw "Viewer generation failed: $Name" }
}
Write-Host "Ready to inspect" $Folder
Invoke-Item $Folder
~~~

Open each `.html` file by double-clicking. The viewer is completely offline and includes a source P selector, experimental arm selector, local round slider, color-coded provenance, and a transfer trace. These diagrams are display layouts only; node positions are not an internal Verdant 3D geometry.

## 4. Share back

Please upload **pocket-a.vcpl** and **pocket-b.vcpl** here, plus any PowerShell error output if a step fails. The first contains the initial four-P Q and the second contains the eight-P Q, which subsumes the initial four; they are not independent experimental replicates.

Each .vcpl includes names of concepts, P/Q IDs, evidence IDs, numerical traces, compression receipts, private session outcomes, and the integrity chain. It does **not** contain the original raw VDK.

See `docs/COGNITIVE_POCKET_DEVELOPMENT_V1.md` for exactly what the system has, and what it does **not** yet prove.
