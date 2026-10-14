# Vast integrated developmental experiment — Windows handoff

This is the **first bounded integration**, not a declaration that the entire Obligation Substrate is autonomously active. It reuses the real V5/V5-X developmental heartbeat and the Workbench CurriculumCompiler against the user's exact VCpack. Native obligation detectors and compilation diagnostics are **read-only**. The software preserves the active obligation v0.65 branch and historical math results, without changing V5 or V5-X.

## Prepare isolated checkout

Run in a NEW PowerShell window, not inside your working V5-X directory:

```powershell
$Work = "$env:USERPROFILE\Verdant-Vast-Integrated-Test"
if (Test-Path $Work) { throw "Checkout exists. Do not overwrite it." }
git clone --branch test/vast-integrated-development-v0 --single-branch https://github.com/Captainkoopa42/Verdant-Minds.git "$Work"
if ($LASTEXITCODE -ne 0) { throw "Clone failed." }
Set-Location $Work
py -3.11 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Python 3.11 environment failed." }
$Py = ".\.venv\Scripts\python.exe"
& $Py -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
& $Py -m pytest -q tests/test_vast_integrated.py
if ($LASTEXITCODE -ne 0) { throw "Focused integration tests failed. Stop." }
```

## Select the actual curriculum you uploaded

Download or copy the `.vcpack` to your Windows Downloads folder. If you have multiple copies, select the matching file rather than assuming the filename:

```powershell
$Candidates = @(Get-ChildItem "$env:USERPROFILE\Downloads" -Filter 'verdant_vast_developmental_curriculum_001*.vcpack' -File)
$ExpectedHash = "65724b4ad2e9dedf30d9bc00b1e31763b213ba5b65b00edc3701a1504d299bd4"
$Matches = @($Candidates | Where-Object { (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -eq $ExpectedHash })
if ($Matches.Count -ne 1) {
    throw "Expected exactly one matching curriculum in Downloads. Locate or copy the original VCpack there; do not substitute a different version silently."
}
$Pack = $Matches[0].FullName
Write-Host "Using:" $Pack
& $Py -m verdant_integrated.vast preview $Pack --sections 1
if ($LASTEXITCODE -ne 0) { throw "Curriculum preflight failed." }
```

## Stage A — one-section smoke (20 teaching experiences per arm)

```powershell
$Output = ".\vast-smoke-01"
if (Test-Path $Output) { throw "Output directory already exists." }
$Watch = [Diagnostics.Stopwatch]::StartNew()
& $Py -m verdant_integrated.vast start $Output $Pack --sections 1 --seeds 81001
$ExitCode = $LASTEXITCODE
$Watch.Stop()
Write-Host "Seconds:" $Watch.Elapsed.TotalSeconds
if ($ExitCode -ne 0) { throw "Smoke interrupted or failed. Preserve output." }
& $Py -m verdant_integrated.vast report $Output
if ($LASTEXITCODE -ne 0) { throw "Stage verification or report failed." }
```

The three roles get 20 **teaching experiences each**. The true full-heartbeat roles can advance **multiple internal kernel cycles per experience**; the output deliberately reports the numbers separately. Baseline `kernel_only` is a storage control, **not** equivalent computational effort.

## Stage B — three sections, then full 30-section one-seed cohort

Start each in a fresh output directory only **after** prior stages pass. The complete run may take much longer than the recent direct-kernel pilots; record timings and disk growth, not guessed runtimes.

```powershell
$Output = ".\vast-three-sections"
if (Test-Path $Output) { throw "Output directory already exists." }
& $Py -m verdant_integrated.vast start $Output $Pack --sections 3 --seeds 81001
if ($LASTEXITCODE -ne 0) { throw "Three-section stage failed. Preserve evidence." }
& $Py -m verdant_integrated.vast report $Output
if ($LASTEXITCODE -ne 0) { throw "Report failed." }
```

Once resource usage is acceptable, execute the complete **600-experience** curriculum through each of the three arms with one seed:

```powershell
$Output = ".\vast-full-30-one-seed"
if (Test-Path $Output) { throw "Output directory already exists." }
$Watch = [Diagnostics.Stopwatch]::StartNew()
& $Py -m verdant_integrated.vast start $Output $Pack --sections 30 --seeds 81001
$ExitCode = $LASTEXITCODE
$Watch.Stop()
Write-Host "Seconds:" $Watch.Elapsed.TotalSeconds
if ($ExitCode -ne 0) { throw "Run incomplete. Preserve outputs before recovery." }
& $Py -m verdant_integrated.vast report $Output
if ($LASTEXITCODE -ne 0) { throw "Verification failed." }
```

If that completes, a separately chosen fresh output folder and `--seeds 81001 81002 81003` will run 3 × 3 arms × 600 teaching items = 5,400 **experience inputs**, not 5,400 native internal cycles. Do not begin those additional seeds until capacity is measured.

## Interrupted process recovery

No code changes, no `git pull`, no overwritten stages and no re-running `start` in the same folder. After checking the cause is an ordinary interruption:

```powershell
Set-Location "$env:USERPROFILE\Verdant-Vast-Integrated-Test"
$Py = ".\.venv\Scripts\python.exe"
$Output = ".\vast-full-30-one-seed"
& $Py -m verdant_integrated.vast status $Output
if ($LASTEXITCODE -ne 0) { throw "Integrity status failed. Preserve evidence." }
& $Py -m verdant_integrated.vast resume $Output
if ($LASTEXITCODE -ne 0) { throw "Resume failed. Preserve evidence." }
& $Py -m verdant_integrated.vast report $Output
if ($LASTEXITCODE -ne 0) { throw "Final report verification failed." }
```

A fully committed section can be resumed; an interruption between writing a VDK stage and its JSON receipt **fails closed** rather than altering or guessing the original checkpoint. There is no general automatic partial-section resume in v0.1.

## What to return from Stage A/B

Share the focused pytest result, per-stage save messages, runtime, and `report` output. The report lists *actual* engine cycles, native semantic counts, plastic associations, P/Q status, and read-only obligation candidate counts. Zero DependencyGap findings may be the correct result: synthetic `depends_on` does not automatically satisfy the detector's qualified `requires` + Action/Outcome policy.

Preserve `manifest.json`, `curriculum.vcpack`, `stages/` (checkpoint + receipt pairs), and `results.json` in each output folder. They include the exact input identity, code hashes and native state.

The operator pack's 240 probes are **compilation inspections without answer labels**, not scientific correctness scores. This run does not execute integrated inquiry, authorize real actions, automatically promote P/Q, claim an autonomous mind, or rewrite obligations. Future increments must test those explicit gates on matched private forks with native evidence.
