from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .version import COMMAND_SCHEMA_VERSION, EVENT_SCHEMA_VERSION, SNAPSHOT_SCHEMA_VERSION


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, serialize_by_alias=True)


class ActorKind(str, Enum):
    HUMAN = "human"
    API = "api"
    TEST = "test"
    SYSTEM = "system"


class CommandEnvelope(FrozenModel):
    schema_id: Literal[COMMAND_SCHEMA_VERSION] = Field(default=COMMAND_SCHEMA_VERSION, alias="schema", serialization_alias="schema")
    command_id: str = Field(default_factory=lambda: new_id("cmd"))
    run_id: str
    organism_id: str
    command_type: str
    expected_state_revision: int | None = Field(default=None, ge=0)
    issued_at: str = Field(default_factory=utc_now_iso)
    actor: ActorKind = ActorKind.API
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("run_id", "organism_id", "command_type")
    @classmethod
    def nonempty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Command identity fields cannot be empty.")
        return value


class EventEnvelope(FrozenModel):
    schema_id: Literal[EVENT_SCHEMA_VERSION] = Field(default=EVENT_SCHEMA_VERSION, alias="schema", serialization_alias="schema")
    event_id: str
    run_id: str
    organism_id: str
    engine_cycle: int = Field(ge=0)
    state_revision: int = Field(ge=0)
    event_type: str
    source_command_id: str
    timestamp_utc: str = Field(default_factory=utc_now_iso)
    payload: dict[str, Any] = Field(default_factory=dict)
    payload_sha256: str


class OrganismConfig(FrozenModel):
    seed: int = 7741
    state_dim: int = Field(default=128, ge=1)
    run_label: str = "verdant-workbench"


class OrganismDescriptor(FrozenModel):
    organism_id: str
    run_id: str
    kernel_id: str
    seed: int
    state_dim: int
    run_label: str
    cycle: int
    state_revision: int
    fingerprint: str


class CommandReceipt(FrozenModel):
    command_id: str
    command_type: str
    organism_id: str
    run_id: str
    state_revision_before: int
    state_revision_after: int
    cycle_before: int
    cycle_after: int
    fingerprint_before: str
    fingerprint_after: str
    replayed: bool = False
    events: tuple[EventEnvelope, ...] = ()
    result: dict[str, Any] = Field(default_factory=dict)


class TeachingRequest(FrozenModel):
    context_id: str
    labels: tuple[str, ...] = Field(min_length=1)
    feature_vector: tuple[float, ...] | None = None
    event_key: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ProbeRequest(FrozenModel):
    cue_labels: tuple[str, ...] = Field(min_length=1)


class GrammarPreviewRequest(FrozenModel):
    sentence: str = Field(min_length=1)
    event_key: str = "workbench-grammar-preview"


class GrammarRuleTeachRequest(FrozenModel):
    rule_id: str
    event_key: str | None = None


class LexemeTeachRequest(FrozenModel):
    lemma: str
    category: str
    forms: tuple[str, ...] = Field(min_length=1)
    attributes: dict[str, Any] = Field(default_factory=dict)
    event_key: str | None = None


class LanguageSentenceTeachRequest(FrozenModel):
    sentence: str = Field(min_length=1)
    event_key: str


class SnapshotScope(str, Enum):
    SUMMARY = "summary"
    WORKSPACE = "workspace"
    STRUCTURES = "structures"
    FULL_DEBUG = "full_debug"


class Snapshot(FrozenModel):
    schema_id: Literal[SNAPSHOT_SCHEMA_VERSION] = Field(default=SNAPSHOT_SCHEMA_VERSION, alias="schema", serialization_alias="schema")
    organism_id: str
    run_id: str
    scope: SnapshotScope
    engine_cycle: int
    state_revision: int
    fingerprint: str
    payload: dict[str, Any]


class CheckpointDescriptor(FrozenModel):
    path: str
    checkpoint_sha256: str
    canonical_fingerprint: str
    state_revision: int
    cycle: int


class WorkerRequest(FrozenModel):
    request_id: str = Field(default_factory=lambda: new_id("req"))
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)


class WorkerResponse(FrozenModel):
    request_id: str
    ok: bool
    payload: dict[str, Any] = Field(default_factory=dict)
    error_type: str | None = None
    error_message: str | None = None
