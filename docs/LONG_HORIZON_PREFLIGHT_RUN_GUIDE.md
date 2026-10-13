# Running the native long-horizon feasibility pilot

Status: **experimental runner implemented; full 12,000-cycle curriculum NOT implemented or executed**. The preflight only measures native storage and direct taught-fact retention under interference. It is not evidence of adaptive transfer, arithmetic understanding, spontaneous learning, self-repair or agency. Neither existing v0.65 artifacts nor the core kernel are changed.

## What this runner actually performs

For each of three seeds, clones the same fresh native Verdant kernel into four isolated arms: progressive (eight different teacher-supplied addition facts over cycles 25–375), rehearsal (one fact repeatedly), activity-only (no math claims), and delayed (eight facts at cycles 625–975). All other charged cycles use genuine native experience transitions carrying no math answer. Native cycles, transition refs and restarts are checked. At cycles 0, 250, 500, 750 and 1,000 it saves an independent VDK checkpoint, reloads it and records read-only responses to all 20 fixed questions. A separate explicit command grades only after all responses have been written.

The run is **12,000 total native operations** at 1,000 cycles × 4 arms × 3 seeds; it is NOT the proposed **144,000-operation** 12,000-per-arm long-horizon curriculum. The final full curriculum additionally requires new genuinely disjoint held-outs, transfer and learning-efficiency tests, multi-domain learning adapters and a frozen prospective protocol.

## Windows PowerShell from the repository folder

Use a separate directory for each experiment; outputs are immutable and cannot be overwritten or resumed.

```powershell
Set-Location "$env:USERPROFILE\Verdant-Minds-V5X-Test"
git fetch origin
git switch test/long-horizon-curriculum-v0
git pull --ff-only origin test/long-horizon-curriculum-v0

# Existing project virtual environment, or replace with your installed Python.
$Py = ".\.venv\Scripts\python.exe"

# First, verify the implementation's focused tests.
& $Py -m pytest -q tests/test_long_horizon_preflight.py

# Then a tiny native smoke run, four roles by three seeds for 2 cycles
# (the runner defaults to three seeds).
& $Py -m verdant_math.long_horizon_preflight pilot ".\long-horizon-smoke" --cycles 2
& $Py -m verdant_math.long_horizon_preflight grade ".\long-horizon-smoke\responses.json" ".\long-horizon-smoke\grades.json"

# Only after the tests and smoke pass: 1,000 native cycles per arm.
& $Py -m verdant_math.long_horizon_preflight pilot ".\long-horizon-1000" --cycles 1000
& $Py -m verdant_math.long_horizon_preflight grade ".\long-horizon-1000\responses.json" ".\long-horizon-1000\grades.json"
```

If your checkout has a different folder, use that path instead. Do not run a different branch or merge the experimental branch into milestone branches.

## Evaluation guardrails

- Do not substitute benchmark truth for responder evidence.
- Every claim is explicit teacher testimony. A correct recalled addition fact is **not** a discovered arithmetic rule.
- Native unrelated experience cycles are **not** proof of learning. They provide a time/interference and checkpoint-continuity challenge.
- The early arm includes delayed probes before and after teaching; the delayed arm supplies a same-cycle-count comparison.
- Three seeds are *independent initialization replicates*, not independent scientific datasets.
- The trained, reversed and novel 20-case probes are explicit protocol-design choices, **not** independently frozen prospective holdouts. They can diagnose behavior but cannot justify a broad generalization claim.
- No outcomes or grades reach the responder. All replies are saved first; grading is a later explicit step.
- Every output gets a distinct directory. On failure, preserve partial outputs for analysis, and rerun in a new directory.
- Expect heavy Python/kernel CPU, RAM, and disk costs. The exact duration has not been benchmarked. Never claim a run succeeded unless complete native checkpoints, responses, grades and process exit statuses were inspected.
- Run the repository's full validation suite and legacy checkpoints before declaring the branch stable.
- The separate 12,000-per-arm curriculum must be implemented after preflight results and protocol freeze, not by raising this diagnostic runner's 1,000-cycle cap.

## Research report minimum

For every role and seed report exact native cycle count, number of distinct teacher facts introduced, fingerprint of initial and final private state, checkpoint failures, counts of correct/incorrect/abstained answers at each probe, and evidence of any failure. Explicitly distinguish persistence from transfer and repeated rehearsal.

A passing smoke test permits attempting the 1,000-cycle feasibility run. A passing feasibility run alone does **not** authorize the full curriculum without independent task design and resource estimates.
