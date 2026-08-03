# Verdant Workbench Plugin SDK — WB-09

Plugin API: `verdant.workbench.plugin.v1`.

The initial SDK is intentionally narrow. A normal plugin does **not** receive mutable `KernelState`, a Verdant engine adapter, or a Workbench database connection. The Workbench launches the plugin as a subprocess and sends one explicit JSON object on stdin; the plugin returns one JSON object on stdout.

## Manifest

Each plugin lives in its own directory and contains `plugin.json` plus its executable/script. The manifest records plugin ID, version, API version, kind, declared permissions, entrypoint, timeout, and SHA-256 of the plugin code.

Supported initial kinds are `metric`, `exporter`, and `curriculum_provider`. The implemented reference path in Workbench 1.0 is the `metric` contract.

Supported declared permissions are:

- `read_metrics`
- `read_snapshot`
- `write_export`

Unknown permissions are rejected. The code hash is verified before invocation. Entry paths may not escape the plugin directory. Execution has a timeout and a deliberately minimal environment.

## Example metric plugin

`workbench/plugins/example_metric` receives:

```json
{
  "api_version": "verdant.workbench.plugin.v1",
  "plugin_id": "example_metric",
  "payload": {
    "run_id": "...",
    "metrics": {"concept_count": 4, "relation_count": 3}
  }
}
```

and returns a JSON metric record. Drop third-party plugins under `<WORKBENCH_HOME>/plugins/<plugin_id>/`.

## Security boundary

Subprocess separation is a capability/data boundary, **not an operating-system sandbox**. Do not install untrusted local plugin code. A future sandboxed plugin host can preserve the same JSON contract.
