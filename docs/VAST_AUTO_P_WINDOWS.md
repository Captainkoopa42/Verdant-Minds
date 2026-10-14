# Automated P Promotion — Windows experimental handoff

Use a NEW checkout. Do not modify previous 20/60/200-experience baseline experiments, their archives, V5, V5-X or the active Obligation Substrate branch. The new research branch has four arms: v5 and v5x_observe (unpromoted developmental controls), v5x_auto_p (automatic native Council-gated P promotion), and kernel_only (direct-storage control).

## Optional first: inspect old 200-experience P eligibility, READ-ONLY

In your already-existing Verdant-Vast-Integrated-Test folder:

~~~powershell
Set-Location "$env:USERPROFILE\Verdant-Vast-Integrated-Test"
$Py = ".\.venv\Scripts\python.exe"
& $Py -c "from pathlib import Path; from collections import Counter; from verdant_kernel import load_checkpoint, VerdantKernel; p=Path('vast-ten-sections/stages/seed-81001/v5/010.vdk'); k=VerdantKernel.from_state(load_checkpoint(p)); print('Total P candidates:',len(k.state.structure_candidates)); print('P status:',dict(Counter(c.status.value for c in k.state.structure_candidates.values()))); print('Already promoted:',len(k.state.structures))"
~~~

ELIGIBLE candidates satisfy preliminary native thresholds. Council approval is a separate required gate. This command does not promote anything.

## Step 1 — isolated clone and dependencies

In a NEW PowerShell window:

~~~powershell
$Work = "$env:USERPROFILE\Verdant-Vast-AutoP-Test"
if (Test-Path $Work) { throw "Auto-P checkout already exists. Preserve it." }
git clone --branch test/vast-auto-p-promotion-v0 --single-branch https://github.com/Captainkoopa42/Verdant-Minds.git "$Work"
if ($LASTEXITCODE -ne 0) { throw "Git clone failed." }
Set-Location $Work
py -3.11 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Python 3.11 environment failed." }
$Py = ".\.venv\Scripts\python.exe"
& $Py -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
& $Py -m pytest -q tests/test_vast_integrated.py tests/test_structures_phase.py
if ($LASTEXITCODE -ne 0) { throw "Native auto-P tests failed. STOP." }
git branch --show-current
git rev-parse --short HEAD
~~~

## Step 2 — exact original VCpack only

Save the same previously uploaded curriculum in Windows Downloads:

~~~powershell
$ExpectedHash = "65724b4ad2e9dedf30d9bc00b1e31763b213ba5b65b00edc3701a1504d299bd4"
$Candidates = @(Get-ChildItem "$env:USERPROFILE\Downloads" -Filter "verdant_vast_developmental_curriculum_001*.vcpack" -File)
$Matches = @($Candidates | Where-Object { (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -eq $ExpectedHash })
if ($Matches.Count -eq 0) { throw "Original verified curriculum not found." }
$Pack = $Matches[0].FullName
Write-Host "Verified: $Pack"
& $Py -m verdant_integrated.vast preview $Pack --sections 1
if ($LASTEXITCODE -ne 0) { throw "Pack compiler preflight failed." }
~~~

## Step 3 — first single-section four-arm smoke test

~~~powershell
$Output = ".\vast-autop-smoke-01"
if (Test-Path $Output) { throw "Output exists; do not overwrite." }
$Watch = [Diagnostics.Stopwatch]::StartNew()
& $Py -m verdant_integrated.vast start $Output $Pack --sections 1 --seeds 81001
$ExitCode = $LASTEXITCODE
$Watch.Stop()
Write-Host "Elapsed seconds:" $Watch.Elapsed.TotalSeconds
if ($ExitCode -ne 0) { throw "Experiment failed; preserve output." }
& $Py -m verdant_integrated.vast report $Output
if ($LASTEXITCODE -ne 0) { throw "Stage verification failed." }
~~~

Inspect the native P promotion receipt:

~~~powershell
$Receipt = Get-Content ".\vast-autop-smoke-01\stages\seed-81001\v5x_auto_p\001.json" -Raw | ConvertFrom-Json
$Receipt.p_promotion | ConvertTo-Json -Depth 12
~~~

The receipt includes how many candidates were eligible, promoted, deferred, or unconsidered because of the cap. Native Council decision IDs bind actual authorized promotion events. Zero promotions are valid if no candidate passes the gates.

## Step 4 — three sections ONLY AFTER one-section smoke passes

~~~powershell
$Output = ".\vast-autop-three-sections"
if (Test-Path $Output) { throw "Output exists; do not overwrite." }
$Watch = [Diagnostics.Stopwatch]::StartNew()
& $Py -m verdant_integrated.vast start $Output $Pack --sections 3 --seeds 81001
$ExitCode = $LASTEXITCODE
$Watch.Stop()
Write-Host "Elapsed seconds:" $Watch.Elapsed.TotalSeconds
if ($ExitCode -ne 0) { throw "Experiment failed; preserve output." }
& $Py -m verdant_integrated.vast report $Output
if ($LASTEXITCODE -ne 0) { throw "Stage verification failed." }
~~~

Stop at three sections for now. The ten-section baseline with three arms already required about 33 minutes, and real P promotion adds additional Council and structure transitions.

## Resume without mutating previous files

~~~powershell
Set-Location "$env:USERPROFILE\Verdant-Vast-AutoP-Test"
$Py = ".\.venv\Scripts\python.exe"
$Output = ".\vast-autop-three-sections"
& $Py -m verdant_integrated.vast status $Output
if ($LASTEXITCODE -ne 0) { throw "Integrity status failed. STOP." }
& $Py -m verdant_integrated.vast resume $Output
if ($LASTEXITCODE -ne 0) { throw "Resume failed. Preserve evidence." }
& $Py -m verdant_integrated.vast report $Output
if ($LASTEXITCODE -ne 0) { throw "Report failed." }
~~~

Never run start again on an existing study folder. Do not change the Python code, pull a later commit, edit receipts or delete an incomplete checkpoint pair to force recovery. The immutable source manifest checks for code drift; only fully published section boundaries are restartable.

## Research limits

The scheduling of eligible P candidates is fixed external policy, not something Verdant independently learned. It acts only at section boundaries, promoting at most four per section, through existing recurrence, diversity, cohesion, reconstructability, selectivity, cross-context and Council gates. It does not automatically promote Q, run multi-family Obligation Substrate inquiry, use Tg for behavioral control, claim correct factual understanding or grade the 240 supplied diagnostic cues. Compare P reuse on native compilation probes, not merely raw number of promoted structures.
