from __future__ import annotations

import hashlib
import io
import json
import os
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .curriculum import EditableTeachingBundle, TEACHING_BUNDLE_SCHEMA_VERSION
from .models import new_id, utc_now_iso

PROVIDER_CAPTURE_SCHEMA_VERSION = "verdant.provider.capture.v1"
PROVIDER_CONFIG_SCHEMA_VERSION = "verdant.provider.config.v1"
PROVIDER_CAPTURE_MEDIA_TYPE = "application/vnd.verdant.provider-capture+zip"


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ProviderConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_id: Literal[PROVIDER_CONFIG_SCHEMA_VERSION] = Field(default=PROVIDER_CONFIG_SCHEMA_VERSION, alias="schema", serialization_alias="schema")
    provider_id: str
    display_name: str
    kind: Literal["paste", "http_json"] = "paste"
    endpoint_url: str | None = None
    model: str | None = None
    secret_env: str | None = None
    enabled: bool = True
    timeout_seconds: float = Field(default=60.0, ge=1.0, le=300.0)
    extra_headers: dict[str, str] = Field(default_factory=dict)


class ProviderProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    prompt: str
    system_prompt: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    expected_schema: str = TEACHING_BUNDLE_SCHEMA_VERSION


class ProviderCapture(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_id: Literal[PROVIDER_CAPTURE_SCHEMA_VERSION] = Field(default=PROVIDER_CAPTURE_SCHEMA_VERSION, alias="schema", serialization_alias="schema")
    capture_id: str
    provider_id: str
    provider_kind: str
    created_at: str
    request_sha256: str
    response_sha256: str
    request: dict[str, Any]
    raw_response: str
    parsed_teaching_bundle: dict[str, Any] | None = None
    parse_error: str | None = None
    provider_metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderError(RuntimeError):
    pass


class ProviderRegistry:
    """Optional teaching-provider host.

    Providers are *outside* Verdant cognition. Their output is captured as an immutable
    artifact and must still flow through the editable teaching-record/compiler path.
    Secret values are read only at call time from environment variables; only the name
    of the environment variable is persisted.
    """

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.config_path = self.root / "providers.json"
        self.capture_index_path = self.root / "captures.json"
        if not self.config_path.exists():
            self._write_json(self.config_path, {"schema": "verdant.providers.index.v1", "providers": []})
        if not self.capture_index_path.exists():
            self._write_json(self.capture_index_path, {"schema": "verdant.provider-captures.index.v1", "captures": []})
        # Always ensure a zero-secret copy/paste adapter exists.
        if not any(p.provider_id == "provider_paste" for p in self.list_configs()):
            self.save_config(ProviderConfiguration(provider_id="provider_paste", display_name="Manual / External LLM Paste", kind="paste"))

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_bytes(_canonical_json_bytes(payload))
        os.replace(temp, path)

    def list_configs(self) -> list[ProviderConfiguration]:
        payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        return [ProviderConfiguration.model_validate(item) for item in payload.get("providers", [])]

    def get_config(self, provider_id: str) -> ProviderConfiguration:
        for item in self.list_configs():
            if item.provider_id == provider_id:
                return item
        raise KeyError(provider_id)

    def save_config(self, config: ProviderConfiguration) -> ProviderConfiguration:
        configs = {item.provider_id: item for item in self.list_configs()}
        configs[config.provider_id] = config
        self._write_json(self.config_path, {
            "schema": "verdant.providers.index.v1",
            "providers": [configs[key].model_dump(mode="json", by_alias=True) for key in sorted(configs)],
        })
        return config

    def list_capture_index(self) -> list[dict[str, Any]]:
        return list(json.loads(self.capture_index_path.read_text(encoding="utf-8")).get("captures", []))

    def register_capture_artifact(self, capture: ProviderCapture, artifact_sha256: str, size_bytes: int) -> dict[str, Any]:
        rows = self.list_capture_index()
        record = {
            "capture_id": capture.capture_id,
            "provider_id": capture.provider_id,
            "created_at": capture.created_at,
            "request_sha256": capture.request_sha256,
            "response_sha256": capture.response_sha256,
            "artifact_sha256": artifact_sha256,
            "artifact_size_bytes": size_bytes,
            "has_teaching_bundle": capture.parsed_teaching_bundle is not None,
            "parse_error": capture.parse_error,
        }
        rows.append(record)
        self._write_json(self.capture_index_path, {"schema": "verdant.provider-captures.index.v1", "captures": rows})
        return record

    @staticmethod
    def _parse_teaching_bundle(raw_response: str) -> tuple[dict[str, Any] | None, str | None]:
        try:
            value = json.loads(raw_response)
            bundle = EditableTeachingBundle.model_validate(value)
            return bundle.model_dump(mode="json", by_alias=True), None
        except Exception as exc:
            return None, str(exc)

    def capture_paste(self, provider_id: str, request: ProviderProposalRequest, raw_response: str) -> ProviderCapture:
        config = self.get_config(provider_id)
        if config.kind != "paste":
            raise ProviderError(f"Provider {provider_id} is not a paste provider.")
        return self._capture(config, request, raw_response, {"source": "manual_paste"})

    def propose_http(self, provider_id: str, request: ProviderProposalRequest) -> ProviderCapture:
        config = self.get_config(provider_id)
        if config.kind != "http_json":
            raise ProviderError(f"Provider {provider_id} is not an HTTP JSON provider.")
        if not config.enabled:
            raise ProviderError(f"Provider {provider_id} is disabled.")
        if not config.endpoint_url:
            raise ProviderError("HTTP provider requires endpoint_url.")
        body = {
            "model": config.model,
            "prompt": request.prompt,
            "system_prompt": request.system_prompt,
            "settings": request.settings,
            "expected_schema": request.expected_schema,
        }
        headers = {"Content-Type": "application/json", **config.extra_headers}
        if config.secret_env:
            secret = os.environ.get(config.secret_env)
            if not secret:
                raise ProviderError(f"Required provider secret environment variable {config.secret_env!r} is not set.")
            headers["Authorization"] = f"Bearer {secret}"
        req = urllib.request.Request(config.endpoint_url, data=_canonical_json_bytes(body), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=config.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                status = getattr(response, "status", None)
        except Exception as exc:
            raise ProviderError(f"Provider request failed: {exc}") from exc
        # Generic JSON providers may return {"output": "..."}; otherwise capture body as-is.
        try:
            obj = json.loads(raw)
            response_text = obj.get("output") if isinstance(obj, dict) and isinstance(obj.get("output"), str) else raw
        except Exception:
            response_text = raw
        return self._capture(config, request, response_text, {"source": "http_json", "http_status": status, "endpoint_url": config.endpoint_url, "model": config.model})

    def _capture(self, config: ProviderConfiguration, request: ProviderProposalRequest, raw_response: str, metadata: dict[str, Any]) -> ProviderCapture:
        request_payload = request.model_dump(mode="json")
        # No secret values are ever included here.
        request_payload["provider_configuration"] = {
            "provider_id": config.provider_id,
            "kind": config.kind,
            "model": config.model,
            "endpoint_url": config.endpoint_url,
            "secret_env": config.secret_env,
        }
        req_bytes = _canonical_json_bytes(request_payload)
        response_bytes = raw_response.encode("utf-8")
        parsed, parse_error = self._parse_teaching_bundle(raw_response)
        return ProviderCapture(
            capture_id=new_id("capture"),
            provider_id=config.provider_id,
            provider_kind=config.kind,
            created_at=utc_now_iso(),
            request_sha256=_sha256(req_bytes),
            response_sha256=_sha256(response_bytes),
            request=request_payload,
            raw_response=raw_response,
            parsed_teaching_bundle=parsed,
            parse_error=parse_error,
            provider_metadata=metadata,
        )


def build_provider_capture_package(capture: ProviderCapture) -> bytes:
    capture_json = _canonical_json_bytes(capture.model_dump(mode="json", by_alias=True))
    manifest = {
        "schema": PROVIDER_CAPTURE_SCHEMA_VERSION,
        "capture_id": capture.capture_id,
        "provider_id": capture.provider_id,
        "request_sha256": capture.request_sha256,
        "response_sha256": capture.response_sha256,
        "capture_json_sha256": _sha256(capture_json),
    }
    hashes = {
        "capture.json": _sha256(capture_json),
        "response.txt": _sha256(capture.raw_response.encode("utf-8")),
        "manifest.json": _sha256(_canonical_json_bytes(manifest)),
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", _canonical_json_bytes(manifest))
        zf.writestr("capture.json", capture_json)
        zf.writestr("response.txt", capture.raw_response.encode("utf-8"))
        zf.writestr("hashes.json", _canonical_json_bytes(hashes))
    return buf.getvalue()


def read_provider_capture_package(path: Path | str) -> ProviderCapture:
    with zipfile.ZipFile(path, "r") as zf:
        capture_bytes = zf.read("capture.json")
        hashes = json.loads(zf.read("hashes.json"))
        if _sha256(capture_bytes) != hashes["capture.json"]:
            raise ProviderError("Provider capture package failed capture.json integrity verification.")
        capture = ProviderCapture.model_validate_json(capture_bytes)
        response_bytes = zf.read("response.txt")
        if _sha256(response_bytes) != capture.response_sha256:
            raise ProviderError("Provider capture response hash mismatch.")
        return capture
