# ====================================================================
# Verdant-Minds V5-X Isolated Validation Batch Runner
# ====================================================================

param(
    [int[]]$Seeds = @(8501, 8513, 8521, 1901, 2026),
    [string]$OutputVault = "Verdant_V5X_Validation_Data",
    [int]$StateDim = 16,
    [int]$NoiseConcepts = 0,
    [string]$SourceRef = "V5-X",
    [ValidateSet("all", "m19", "thermodynamics", "lesions")]
    [string]$Experiment = "all"
)

$ErrorActionPreference = "Stop"
$Runner = "run_v5x_validation.py"
$PipelineLog = Join-Path $OutputVault "global_batch_pipeline_log.txt"

if (!(Test-Path $Runner)) {
    throw "Run this script from the repository root where $Runner is present."
}
if (!(Test-Path $OutputVault)) {
    New-Item -ItemType Directory -Path $OutputVault | Out-Null
}

"====================================================" | Tee-Object -FilePath $PipelineLog
"LAUNCHING V5-X ISOLATED VALIDATION PROTOCOL" | Tee-Object -FilePath $PipelineLog -Append
"Timestamp: $(Get-Date -Format 'MMM dd, yyyy, h:mm tt')" | Tee-Object -FilePath $PipelineLog -Append
"Seeds: $($Seeds -join ', ')" | Tee-Object -FilePath $PipelineLog -Append
"Experiment: $Experiment" | Tee-Object -FilePath $PipelineLog -Append
"====================================================" | Tee-Object -FilePath $PipelineLog -Append

foreach ($Seed in $Seeds) {
    $RunDate = Get-Date -Format 'yyyyMMdd-HHmmss'
    $RunDir = Join-Path $OutputVault "V5X-Seed-$Seed-$RunDate"
    New-Item -ItemType Directory -Path $RunDir | Out-Null
    $Output = Join-Path $RunDir "validation.json"

    "START seed=$Seed at $(Get-Date -Format 'h:mm tt')" | Tee-Object -FilePath $PipelineLog -Append
    $Args = @(
        $Runner,
        "--seed", $Seed,
        "--state-dim", $StateDim,
        "--noise-concepts", $NoiseConcepts,
        "--experiment", $Experiment,
        "--output", $Output,
        "--source-ref", $SourceRef,
        "--headless"
    )
    $Worker = Start-Process python -ArgumentList $Args -Wait -NoNewWindow -PassThru
    if ($Worker.ExitCode -eq 0) {
        "SUCCESS seed=$Seed package=$Output" | Tee-Object -FilePath $PipelineLog -Append
    } else {
        "ERROR seed=$Seed exit=$($Worker.ExitCode)" | Tee-Object -FilePath $PipelineLog -Append
    }
    [System.GC]::Collect()
}

"====================================================" | Tee-Object -FilePath $PipelineLog -Append
"V5-X BATCH COMPLETE" | Tee-Object -FilePath $PipelineLog -Append
"Final Timestamp: $(Get-Date -Format 'MMM dd, yyyy, h:mm tt')" | Tee-Object -FilePath $PipelineLog -Append
"====================================================" | Tee-Object -FilePath $PipelineLog -Append
