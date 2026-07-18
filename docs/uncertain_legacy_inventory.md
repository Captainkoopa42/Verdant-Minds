# Uncertain Legacy Inventory

These items were intentionally left in place because they may still validate, document, or support the current V4 build. They need owner review before archive, rename, or deletion.

## Leave in place for now

- `tests_v2/` — naming is historical, but collection succeeds and a sampled focused run passed. A full run was started and reached 4 passing tests before being interrupted after more than two minutes, so this suite needs a slower dedicated pass before rename/archive decisions.
- `Paper/` — filenames and text still contain older version naming, but the directory was part of the proposed retained submission surface. Confirm whether this is the current paper source/figure bundle before renaming or archiving.
- `analysis/state_adapter.py` — intentionally supports historical persisted state shapes, which may be useful for cross-version validation. Confirm whether backward compatibility is still required for V4 reproducibility.
- `Verdant_Minds_Runner_Patched (2).py` — retained as an experimental runner patch and explicitly excluded from the supported V4 runtime path in the README. Confirm whether it should be renamed, archived, or deleted later.
