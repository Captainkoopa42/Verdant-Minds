# Campaign manifests

No locked test manifest exists yet.

- Development manifests may contain visible cases used to debug generators and harness behavior.
- Validation manifests may be used to set feasible ranges before protocol sealing.
- The locked manifest is generated, hashed, and committed in Phase 3 before outcomes are opened.

Creating a file named `locked_test_manifest.jsonl` before Phase 3 is prohibited. The status file must identify the sealed protocol commit and manifest SHA-256 when that file is created.

