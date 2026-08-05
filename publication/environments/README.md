# Environment records

Each campaign platform receives a machine-readable environment record containing:

- operating system and architecture;
- Python implementation and version;
- dependency-lock SHA-256;
- installed-package snapshot;
- candidate commit and dirty-worktree status;
- test command and result;
- start and completion timestamps.

The Phase 0 Linux record is generated after the complete preflight run. The Windows record is produced during the cross-platform phase rather than inferred from Linux.

