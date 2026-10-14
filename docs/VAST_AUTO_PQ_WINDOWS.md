# Windows handoff — native automatic P + Q development

This is the first full P-to-Q *experimental* curriculum integration. It is NOT autonomous policy learning or the whole Obligation Substrate. Begin with one section; do not run all 600 lessons until measurement.

Keep all previous folders and experiments unchanged. The existing V5-X manual Workbench is not modified.

## 1. Optional read-only inspection of the old ten-section baseline

In PowerShell, if you want to know how many of your 42 native P candidates were eligible:

~~~powershell
Set-Location "$env:USERPROFILE\Verdant-Vast-Integrated-Test"
$Py = ".\.venv\Scripts\python.exe"
& $Py -c "from pathlib import Path; from collections import Counter; from verdant_kernel import load_checkpoint, VerdantKernel; p=Path('vast-ten-sections/stages/seed-81001/v5/010.vdk'); k=VerdantKernel.from_state(load_checkpoint(p)); print('P candidates:',len(k.state.structure_candidates)); print('Statuses:',dict(Counter(c.status.value for c in k.state.structure_candidates.values()))); print('Promoted P:',len(k.state.structures)); print('Promoted Q:',len(k.state.layered_structures))"
~~~

Reading the existing native VDK does not promote anything.

## 2. Install a NEW isolated research checkout

Open a NEW PowerShell window:

~~~powershell
$Work = "$env:USERPROFILE\Verdant-Vast-AutoPQ-Test"
if (Test-Path $Work) { throw "Folder already exists; preserve it." }
git clone --branch test/vast-auto-pq-development-v0 --single-branch https://github.com/Captainkoopa42/Verdant-Minds.git "$Work"
if ($LASTEXITCODE -ne 0) { throw "Clone failed." }
Set-Location $Work
py -3.11 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Python 3.11 setup failed." }
$Py = ".\.venv\Scripts\python.exe"
& $Py -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw "Locked dependency install failed." }
& $Py -m pytest -q tests/test_vast_integrated.py tests/test_structures_phase.py tests/test_hierarchy_phase.py
if ($LASTEXITCODE -ne 0) { throw "P/Q native tests failed. STOP." }
git branch --show-current
git rev-parse --short HEAD
~~~

Expected: 25 passing focused and native P/Q tests (unless additional tests were added later). No operator curriculum runs automatically.

## 3. Select ONLY the exact uploaded VCpack

The original user pack was verdant_vast_developmental_curriculum_001(1).vcpack, 1,272,615 bytes, field dimension 128. Find and verify matching original content in Windows Downloads:

~~~powershell
$ExpectedHash = "65724b4ad2e9dedf30d9bc00b1e31763b213ba5b65b00edc3701a1504d299bd4"
$Files = @(Get-ChildItem "$env:USERPROFILE\Downloads" -Filter "verdant_vast_developmental_curriculum_001*.vcpack" -File)
$Matching = @($Files | Where-Object { (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -eq $ExpectedHash })
if ($Matching.Count -lt 1) { throw "Exact uploaded VCpack not found. Stop." }
$Pack = $Matching[0].FullName
Write-Host "Using verified curriculum: $Pack"
& $Py -m verdant_integrated.vast preview $Pack --sections 1
if ($LASTEXITCODE -ne 0) { throw "Curriculum compilation preview failed." }
~~~

If this file does not match, **do not ignore the checksum** or silently substitute an edited pack.

## 4. First smoke test: 20 lessons per arm, 5 arms

~~~powershell
$Output = ".\vast-auto-pq-smoke-01"
if (Test-Path $Output) { throw "Output already exists. Preserve it." }
$Watch = [Diagnostics.Stopwatch]::StartNew()
& $Py -m verdant_integrated.vast start $Output $Pack --sections 1 --seeds 81001
$Code = $LASTEXITCODE
$Watch.Stop()
Write-Host "Elapsed seconds:" $Watch.Elapsed.TotalSeconds
if ($Code -ne 0) { throw "Smoke run failed. Preserve output for diagnosis." }
& $Py -m verdant_integrated.vast report $Output
if ($LASTEXITCODE -ne 0) { throw "Checkpoint report validation failed." }
~~~

Expected five arm names: v5, v5x_observe, v5x_auto_p, v5x_auto_pq, kernel_only. The new output includes P candidates, P eligible, promoted P, Q candidates, eligible Q, promoted Q, Q promotion events and native P-to-P interactions. Different native-cycle counts are expected.

## 5. Inspect exactly what P and Q automation did

~~~powershell
$Stage = ".\vast-auto-pq-smoke-01\stages\seed-81001\v5x_auto_pq\001.json"
$Receipt = Get-Content $Stage -Raw | ConvertFrom-Json
Write-Host "Native P scheduler:"
$Receipt.p_promotion | ConvertTo-Json -Depth 16
Write-Host "Native Q scheduler:"
$Receipt.q_promotion | ConvertTo-Json -Depth 16
~~~

A section with fewer than three promoted Ps should have no Q interactions or promoted Qs. This is expected, not a failure. When at least three native Ps exist, every Q interaction, observation and Council decision must be preserved in the checkpoint. The Q process does not work from unpromoted candidates.

## 6. Only after review: first THREE sections

~~~powershell
$Output = ".\vast-auto-pq-three-sections"
if (Test-Path $Output) { throw "Output already exists. Preserve it." }
$Watch = [Diagnostics.Stopwatch]::StartNew()
& $Py -m verdant_integrated.vast start $Output $Pack --sections 3 --seeds 81001
$Code = $LASTEXITCODE
$Watch.Stop()
Write-Host "Elapsed seconds:" $Watch.Elapsed.TotalSeconds
if ($Code -ne 0) { throw "Experiment interrupted or failed. Keep its archives." }
& $Py -m verdant_integrated.vast report $Output
if ($LASTEXITCODE -ne 0) { throw "Stage verification failed." }
~~~

Stop and compare output with previous P-only and no-promotion results before any 10- or 30-section attempt. The prior 200-experience three-arm baseline took over 33 minutes, and this five-arm P/Q study may be substantially slower.

## Interrupted study recovery (only unchanged source commit)

~~~powershell
Set-Location "$env:USERPROFILE\Verdant-Vast-AutoPQ-Test"
$Py = ".\.venv\Scripts\python.exe"
$Output = ".\vast-auto-pq-three-sections"
& $Py -m verdant_integrated.vast status $Output
if ($LASTEXITCODE -ne 0) { throw "Integrity failure. Do not resume." }
& $Py -m verdant_integrated.vast resume $Output
if ($LASTEXITCODE -ne 0) { throw "Resume failed. Preserve evidence." }
& $Py -m verdant_integrated.vast report $Output
if ($LASTEXITCODE -ne 0) { throw "Final stage verification failed." }
~~~

Do not modify code after a run starts. Do not reuse/overwrite outputs from earlier branches; their source/code hashes are intentionally different. Interrupted *partially written* stage pairs fail closed.

## Research interpretation

Automatic P/Q promotion is a **fixed external scheduling mechanism**. The native learner must still earn the P/Q structures and pass Council; Q also needs independently verified native P interactions. Neither promoted P nor Q proves understanding, independent procedural learning, faster computation, or successful curriculum mastery. Report what actually emerged with native evidence and appropriate negative controls.
