from __future__ import annotations

import json
import os

from fastapi.testclient import TestClient

from verdant_workbench import DurableRunService
from verdant_workbench.app import app, runtime
from verdant_workbench.curriculum import CurriculumCompileRequest
from verdant_workbench.providers import ProviderConfiguration, ProviderProposalRequest, read_provider_capture_package


def _bundle(service: DurableRunService) -> str:
    return service.editable_teaching_template()["source_text"]


def test_wb08_manual_external_llm_capture_is_immutable_replayable_and_compilable(tmp_path):
    service = DurableRunService(tmp_path / "provider")
    try:
        raw = _bundle(service)
        request = ProviderProposalRequest(prompt="Produce a Verdant editable teaching record.")
        result = service.capture_provider_paste("provider_paste", request, raw)
        record = result["record"] if "record" in result else result
        assert service.artifacts.verify(record["artifact_sha256"])
        detail = service.provider_capture_detail(record["capture_id"])
        assert detail["capture"]["raw_response"] == raw
        assert detail["capture"]["parsed_teaching_bundle"]["schema"] == "verdant.teaching.bundle.v1"
        source = service.provider_capture_curriculum_source(record["capture_id"])
        compiled = service.curriculum_compiler.compile(CurriculumCompileRequest(
            project_id="not-used-for-compile", title="Captured", source_format="teaching_bundle_json",
            source_text=source["source_text"], state_dim=128,
        ))
        assert compiled.item_count == 1
        # Replay reads the exact captured artifact; it does not call a provider.
        path = service.artifacts.resolve(record["artifact_sha256"], verify=True)
        replayed = read_provider_capture_package(path)
        assert replayed.response_sha256 == detail["capture"]["response_sha256"]
        assert replayed.raw_response == raw
    finally:
        service.close()


def test_wb08_secrets_are_referenced_by_name_and_never_persisted(tmp_path, monkeypatch):
    monkeypatch.setenv("VERDANT_TEST_PROVIDER_SECRET", "super-secret-value-never-store-me")
    service = DurableRunService(tmp_path / "secret")
    try:
        service.save_provider(ProviderConfiguration(
            provider_id="provider_http_test", display_name="HTTP Test", kind="http_json",
            endpoint_url="https://example.invalid/provider", model="fixture-model",
            secret_env="VERDANT_TEST_PROVIDER_SECRET",
        ))
        config_bytes = (service.root / "connections" / "providers.json").read_bytes()
        assert b"VERDANT_TEST_PROVIDER_SECRET" in config_bytes
        assert b"super-secret-value-never-store-me" not in config_bytes
        # A paste capture also must never accidentally inherit environment secrets.
        result = service.capture_provider_paste(
            "provider_paste", ProviderProposalRequest(prompt="test"), _bundle(service)
        )
        path = service.artifacts.resolve(result["artifact_sha256"], verify=True)
        assert b"super-secret-value-never-store-me" not in path.read_bytes()
    finally:
        service.close()


def test_wb08_invalid_provider_output_is_preserved_but_not_promoted_to_curriculum(tmp_path):
    service = DurableRunService(tmp_path / "invalid")
    try:
        result = service.capture_provider_paste(
            "provider_paste", ProviderProposalRequest(prompt="bad fixture"), "This is not a teaching bundle."
        )
        assert result["has_teaching_bundle"] is False
        assert result["parse_error"]
        detail = service.provider_capture_detail(result["capture_id"])
        assert detail["capture"]["raw_response"] == "This is not a teaching bundle."
        try:
            service.provider_capture_curriculum_source(result["capture_id"])
            raise AssertionError("invalid provider output unexpectedly became curriculum source")
        except Exception as exc:
            assert "valid editable teaching bundle" in str(exc)
    finally:
        service.close()


def test_wb08_api_supports_paste_capture_and_replay_source(tmp_path):
    runtime.reset(tmp_path / "api")
    client = TestClient(app)
    try:
        template = client.get("/api/v1/curricula/templates/editable-teaching-record").json()
        providers = client.get("/api/v1/providers")
        assert providers.status_code == 200
        assert any(item["provider_id"] == "provider_paste" for item in providers.json())
        captured = client.post("/api/v1/providers/provider_paste/capture-paste", json={
            "prompt": "Generate a curriculum", "raw_response": template["source_text"], "settings": {}
        })
        assert captured.status_code == 200, captured.text
        capture_id = captured.json()["capture_id"]
        source = client.get(f"/api/v1/provider-captures/{capture_id}/curriculum-source")
        assert source.status_code == 200
        assert source.json()["source_format"] == "teaching_bundle_json"
        package = client.get(f"/api/v1/provider-captures/{capture_id}/package")
        assert package.status_code == 200 and package.content[:2] == b"PK"
    finally:
        runtime.close()


def test_wb08_http_json_provider_calls_local_adapter_and_captures_without_secret(tmp_path, monkeypatch):
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    secret_seen = {"value": None}
    service = DurableRunService(tmp_path / "http-provider")
    raw_bundle = _bundle(service)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            secret_seen["value"] = self.headers.get("Authorization")
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            assert body["expected_schema"] == "verdant.teaching.bundle.v1"
            payload = json.dumps({"output": raw_bundle}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("VERDANT_LOCAL_PROVIDER_SECRET", "ephemeral-test-secret")
    try:
        service.save_provider(ProviderConfiguration(
            provider_id="provider_local_http", display_name="Local HTTP", kind="http_json",
            endpoint_url=f"http://127.0.0.1:{server.server_port}/", model="local-fixture",
            secret_env="VERDANT_LOCAL_PROVIDER_SECRET", timeout_seconds=5,
        ))
        result = service.call_provider("provider_local_http", ProviderProposalRequest(prompt="make bundle"))
        assert result["has_teaching_bundle"] is True
        assert secret_seen["value"] == "Bearer ephemeral-test-secret"
        path = service.artifacts.resolve(result["artifact_sha256"], verify=True)
        assert b"ephemeral-test-secret" not in path.read_bytes()
        detail = service.provider_capture_detail(result["capture_id"])
        assert detail["capture"]["request"]["provider_configuration"]["secret_env"] == "VERDANT_LOCAL_PROVIDER_SECRET"
    finally:
        server.shutdown(); server.server_close(); service.close()
