# V5-X Adversarial Provenance Stress Test

## What this runs

This is a deterministic, controlled V5-X benchmark. It creates two equally
weighted, independently declared direct observations about the same critical
state:

- `S1`: the critical loop is stable;
- `S2`: the critical loop is not stable.

It then verifies that V5-X:

1. preserves both evidence lineages;
2. creates an active contradiction without a preferred claim;
3. holds `current_belief` open;
4. defers and causally blocks an action that requires a definitive state;
5. leaves previously earned P and Q structures exact;
6. preserves compiled-probe cost and compression gain;
7. resolves preference only after a higher-weight physical-outcome record `S3`;
8. retains the rejected S2 claim and its evidence;
9. survives an exact checkpoint round trip.

The run also captures native V5-X thermodynamic telemetry. Proposed
`u_c`, `U_b`, `C_b`, and `F(t)` values are emitted separately as
benchmark-local, zero-authority shadow telemetry. They are not represented as
implemented kernel policy.

The current run is also expected to reveal a V5-X telemetry limitation: a
contradiction with a preferred claim is still a `weighted` contradiction, and
the developmental pipeline currently reintroduces it to workspace with full
contradiction pressure. The core evidence/governance test may therefore pass
while the report status is `core_pass_with_native_telemetry_gap`.

## Run on Windows PowerShell

From the Verdant-Minds repository:

```powershell
git fetch origin V5-X
git switch V5-X
git pull --ff-only origin V5-X

& .\.venv\Scripts\python.exe -m pytest -q tests/test_adversarial_provenance.py
& .\.venv\Scripts\python.exe .\run_adversarial_provenance.py
```

If the virtual environment does not exist yet, follow the repository's normal
V5-X installation instructions first.

## Share these results

After the run completes, share:

```text
artifacts/adversarial_provenance_v5x/adversarial_provenance_v5x_report.json
```

The corresponding exact checkpoint is:

```text
artifacts/adversarial_provenance_v5x/adversarial_provenance_v5x.vdk
```

The three exact controlled source texts are stored under:

```text
artifacts/adversarial_provenance_v5x/sources/
```

## Scientific boundary

This benchmark uses controlled declarations, not live authenticated sensors.
The current claim ledger also does not yet enforce dependency collapsing or
learn source-specific reliability. Those gaps are printed in the report rather
than silently treated as implemented behavior.
