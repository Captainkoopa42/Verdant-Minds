# Verdant Structural Transfer v0.1 — PowerShell

The separate branch is `test/structural-transfer-v0`. The experimental runner uses native Verdant claim/evidence storage and a supplied path-walking rule. It probes 8 **unseen multi-hop compositions** without teaching their final answers. Four other final cases are deliberately unreachable and should abstain. Controls: `progressive`, `exact_null`, `no_rule`, `incomplete`, `wrong_link`. The default 3 seeds and 1,000 native cycles per arm total 15,000 operations. It does **not** show independent rule discovery, unscaffolded transfer, generalized arithmetic or autonomous intelligence.

Do not merge old branches or touch completed retention outputs. No training is triggered on push.

## 1. New Windows checkout (once)

```powershell
$Work = "$env:USERPROFILE\Verdant-Structural-Transfer-Test"
if (Test-Path $Work) { throw "Checkout already exists. Use that folder rather than overwrite it." }
git clone --branch test/structural-transfer-v0 --single-branch https://github.com/Captainkoopa42/Verdant-Minds.git "$Work"
if ($LASTEXITCODE -ne 0) { throw "Clone failed" }
Set-Location $Work
py -3.11 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Python environment failed" }
$Py = ".\.venv\Scripts\python.exe"
& $Py -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed" }
```

## 2. Run focused tests

```powershell
Set-Location "$env:USERPROFILE\Verdant-Structural-Transfer-Test"
$Py = ".\.venv\Scripts\python.exe"
& $Py -m pytest -q tests/test_structural_transfer.py
if ($LASTEXITCODE -ne 0) { throw "Tests failed. Stop." }
```

## 3. Run 200-cycle/arm Windows smoke first

```powershell
$Output = ".\structural-smoke-200"
if (Test-Path $Output) { throw "Output exists" }
& $Py -m verdant_math.structural_transfer.experiment start $Output --cycles 200
if ($LASTEXITCODE -ne 0) { throw "Smoke failed" }
& $Py -m verdant_math.structural_transfer.experiment status $Output
if ($LASTEXITCODE -ne 0) { throw "Stage integrity failure" }
& $Py -m verdant_math.structural_transfer.experiment grade $Output
if ($LASTEXITCODE -ne 0) { throw "Smoke grading failed" }
```

## 4. Full 1,000-cycle/arm structural-transfer pilot

Only after the tests and smoke pass:

```powershell
$Output = ".\structural-transfer-1000"
if (Test-Path $Output) { throw "Output exists" }
$Watch = [Diagnostics.Stopwatch]::StartNew()
& $Py -m verdant_math.structural_transfer.experiment start $Output --cycles 1000
$Exit = $LASTEXITCODE
$Watch.Stop()
Write-Host "Seconds:" $Watch.Elapsed.TotalSeconds
if ($Exit -ne 0) { throw "Run interrupted or failed. Preserve directory." }
& $Py -m verdant_math.structural_transfer.experiment status $Output
if ($LASTEXITCODE -ne 0) { throw "Stage integrity failure" }
& $Py -m verdant_math.structural_transfer.experiment grade $Output
if ($LASTEXITCODE -ne 0) { throw "Grading failed" }
$Result = Get-Content "$Output\grades.json" -Raw | ConvertFrom-Json
$Hash = (Get-FileHash "$Output\responses.json" -Algorithm SHA256).Hash.ToLowerInvariant()
if ($Hash -ne $Result.response_sha256) { throw "Response and grading hashes disagree" }
$Result.grading | ForEach-Object {
    $Last = $_.probes[-1]
    [PSCustomObject]@{
        Seed=$_.seed; Role=$_.role
        Correct=$Last.correct; Incorrect=$Last.incorrect
        Abstained=$Last.abstained; Total=$Last.total
    }
} | Format-Table -AutoSize
```

## Resume interrupted run (do not run start again)

Only after diagnosing an ordinary interruption, not a failed integrity check:

```powershell
Set-Location "$env:USERPROFILE\Verdant-Structural-Transfer-Test"
$Py = ".\.venv\Scripts\python.exe"
$Output = ".\structural-transfer-1000"
& $Py -m verdant_math.structural_transfer.experiment status $Output
if ($LASTEXITCODE -ne 0) { throw "Invalid checkpoint; preserve evidence" }
& $Py -m verdant_math.structural_transfer.experiment resume $Output
if ($LASTEXITCODE -ne 0) { throw "Resume failed; preserve evidence" }
& $Py -m verdant_math.structural_transfer.experiment grade $Output
if ($LASTEXITCODE -ne 0) { throw "Grading failed" }
```

The run saves immutable, hashed per-arm `.vst` stages with checkpoint bytes, native events, private teaching schedules and trace-grounded responses. All native responses are durably recorded before separate external grading. A code or manifest change fails closed during resume; do not edit saved evidence. Preserve `manifest.json`, `responses.json`, `grades.json`, and `stages/`.

Existing `v0.65` evidence remains untouched. The full 12,000-per-arm adaptive curriculum still requires separate experimental implementation and validation.
