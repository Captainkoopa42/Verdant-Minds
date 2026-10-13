# Long-Horizon Resumable Preflight (v0.2)

**Status:** 12 focused tests passed in GitHub Actions, including simulated interruption/recovery. This is an experimental 1,000-cycle-per-arm *retention* pilot, not the 12,000-cycle-per-arm general-learning curriculum.

Branch: test/long-horizon-curriculum-v0. All execution is opt-in; GitHub Actions runs only small focused tests.

## PowerShell: update and validate

```powershell
Set-Location "$env:USERPROFILE\Verdant-Long-Horizon-Test"
git fetch origin
git pull --ff-only origin test/long-horizon-curriculum-v0
$Py = ".\.venv\Scripts\python.exe"
& $Py -m pytest -q tests/test_long_horizon_preflight.py tests/test_long_horizon_resume.py
if ($LASTEXITCODE -ne 0) { throw "Tests failed. Do not run." }
```

## First validate recovery on a NEW 50-cycle run

```powershell
$Output = ".\long-horizon-resumable-50"
if (Test-Path $Output) { throw "Output exists. Choose a new folder." }
& $Py -m verdant_math.long_horizon_preflight.resumable start $Output --cycles 50
if ($LASTEXITCODE -ne 0) { throw "Smoke run failed; preserve output." }
& $Py -m verdant_math.long_horizon_preflight.resumable status $Output
if ($LASTEXITCODE -ne 0) { throw "Status validation failed." }
& $Py -m verdant_math.long_horizon_preflight grade "$Output\responses.json" "$Output\grades.json"
if ($LASTEXITCODE -ne 0) { throw "External grading failed." }
```

## Run the 1,000-cycle per-arm experiment (12,000 total operations)

Only after focused tests and smoke pass:

```powershell
$Output = ".\long-horizon-resumable-1000"
if (Test-Path $Output) { throw "Output exists. Choose a new folder." }
$Watch = [System.Diagnostics.Stopwatch]::StartNew()
& $Py -m verdant_math.long_horizon_preflight.resumable start $Output --cycles 1000
$Exit = $LASTEXITCODE
$Watch.Stop()
Write-Host "Elapsed seconds:" $Watch.Elapsed.TotalSeconds
if ($Exit -ne 0) { Write-Host "Interrupted or failed. Diagnose before resuming." }
```

To resume after an ordinary process interruption (never overwrite or rerun start):

```powershell
& $Py -m verdant_math.long_horizon_preflight.resumable status ".\long-horizon-resumable-1000"
& $Py -m verdant_math.long_horizon_preflight.resumable resume ".\long-horizon-resumable-1000"
if ($LASTEXITCODE -ne 0) { throw "Recovery failed; preserve outputs." }
```

Grade only after responses.json exists and the entire cohort finished:

```powershell
& $Py -m verdant_math.long_horizon_preflight grade ".\long-horizon-resumable-1000\responses.json" ".\long-horizon-resumable-1000\grades.json"
if ($LASTEXITCODE -ne 0) { throw "Grading failed." }
$Data = Get-Content ".\long-horizon-resumable-1000\grades.json" -Raw | ConvertFrom-Json
$Data.grading | ForEach-Object {
  $Last = $_.probes[-1]
  [PSCustomObject]@{ Seed=$_.seed; Role=$_.role; Cycle=$Last.cycle; Correct=$Last.correct; Incorrect=$Last.incorrect; Abstained=$Last.abstained; Total=$Last.total }
} | Format-Table -AutoSize
```

## Safety and interpretation

- Keep the previous long-horizon-50 and long-horizon-250 directories unchanged: those belong to the original nonresumable runner.
- The recovery runner writes new immutable per-arm .vstage receipts containing VDK checkpoint bytes, teaching history, response probes and a lineage chain.
- Each restart validates committed milestones and re-executes only uncommitted native cycles (normally at most 250 per arm). It does not overwrite existing committed outputs.
- A fresh output directory is mandatory. Do not run two processes for the same directory or manually edit artifacts.
- A source-code change or corrupted manifest is a hard stop, not permission to continue under altered conditions.
- All responses are durably written before the separate grading command is called.
- The 1,000-cycle pilot tests teacher-testimony retention and partial interference only. It cannot substantiate spontaneous learning, arithmetic generalization or cheaper learning.
- The full 144,000-operation cross-domain curriculum still requires additional teaching/transfer adapters and independent held-outs, and is not yet executable.