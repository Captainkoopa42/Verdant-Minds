# Windows — safe Q subfamily diagnostic and optional v0.4 curriculum comparison

This is a new isolated research branch. Your successful original V5/V5-X/Auto-P/Auto-PQ and kernel-only VDK results stay unchanged. Source/version identities intentionally prohibit using v0.4 to RESUME an old v0.3 experiment.

## 1 — NEW checkout, no pre-existing files removed

Open a new PowerShell window:

~~~powershell
$Work = "$env:USERPROFILE\Verdant-Vast-QSubfamily-Test"
if (Test-Path $Work) { throw "New work folder exists; do not overwrite it." }
git clone --branch test/vast-q-bounded-subfamilies-v0 --single-branch https://github.com/Captainkoopa42/Verdant-Minds.git "$Work"
if ($LASTEXITCODE -ne 0) { throw "Clone failed." }
Set-Location $Work
py -3.11 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Python 3.11 environment failed." }
$Py = ".\.venv\Scripts\python.exe"
& $Py -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency setup failed." }
& $Py -m pytest -q tests/test_q_subfamilies.py tests/test_hierarchy_phase.py tests/test_structure_interaction_phase.py tests/test_vast_integrated.py tests/test_structures_phase.py
if ($LASTEXITCODE -ne 0) { throw "Focused tests failed; stop." }
git branch --show-current
git rev-parse --short HEAD
~~~

Do NOT git pull after starting a new source-locked experimental cohort. No operator curriculum starts on clone or push.

## 2 — Audit the ALREADY COMPLETED 12-P/2-Q Section 3 checkpoint, READ-ONLY

This is the most useful immediate step. It does not require running one more lesson:

~~~powershell
Set-Location "$env:USERPROFILE\Verdant-Vast-QSubfamily-Test"
$Py = ".\.venv\Scripts\python.exe"
$OldCheckpoint = Join-Path $env:USERPROFILE "Verdant-Vast-AutoPQ-Test\vast-auto-pq-three-sections\stages\seed-81001\v5x_auto_pq\003.vdk"
if (-not (Test-Path $OldCheckpoint)) { throw "Existing native checkpoint missing. STOP." }

& $Py -m verdant_integrated.q_subfamily_audit $OldCheckpoint
if ($LASTEXITCODE -ne 0) { throw "Read-only audit failed." }
~~~

Look for component_reports and member_count=12. If bounded_subfamilies is empty and blocked_oversize_no_supported_split is true, the native Ps are too uniformly connected under this fixed policy to justify subgroup claims. This branch deliberately does NOT invent an arbitrary third Q. If distinct 3–8-sized groups are listed, verify their boundaries before trying a fresh 3-section run. Component pair similarities show only **association-graph topology**, not canonical relation type/direction.

## 3 — Only if the audit justifies further work: real pack verification

~~~powershell
$ExpectedHash = "65724b4ad2e9dedf30d9bc00b1e31763b213ba5b65b00edc3701a1504d299bd4"
$Matches = @(Get-ChildItem "$env:USERPROFILE\Downloads" -Filter "verdant_vast_developmental_curriculum_001*.vcpack" -File | Where-Object {
    (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -eq $ExpectedHash
})
if ($Matches.Count -eq 0) { throw "Exact original VCpack missing." }
$Pack = $Matches[0].FullName
& $Py -m verdant_integrated.vast preview $Pack --sections 1
if ($LASTEXITCODE -ne 0) { throw "Source compiler preflight failed." }
~~~

## 4 — Optional bounded one-section five-arm smoke

~~~powershell
$Output = ".\vast-qsubfamily-smoke-01"
if (Test-Path $Output) { throw "Output already exists; preserve." }
$Watch = [Diagnostics.Stopwatch]::StartNew()
& $Py -m verdant_integrated.vast start $Output $Pack --sections 1 --seeds 81001
$Code = $LASTEXITCODE
$Watch.Stop()
Write-Host "Elapsed seconds:" $Watch.Elapsed.TotalSeconds
if ($Code -ne 0) { throw "Experiment failed. Preserve all files." }
& $Py -m verdant_integrated.vast report $Output
if ($LASTEXITCODE -ne 0) { throw "Report verification failed." }
~~~

No change is expected to legacy 4-P Section 1 behavior. A positive one-section test is NOT proof the 12-P limit has been solved on real data.

## 5 — Optional 3-section matched comparison; do not run until audit review

~~~powershell
$Output = ".\vast-qsubfamily-three-sections"
if (Test-Path $Output) { throw "Output already exists; preserve." }
$Watch = [Diagnostics.Stopwatch]::StartNew()
& $Py -m verdant_integrated.vast start $Output $Pack --sections 3 --seeds 81001
$Code = $LASTEXITCODE
$Watch.Stop()
Write-Host "Elapsed seconds:" $Watch.Elapsed.TotalSeconds
if ($Code -ne 0) { throw "Experiment failed. Preserve checkpoints." }
& $Py -m verdant_integrated.vast report $Output
if ($LASTEXITCODE -ne 0) { throw "Report verification failed." }

$Stage = ".\vast-qsubfamily-three-sections\stages\seed-81001\v5x_auto_pq\003.json"
$Receipt = Get-Content $Stage -Raw | ConvertFrom-Json
$Receipt.q_promotion.oversized_hierarchy_diagnostics | ConvertTo-Json -Depth 12
~~~

Expect five native arms with separate lineages. Measure actual Q members, Council decisions, occurrence evidence and computational runtime; neither a positive Q count nor the synthetic control test is a learning score.

## Research restrictions

The 0.03 near-best and 0.03 internal-external symbolic score margins are fixed external experimental gates. Candidate size remains 3–8 and its native quality/Council requirements are unchanged. Uniform 12-P clique still abstains. We do not automatically turn on thermodynamic behavior, obligations, simulation writebacks, motor action, or Q policy learning. Do not change thresholds simply to force a Q.

For a failed run, use status/report under the same unchanged new source commit; do not modify an old source-frozen run or manually delete stage files.
