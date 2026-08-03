from __future__ import annotations

from pathlib import Path

import pytest

from verdant_workbench import (
    ArtifactIntegrityError,
    ContentAddressedArtifactStore,
    DurableRunService,
    OrganismConfig,
    TeachingRequest,
)


def test_content_addressed_artifact_store_deduplicates_and_detects_tampering(tmp_path):
    store = ContentAddressedArtifactStore(tmp_path / "store")
    source_a = tmp_path / "a.bin"
    source_b = tmp_path / "b.bin"
    source_a.write_bytes(b"verdant-checkpoint")
    source_b.write_bytes(b"verdant-checkpoint")

    first = store.ingest_file(source_a)
    second = store.ingest_file(source_b)
    assert first.sha256 == second.sha256
    assert first.path == second.path

    stored_path = Path(first.path)
    stored_path.write_bytes(b"tampered")
    with pytest.raises(ArtifactIntegrityError):
        store.resolve(first.sha256, verify=True)


def test_wb02_create_save_close_reopen_preserves_checkpoint_and_events(tmp_path):
    home = tmp_path / "lab"
    service = DurableRunService(home)
    try:
        project = service.create_project("Persistence Lab", project_id="proj_persist")
        descriptor = service.create_run(
            project.project_id,
            OrganismConfig(seed=1901, state_dim=16, run_label="wb02-persist"),
            organism_id="org_persist",
            run_id="run_persist",
        )
        receipt = service.teach(
            descriptor["run_id"],
            TeachingRequest(context_id="world-a", labels=("kren", "tar"), event_key="persist-001"),
            expected_state_revision=descriptor["state_revision"],
            command_id="cmd_persist_001",
        )
        assert receipt["events"]
        checkpoint = service.save_checkpoint("run_persist", label="after-first-teach", checkpoint_id="ckpt_persist")
        checkpoint_path = service.checkpoint_path(checkpoint.checkpoint_id)
        checkpoint_bytes = checkpoint_path.read_bytes()
        event_ids_before = [item.event_id for item in service.events.read_run("run_persist")]
        service.close_run("run_persist")
        expected_fingerprint = checkpoint.canonical_fingerprint
        expected_sha = checkpoint.artifact_sha256
    finally:
        service.close()

    reopened = DurableRunService(home)
    try:
        verified = reopened.verify_checkpoint("ckpt_persist")
        assert verified.artifact_sha256 == expected_sha
        assert reopened.checkpoint_path("ckpt_persist").read_bytes() == checkpoint_bytes
        descriptor_2 = reopened.reopen_run("run_persist")
        assert descriptor_2["fingerprint"] == expected_fingerprint
        assert reopened.repository.get_run("run_persist").status == "active"
        assert [item.event_id for item in reopened.events.read_run("run_persist")] == event_ids_before
        assert len(reopened.repository.list_event_index("run_persist")) == len(event_ids_before)
    finally:
        reopened.close()


def test_wb02_branch_preserves_ancestry_and_parent_checkpoint(tmp_path):
    service = DurableRunService(tmp_path / "branch-lab")
    try:
        project = service.create_project("Branch Lab", project_id="proj_branch")
        descriptor = service.create_run(
            project.project_id,
            OrganismConfig(seed=77, state_dim=8, run_label="branch-root"),
            organism_id="org_branch",
            run_id="run_root",
        )
        service.teach(
            "run_root",
            TeachingRequest(context_id="root", labels=("a", "b"), event_key="root-001"),
            expected_state_revision=descriptor["state_revision"],
            command_id="cmd_root_001",
        )
        parent_checkpoint = service.save_checkpoint("run_root", checkpoint_id="ckpt_root")
        parent_bytes = service.checkpoint_path("ckpt_root").read_bytes()
        branch_descriptor = service.branch_from_checkpoint("ckpt_root", new_run_id="run_child")
        assert branch_descriptor["fingerprint"] == parent_checkpoint.canonical_fingerprint
        ancestry = service.ancestry("run_child")
        assert [item["run_id"] for item in ancestry] == ["run_root", "run_child"]
        child_record = service.repository.get_run("run_child")
        assert child_record.parent_run_id == "run_root"
        assert child_record.parent_checkpoint_id == "ckpt_root"

        service.teach(
            "run_child",
            TeachingRequest(context_id="child", labels=("c",), event_key="child-001"),
            expected_state_revision=branch_descriptor["state_revision"],
            command_id="cmd_child_001",
        )
        child_checkpoint = service.save_checkpoint("run_child", checkpoint_id="ckpt_child")
        assert child_checkpoint.canonical_fingerprint != parent_checkpoint.canonical_fingerprint
        assert service.checkpoint_path("ckpt_root").read_bytes() == parent_bytes
        assert service.repository.get_checkpoint("ckpt_child").parent_checkpoint_id == "ckpt_root"
    finally:
        service.close()


def test_wb02_checkpoint_integrity_blocks_reopen(tmp_path):
    service = DurableRunService(tmp_path / "integrity-lab")
    try:
        project = service.create_project("Integrity Lab", project_id="proj_integrity")
        service.create_run(
            project.project_id,
            OrganismConfig(seed=5, state_dim=8, run_label="integrity"),
            organism_id="org_integrity",
            run_id="run_integrity",
        )
        checkpoint = service.save_checkpoint("run_integrity", checkpoint_id="ckpt_integrity")
        service.close_run("run_integrity")
        path = service.checkpoint_path(checkpoint.checkpoint_id)
        path.write_bytes(path.read_bytes() + b"tamper")
        with pytest.raises(ArtifactIntegrityError):
            service.reopen_run("run_integrity")
    finally:
        service.close()
