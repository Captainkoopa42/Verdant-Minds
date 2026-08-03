from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from verdant_workbench.curriculum import CurriculumCompileRequest
from verdant_workbench.providers import ProviderConfiguration, ProviderProposalRequest
from verdant_workbench.run_service import DurableRunService

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "workbench" / "artifacts" / "wb08_provider_connections_proof.json"
HOME = ROOT / "workbench" / "artifacts" / "_wb08_proof_home"
if HOME.exists():
    shutil.rmtree(HOME)
service = DurableRunService(HOME)
raw_bundle = service.editable_teaching_template()["source_text"]
secret_seen = {"value": None}

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        secret_seen["value"] = self.headers.get("Authorization")
        n = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(n) or b"{}")
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
os.environ["VERDANT_WB08_PROOF_SECRET"] = "wb08-ephemeral-secret"
try:
    project = service.create_project("WB08 Proof", project_id="proj_wb08_proof")
    manual = service.capture_provider_paste(
        "provider_paste",
        ProviderProposalRequest(prompt="Create an editable Verdant teaching record."),
        raw_bundle,
    )
    manual_source = service.provider_capture_curriculum_source(manual["capture_id"])
    manual_compiled = service.curriculum_compiler.compile(CurriculumCompileRequest(
        project_id=project.project_id,
        title="WB08 Manual Capture",
        source_format="teaching_bundle_json",
        source_text=manual_source["source_text"],
        state_dim=128,
    ))
    service.save_provider(ProviderConfiguration(
        provider_id="provider_wb08_local_http",
        display_name="WB08 local fixture",
        kind="http_json",
        endpoint_url=f"http://127.0.0.1:{server.server_port}/",
        model="fixture-model",
        secret_env="VERDANT_WB08_PROOF_SECRET",
        timeout_seconds=5,
    ))
    http_capture = service.call_provider(
        "provider_wb08_local_http",
        ProviderProposalRequest(prompt="Create the same editable record through HTTP."),
    )
    http_detail = service.provider_capture_detail(http_capture["capture_id"])
    artifact_path = service.artifacts.resolve(http_capture["artifact_sha256"], verify=True)
    package_bytes = artifact_path.read_bytes()
    proof = {
        "schema": "verdant.workbench.wb08-proof.v1",
        "manual_capture": {
            "capture_id": manual["capture_id"],
            "artifact_sha256": manual["artifact_sha256"],
            "response_sha256": manual["response_sha256"],
            "valid_teaching_bundle": manual["has_teaching_bundle"],
            "compiled_item_count": manual_compiled.item_count,
            "compiled_sha256": manual_compiled.compiled_sha256,
        },
        "http_capture": {
            "capture_id": http_capture["capture_id"],
            "artifact_sha256": http_capture["artifact_sha256"],
            "valid_teaching_bundle": http_capture["has_teaching_bundle"],
            "authorization_header_seen_by_fixture": secret_seen["value"] == "Bearer wb08-ephemeral-secret",
            "secret_value_present_in_artifact": b"wb08-ephemeral-secret" in package_bytes,
            "secret_reference_name": http_detail["capture"]["request"]["provider_configuration"]["secret_env"],
        },
        "provider_count": len(service.list_providers()),
        "capture_count": len(service.list_provider_captures()),
    }
    proof["all_gates_pass"] = all([
        proof["manual_capture"]["valid_teaching_bundle"],
        proof["manual_capture"]["compiled_item_count"] == 1,
        proof["http_capture"]["valid_teaching_bundle"],
        proof["http_capture"]["authorization_header_seen_by_fixture"],
        not proof["http_capture"]["secret_value_present_in_artifact"],
        proof["http_capture"]["secret_reference_name"] == "VERDANT_WB08_PROOF_SECRET",
    ])
    OUT.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(proof, indent=2, sort_keys=True))
finally:
    server.shutdown(); server.server_close(); service.close()
