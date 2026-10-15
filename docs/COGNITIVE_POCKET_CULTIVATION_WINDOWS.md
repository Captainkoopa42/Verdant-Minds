# Windows: replay original Verdant 12-P/2-Q memories inside isolated cognitive pockets

The 60-experience source study is **not rerun**. The two native Qs in Section 3 are your original earned structures. Pocket activity is deterministic private scratch computation and never commits any candidate fact.

Do not check out this new branch into an existing source-frozen VAST or Obligation Substrate clone. It begins at Obligation Substrate v0.67 and adds only read-only pocket experiments.

## One-time checkout and focused tests

Paste as one PowerShell block:

~~~powershell
$Work = "$env:USERPROFILE\Verdant-Pocket-Cultivation-Test"
if (Test-Path $Work) { throw "Folder already exists; preserve it." }

git clone --branch test/cognitive-pocket-cultivation-v0 --single-branch https://github.com/Captainkoopa42/Verdant-Minds.git "$Work"
if ($LASTEXITCODE -ne 0) { throw "Clone failed." }

Set-Location $Work
py -3.11 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Python 3.11 setup failed." }

$Py = ".\.venv\Scripts\python.exe"
& $Py -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw "Install failed." }

& $Py -m pytest -q tests/test_cognitive_pocket_cultivation.py tests/test_hierarchy_phase.py tests/test_structure_interaction_phase.py tests/test_obligation_substrate.py tests/test_counterfactual_runtime.py
if ($LASTEXITCODE -ne 0) { throw "Tests failed: STOP." }

git branch --show-current
git rev-parse --short HEAD
~~~

## Use the original 336-cycle Section-3 checkpoint (no teaching)

~~~powershell
Set-Location "$env:USERPROFILE\Verdant-Pocket-Cultivation-Test"
$Py = ".\.venv\Scripts\python.exe"

$Original = "$env:USERPROFILE\Verdant-Vast-AutoPQ-Test\vast-auto-pq-three-sections\stages\seed-81001\v5x_auto_pq\003.vdk"
if (-not (Test-Path $Original)) { throw "Original Section-3 VDK is missing." }

$Before = (Get-FileHash $Original -Algorithm SHA256).Hash
$Folder = Join-Path (Get-Location).Path ("pockets-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Path $Folder -ErrorAction Stop | Out-Null

& $Py -m verdant_pockets.cli $Original --q-index 0 --rounds 6 --out (Join-Path $Folder "first-q-pocket.json")
if ($LASTEXITCODE -ne 0) { throw "First Q pocket failed: STOP." }

& $Py -m verdant_pockets.cli $Original --q-index 1 --rounds 6 --out (Join-Path $Folder "second-q-pocket.json")
if ($LASTEXITCODE -ne 0) { throw "Second Q pocket failed: STOP." }

$After = (Get-FileHash $Original -Algorithm SHA256).Hash
if ($After -ne $Before) { throw "Original VDK changed: preserve evidence, STOP." }

Write-Host ""
Write-Host "=== READ-ONLY POCKETS ==="

Get-ChildItem $Folder -Filter "*.json" | ForEach-Object {
    $Export = Get-Content $_.FullName -Raw | ConvertFrom-Json
    $P = $Export.pocket
    [pscustomobject]@{
        Report                  = $_.Name
        NativeP                 = $P.p_snapshots.Count
        Concepts                = $P.concepts.Count
        HypotheticalAlignments  = $P.hypothetical_role_alignments.Count
        CanonicalCrossRelations = $P.evidenced_cross_p_relations.Count
        CanonicalCrossWalks     = $P.evidenced_cross_p_walks.Count
        RoleGrammars            = $P.grammar_inventory.Count
        ActivityRounds          = $P.local_rounds.Count
    }
} | Format-Table -AutoSize

Write-Host ""
Write-Host "Original VDK unchanged:" ($Before -eq $After)
Write-Host "Output folder:" $Folder
~~~

## Interpret correctly

- HypotheticalAlignments: native **topology** verification produced a candidate one-to-one role correspondence, NOT typed synonym evidence.
- CanonicalCrossRelations: actual present, evidenced, currently canonical relation records which join different P memberships (not inferred by Q).
- CanonicalCrossWalks: existing two-edge typed directed paths spanning a cross-P relation. A walk is not a new transitive fact.
- RoleGrammars: renaming-invariant equality patterns over current typed relation edges, potentially e.g. R-R versus R-S. This is a dictionary inventory and NOT demonstrated storage compression.
- ActivityRounds: simulation-only numeric activation in the local pocket including explicitly separate native-plastic, evidenced-cross-P and hypothetical-analogy channels. The hypothetical channel is NOT canonical learning, autonomous inquiry or a real causal model.

In the original disjoint 12-P memory, a Q may group P but contains no concept-level native bridge; zero cross-P relations and zero evidenced cross-walks are expected and meaningful. The implementation DOES NOT turn the analogy into a canonical edge to make results look better. Only a later, separately controlled experiment can test evidence-backed candidate cross-links and genuine transfer.

You can share both new JSON files here. They contain source concept labels and evidence IDs plus six rounds of synthetic local dynamics; no raw .vdk bytes. The original checkpoint and the Obligation Substrate experiments remain untouched.

See [the experimental specification](COGNITIVE_POCKET_CULTIVATION_V0.md) for exact claims, exclusions and next controls.
