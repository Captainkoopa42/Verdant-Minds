# Verdant Workbench — WB-09 Plugin SDK, Packaging & Hardening

**Status:** Complete for Workbench 1.0 local-laboratory scope  
**Release:** Verdant Workbench 1.0.0

## Plugin SDK

Workbench now exposes `verdant.workbench.plugin.v1`.

The initial reference implementation is deliberately narrow: plugins execute as subprocesses, receive one explicit JSON payload on stdin, and return one JSON object on stdout. Normal plugins do not receive mutable `KernelState`, a Verdant engine adapter, or direct Workbench database access.

Plugin manifests declare:

```text
plugin_id
name
version
API contract version
kind
entrypoint
permissions
timeout
code SHA-256
```

Implemented protection includes:

- code-hash verification before invocation;
- plugin-directory path confinement;
- permission allow-listing;
- subprocess timeout;
- minimal process environment;
- input and output hashes on every successful result.

The bundled `example_metric` proves that an outside metric can be added without changing Verdant engine source.

**Security boundary:** subprocess separation is a capability/data boundary, not an OS sandbox. Workbench 1.0 must not execute untrusted local plugin code.

## Integrity and recovery

Workbench Engineering now provides artifact integrity scanning across indexed:

- checkpoints;
- curricula;
- experiments;
- provider captures.

Every artifact is checked against its content-addressed SHA-256.

On startup, run records left `active` by a crashed prior Workbench process are marked closed. Workbench does not fabricate the lost in-memory state. The user must explicitly reopen from the last verified checkpoint.

## Launcher / packaging

The repository now has a Workbench 1.0 launcher:

```bash
PYTHONPATH=.:workbench/backend python run_verdant_workbench.py
```

Useful options:

```bash
python run_verdant_workbench.py --home ./my-lab --port 8765 --open-browser
python run_verdant_workbench.py --home ./my-lab --check
```

`--check` runs startup/integrity diagnostics without launching the UI.

Workbench binds to loopback by default. It intentionally does not claim production multi-user authentication; the launcher warns on non-loopback binding.

A desktop/Tauri binary is not required for the 1.0 local-web architecture and has not been added. The stable REST/WebSocket contracts remain the packaging boundary for a future shell.

## Engineering UI

The **Engineering** page is now operational and exposes:

- Workbench/API version;
- project/run counts;
- provider/capture counts;
- artifact integrity state;
- discovered plugins and manifest validity;
- the reference metric-plugin invocation on an active organism.

## Controlled proof

The WB-09 proof:

1. creates a real isolated Verdant run;
2. teaches a controlled input;
3. executes the out-of-process example metric plugin;
4. records plugin input/output hashes;
5. saves a real checkpoint;
6. verifies artifact integrity;
7. simulates stale `active` metadata from a process crash;
8. starts a fresh Workbench service;
9. verifies stale-run recovery and unchanged checkpoint integrity.

`all_gates_pass = true` in `workbench/artifacts/wb09_workbench_1_0_proof.json`.

## Extension status

The manifest schema reserves `metric`, `exporter`, and `curriculum_provider` kinds. Workbench 1.0 provides the complete executable reference contract for **metric** plugins. Exporter/provider plugin execution can extend the same subprocess contract later without changing Verdant cognition.
