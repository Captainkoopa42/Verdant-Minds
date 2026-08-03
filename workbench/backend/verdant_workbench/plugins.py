from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

PLUGIN_MANIFEST_SCHEMA_VERSION = "verdant.plugin.manifest.v1"
PLUGIN_API_VERSION = "verdant.workbench.plugin.v1"


class PluginManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_id: Literal[PLUGIN_MANIFEST_SCHEMA_VERSION] = Field(default=PLUGIN_MANIFEST_SCHEMA_VERSION, alias="schema", serialization_alias="schema")
    plugin_id: str
    name: str
    version: str
    api_version: Literal[PLUGIN_API_VERSION] = PLUGIN_API_VERSION
    kind: Literal["metric", "exporter", "curriculum_provider"]
    entrypoint: tuple[str, ...]
    permissions: tuple[str, ...] = ()
    description: str = ""
    timeout_seconds: float = Field(default=10.0, ge=0.1, le=120.0)
    code_sha256: str


class PluginInvocationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    plugin_id: str
    plugin_version: str
    kind: str
    input_sha256: str
    output_sha256: str
    output: dict[str, Any]


class PluginError(RuntimeError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class PluginManager:
    """Narrow Workbench extension host.

    Initial SDK plugins run as subprocesses and receive only an explicit JSON payload.
    They do not receive KernelState or an engine adapter. This is a capability boundary,
    not an OS security sandbox; untrusted local code should not be installed.
    """

    ALLOWED_PERMISSIONS = {"read_snapshot", "read_metrics", "write_export"}

    def __init__(self, root: Path | str, *, bundled_root: Path | str | None = None) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.bundled_root = None if bundled_root is None else Path(bundled_root).resolve()

    def _plugin_dir(self, plugin_id: str) -> Path:
        candidates = [self.root / plugin_id]
        if self.bundled_root is not None:
            candidates.append(self.bundled_root / plugin_id)
        for raw in candidates:
            candidate = raw.resolve()
            base = self.root if self.root in candidate.parents else self.bundled_root
            if base is not None and (candidate == base or base in candidate.parents) and (candidate / "plugin.json").is_file():
                return candidate
        raise KeyError(plugin_id)

    def list_plugins(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        seen: set[str] = set()
        roots = [self.root] + ([] if self.bundled_root is None else [self.bundled_root])
        for root in roots:
            for manifest_path in sorted(root.glob("*/plugin.json")):
                plugin_id = manifest_path.parent.name
                if plugin_id in seen:
                    continue
                seen.add(plugin_id)
                try:
                    manifest = self.load_manifest(plugin_id)
                    items.append({"valid": True, "manifest": manifest.model_dump(mode="json", by_alias=True)})
                except Exception as exc:
                    items.append({"valid": False, "plugin_id": plugin_id, "error": str(exc)})
        return items

    def load_manifest(self, plugin_id: str) -> PluginManifest:
        plugin_dir = self._plugin_dir(plugin_id)
        manifest_path = plugin_dir / "plugin.json"
        if not manifest_path.is_file():
            raise KeyError(plugin_id)
        manifest = PluginManifest.model_validate_json(manifest_path.read_bytes())
        if manifest.plugin_id != plugin_id:
            raise PluginError("Plugin directory and manifest plugin_id differ.")
        bad = sorted(set(manifest.permissions) - self.ALLOWED_PERMISSIONS)
        if bad:
            raise PluginError("Unsupported plugin permissions: " + ", ".join(bad))
        if not manifest.entrypoint:
            raise PluginError("Plugin entrypoint cannot be empty.")
        script = (plugin_dir / manifest.entrypoint[-1]).resolve() if len(manifest.entrypoint) >= 2 else None
        if script is not None and plugin_dir not in script.parents:
            raise PluginError("Plugin entrypoint escapes plugin directory.")
        if script is not None and script.is_file():
            actual = hashlib.sha256(script.read_bytes()).hexdigest()
            if actual != manifest.code_sha256:
                raise PluginError(f"Plugin code hash mismatch: expected {manifest.code_sha256}, got {actual}.")
        return manifest

    def invoke(self, plugin_id: str, payload: dict[str, Any], *, required_kind: str | None = None) -> PluginInvocationResult:
        manifest = self.load_manifest(plugin_id)
        if required_kind is not None and manifest.kind != required_kind:
            raise PluginError(f"Plugin {plugin_id} is {manifest.kind}, not {required_kind}.")
        plugin_dir = self._plugin_dir(plugin_id)
        command = list(manifest.entrypoint)
        if len(command) >= 2:
            executable = command[0]
            script = (plugin_dir / command[-1]).resolve()
            command = [executable, *command[1:-1], str(script)]
        input_bytes = _canonical({"api_version": PLUGIN_API_VERSION, "plugin_id": plugin_id, "payload": payload})
        env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONIOENCODING": "utf-8",
            "VERDANT_PLUGIN_API_VERSION": PLUGIN_API_VERSION,
        }
        try:
            result = subprocess.run(
                command,
                input=input_bytes,
                cwd=plugin_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=manifest.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise PluginError(f"Plugin {plugin_id} timed out after {manifest.timeout_seconds}s.") from exc
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")[-2000:]
            raise PluginError(f"Plugin {plugin_id} failed with exit code {result.returncode}: {stderr}")
        try:
            output = json.loads(result.stdout.decode("utf-8"))
        except Exception as exc:
            raise PluginError(f"Plugin {plugin_id} returned invalid JSON.") from exc
        if not isinstance(output, dict):
            raise PluginError("Plugin output must be a JSON object.")
        return PluginInvocationResult(
            plugin_id=plugin_id,
            plugin_version=manifest.version,
            kind=manifest.kind,
            input_sha256=_sha(input_bytes),
            output_sha256=_sha(_canonical(output)),
            output=output,
        )
