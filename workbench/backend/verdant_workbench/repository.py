from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Iterable

from .models import EventEnvelope, utc_now_iso


@dataclass(frozen=True)
class ProjectRecord:
    project_id: str
    name: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class OrganismRecord:
    organism_id: str
    project_id: str
    seed: int
    state_dim: int
    run_label: str
    created_at: str


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    project_id: str
    organism_id: str
    status: str
    created_at: str
    updated_at: str
    parent_run_id: str | None
    parent_checkpoint_id: str | None
    head_checkpoint_id: str | None
    latest_state_revision: int
    latest_cycle: int
    latest_fingerprint: str


@dataclass(frozen=True)
class CheckpointRecord:
    checkpoint_id: str
    run_id: str
    organism_id: str
    artifact_sha256: str
    artifact_size_bytes: int
    canonical_fingerprint: str
    state_revision: int
    cycle: int
    created_at: str
    parent_checkpoint_id: str | None
    label: str | None


@dataclass(frozen=True)
class CurriculumRecord:
    curriculum_id: str
    project_id: str
    title: str
    version: int
    source_format: str
    source_sha256: str
    compiled_sha256: str
    artifact_sha256: str
    artifact_size_bytes: int
    item_count: int
    state_dim: int
    compiler_version: str
    created_at: str


@dataclass(frozen=True)
class ExperimentRecord:
    experiment_id: str
    project_id: str
    title: str
    version: int
    protocol_id: str
    manifest_sha256: str
    artifact_sha256: str
    artifact_size_bytes: int
    parent_experiment_id: str | None
    created_at: str


@dataclass(frozen=True)
class ExperimentRunRecord:
    experiment_run_id: str
    experiment_id: str
    status: str
    started_at: str
    completed_at: str | None
    result_artifact_sha256: str | None
    result_artifact_size_bytes: int | None
    scientific_result_sha256: str | None
    assertions_passed: int
    assertions_total: int
    verified: int
    error_message: str | None


@dataclass(frozen=True)
class QueueItemRecord:
    queue_item_id: str
    run_id: str
    sequence_no: int
    command_type: str
    payload_json: str
    status: str
    created_at: str
    started_at: str | None
    completed_at: str | None
    result_json: str | None
    error_message: str | None

    def payload(self) -> dict[str, Any]:
        return json.loads(self.payload_json)

    def result(self) -> dict[str, Any] | None:
        return None if self.result_json is None else json.loads(self.result_json)


class WorkbenchRepository:
    """SQLite metadata/index store. Never stores authoritative cognitive state."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = FULL")
        self._init_schema()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def recover_stale_active_runs(self) -> int:
        """Mark run rows left active by a previous crashed Workbench process as closed.

        Canonical state is not altered; a user may explicitly reopen from the last
        verified checkpoint. Workbench is single-writer per home directory.
        """
        with self._lock:
            cursor = self._conn.execute(
                "UPDATE runs SET status='closed', updated_at=? WHERE status='active'",
                (utc_now_iso(),),
            )
            self._conn.commit()
            return int(cursor.rowcount)

    def _init_schema(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS projects (
            project_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS organisms (
            organism_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(project_id),
            seed INTEGER NOT NULL,
            state_dim INTEGER NOT NULL,
            run_label TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(project_id),
            organism_id TEXT NOT NULL REFERENCES organisms(organism_id),
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            parent_run_id TEXT REFERENCES runs(run_id),
            parent_checkpoint_id TEXT,
            head_checkpoint_id TEXT,
            latest_state_revision INTEGER NOT NULL DEFAULT 0,
            latest_cycle INTEGER NOT NULL DEFAULT 0,
            latest_fingerprint TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS checkpoints (
            checkpoint_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES runs(run_id),
            organism_id TEXT NOT NULL REFERENCES organisms(organism_id),
            artifact_sha256 TEXT NOT NULL,
            artifact_size_bytes INTEGER NOT NULL,
            canonical_fingerprint TEXT NOT NULL,
            state_revision INTEGER NOT NULL,
            cycle INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            parent_checkpoint_id TEXT REFERENCES checkpoints(checkpoint_id),
            label TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_checkpoints_run ON checkpoints(run_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_checkpoints_sha ON checkpoints(artifact_sha256);
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES runs(run_id),
            organism_id TEXT NOT NULL REFERENCES organisms(organism_id),
            engine_cycle INTEGER NOT NULL,
            state_revision INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            source_command_id TEXT NOT NULL,
            timestamp_utc TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            ledger_path TEXT NOT NULL,
            byte_offset INTEGER NOT NULL,
            byte_length INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_events_run_revision ON events(run_id, state_revision, engine_cycle);
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(run_id, event_type);
        CREATE TABLE IF NOT EXISTS run_queue (
            queue_item_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES runs(run_id),
            sequence_no INTEGER NOT NULL,
            command_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            result_json TEXT,
            error_message TEXT,
            UNIQUE(run_id, sequence_no)
        );
        CREATE INDEX IF NOT EXISTS idx_run_queue_status ON run_queue(run_id, status, sequence_no);
        CREATE TABLE IF NOT EXISTS curricula (
            curriculum_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(project_id),
            title TEXT NOT NULL,
            version INTEGER NOT NULL,
            source_format TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            compiled_sha256 TEXT NOT NULL,
            artifact_sha256 TEXT NOT NULL,
            artifact_size_bytes INTEGER NOT NULL,
            item_count INTEGER NOT NULL,
            state_dim INTEGER NOT NULL,
            compiler_version TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(project_id, title, version)
        );
        CREATE INDEX IF NOT EXISTS idx_curricula_project ON curricula(project_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_curricula_compiled_sha ON curricula(compiled_sha256);
        CREATE TABLE IF NOT EXISTS experiments (
            experiment_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(project_id),
            title TEXT NOT NULL,
            version INTEGER NOT NULL,
            protocol_id TEXT NOT NULL,
            manifest_sha256 TEXT NOT NULL,
            artifact_sha256 TEXT NOT NULL,
            artifact_size_bytes INTEGER NOT NULL,
            parent_experiment_id TEXT REFERENCES experiments(experiment_id),
            created_at TEXT NOT NULL,
            UNIQUE(project_id, title, version)
        );
        CREATE INDEX IF NOT EXISTS idx_experiments_project ON experiments(project_id, created_at);
        CREATE TABLE IF NOT EXISTS experiment_runs (
            experiment_run_id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL REFERENCES experiments(experiment_id),
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            result_artifact_sha256 TEXT,
            result_artifact_size_bytes INTEGER,
            scientific_result_sha256 TEXT,
            assertions_passed INTEGER NOT NULL DEFAULT 0,
            assertions_total INTEGER NOT NULL DEFAULT 0,
            verified INTEGER NOT NULL DEFAULT 0,
            error_message TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_experiment_runs_experiment ON experiment_runs(experiment_id, started_at);
        """
        with self._lock, self._conn:
            self._conn.executescript(schema)

    def create_project(self, project_id: str, name: str) -> ProjectRecord:
        now = utc_now_iso()
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO projects(project_id,name,created_at,updated_at) VALUES(?,?,?,?)",
                (project_id, name, now, now),
            )
        return ProjectRecord(project_id, name, now, now)

    def get_project(self, project_id: str) -> ProjectRecord:
        row = self._one("SELECT * FROM projects WHERE project_id=?", (project_id,))
        return ProjectRecord(**dict(row))

    def list_projects(self) -> list[ProjectRecord]:
        return [ProjectRecord(**dict(row)) for row in self._all("SELECT * FROM projects ORDER BY created_at")]

    def create_organism(self, *, organism_id: str, project_id: str, seed: int, state_dim: int, run_label: str) -> OrganismRecord:
        now = utc_now_iso()
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO organisms(organism_id,project_id,seed,state_dim,run_label,created_at) VALUES(?,?,?,?,?,?)",
                (organism_id, project_id, seed, state_dim, run_label, now),
            )
        return OrganismRecord(organism_id, project_id, seed, state_dim, run_label, now)

    def get_organism(self, organism_id: str) -> OrganismRecord:
        row = self._one("SELECT * FROM organisms WHERE organism_id=?", (organism_id,))
        return OrganismRecord(**dict(row))

    def create_run(
        self,
        *,
        run_id: str,
        project_id: str,
        organism_id: str,
        status: str,
        latest_state_revision: int,
        latest_cycle: int,
        latest_fingerprint: str,
        parent_run_id: str | None = None,
        parent_checkpoint_id: str | None = None,
        head_checkpoint_id: str | None = None,
    ) -> RunRecord:
        now = utc_now_iso()
        with self._lock, self._conn:
            self._conn.execute(
                """INSERT INTO runs(
                    run_id,project_id,organism_id,status,created_at,updated_at,parent_run_id,parent_checkpoint_id,
                    head_checkpoint_id,latest_state_revision,latest_cycle,latest_fingerprint
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (run_id, project_id, organism_id, status, now, now, parent_run_id, parent_checkpoint_id,
                 head_checkpoint_id, latest_state_revision, latest_cycle, latest_fingerprint),
            )
        return self.get_run(run_id)

    def get_run(self, run_id: str) -> RunRecord:
        row = self._one("SELECT * FROM runs WHERE run_id=?", (run_id,))
        return RunRecord(**dict(row))

    def list_runs(self, project_id: str | None = None) -> list[RunRecord]:
        if project_id is None:
            rows = self._all("SELECT * FROM runs ORDER BY created_at")
        else:
            rows = self._all("SELECT * FROM runs WHERE project_id=? ORDER BY created_at", (project_id,))
        return [RunRecord(**dict(row)) for row in rows]

    def update_run_head(
        self,
        run_id: str,
        *,
        state_revision: int,
        cycle: int,
        fingerprint: str,
        status: str | None = None,
        head_checkpoint_id: str | None = None,
    ) -> RunRecord:
        current = self.get_run(run_id)
        new_status = status or current.status
        new_head = head_checkpoint_id if head_checkpoint_id is not None else current.head_checkpoint_id
        now = utc_now_iso()
        with self._lock, self._conn:
            self._conn.execute(
                """UPDATE runs SET status=?, updated_at=?, head_checkpoint_id=?, latest_state_revision=?,
                   latest_cycle=?, latest_fingerprint=? WHERE run_id=?""",
                (new_status, now, new_head, state_revision, cycle, fingerprint, run_id),
            )
        return self.get_run(run_id)

    def set_run_status(self, run_id: str, status: str) -> RunRecord:
        current = self.get_run(run_id)
        return self.update_run_head(
            run_id,
            state_revision=current.latest_state_revision,
            cycle=current.latest_cycle,
            fingerprint=current.latest_fingerprint,
            status=status,
        )

    def add_checkpoint(self, record: CheckpointRecord) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """INSERT INTO checkpoints(
                   checkpoint_id,run_id,organism_id,artifact_sha256,artifact_size_bytes,canonical_fingerprint,
                   state_revision,cycle,created_at,parent_checkpoint_id,label
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (record.checkpoint_id, record.run_id, record.organism_id, record.artifact_sha256,
                 record.artifact_size_bytes, record.canonical_fingerprint, record.state_revision, record.cycle,
                 record.created_at, record.parent_checkpoint_id, record.label),
            )

    def get_checkpoint(self, checkpoint_id: str) -> CheckpointRecord:
        row = self._one("SELECT * FROM checkpoints WHERE checkpoint_id=?", (checkpoint_id,))
        return CheckpointRecord(**dict(row))

    def list_checkpoints(self, run_id: str) -> list[CheckpointRecord]:
        return [CheckpointRecord(**dict(row)) for row in self._all(
            "SELECT * FROM checkpoints WHERE run_id=? ORDER BY created_at", (run_id,)
        )]

    def next_curriculum_version(self, project_id: str, title: str) -> int:
        self.get_project(project_id)
        rows = self._all(
            "SELECT COALESCE(MAX(version),0) AS n FROM curricula WHERE project_id=? AND title=?",
            (project_id, title),
        )
        return int(rows[0]["n"]) + 1

    def add_curriculum(self, record: CurriculumRecord) -> CurriculumRecord:
        self.get_project(record.project_id)
        with self._lock, self._conn:
            self._conn.execute(
                """INSERT INTO curricula(
                    curriculum_id,project_id,title,version,source_format,source_sha256,compiled_sha256,
                    artifact_sha256,artifact_size_bytes,item_count,state_dim,compiler_version,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (record.curriculum_id, record.project_id, record.title, record.version, record.source_format,
                 record.source_sha256, record.compiled_sha256, record.artifact_sha256, record.artifact_size_bytes,
                 record.item_count, record.state_dim, record.compiler_version, record.created_at),
            )
        return self.get_curriculum(record.curriculum_id)

    def get_curriculum(self, curriculum_id: str) -> CurriculumRecord:
        row = self._one("SELECT * FROM curricula WHERE curriculum_id=?", (curriculum_id,))
        return CurriculumRecord(**dict(row))

    def list_curricula(self, project_id: str | None = None) -> list[CurriculumRecord]:
        if project_id is None:
            rows = self._all("SELECT * FROM curricula ORDER BY created_at")
        else:
            self.get_project(project_id)
            rows = self._all("SELECT * FROM curricula WHERE project_id=? ORDER BY created_at", (project_id,))
        return [CurriculumRecord(**dict(row)) for row in rows]

    def next_experiment_version(self, project_id: str, title: str) -> int:
        self.get_project(project_id)
        rows = self._all(
            "SELECT COALESCE(MAX(version),0) AS n FROM experiments WHERE project_id=? AND title=?",
            (project_id, title),
        )
        return int(rows[0]["n"]) + 1

    def add_experiment(self, record: ExperimentRecord) -> ExperimentRecord:
        self.get_project(record.project_id)
        if record.parent_experiment_id is not None:
            self.get_experiment(record.parent_experiment_id)
        with self._lock, self._conn:
            self._conn.execute(
                """INSERT INTO experiments(
                    experiment_id,project_id,title,version,protocol_id,manifest_sha256,artifact_sha256,
                    artifact_size_bytes,parent_experiment_id,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (record.experiment_id, record.project_id, record.title, record.version, record.protocol_id,
                 record.manifest_sha256, record.artifact_sha256, record.artifact_size_bytes,
                 record.parent_experiment_id, record.created_at),
            )
        return self.get_experiment(record.experiment_id)

    def get_experiment(self, experiment_id: str) -> ExperimentRecord:
        row = self._one("SELECT * FROM experiments WHERE experiment_id=?", (experiment_id,))
        return ExperimentRecord(**dict(row))

    def list_experiments(self, project_id: str | None = None) -> list[ExperimentRecord]:
        if project_id is None:
            rows = self._all("SELECT * FROM experiments ORDER BY created_at")
        else:
            self.get_project(project_id)
            rows = self._all("SELECT * FROM experiments WHERE project_id=? ORDER BY created_at", (project_id,))
        return [ExperimentRecord(**dict(row)) for row in rows]

    def add_experiment_run(self, record: ExperimentRunRecord) -> ExperimentRunRecord:
        self.get_experiment(record.experiment_id)
        with self._lock, self._conn:
            self._conn.execute(
                """INSERT INTO experiment_runs(
                    experiment_run_id,experiment_id,status,started_at,completed_at,result_artifact_sha256,
                    result_artifact_size_bytes,scientific_result_sha256,assertions_passed,assertions_total,
                    verified,error_message
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (record.experiment_run_id, record.experiment_id, record.status, record.started_at, record.completed_at,
                 record.result_artifact_sha256, record.result_artifact_size_bytes, record.scientific_result_sha256,
                 record.assertions_passed, record.assertions_total, record.verified, record.error_message),
            )
        return self.get_experiment_run(record.experiment_run_id)

    def update_experiment_run(self, experiment_run_id: str, **updates: Any) -> ExperimentRunRecord:
        allowed = {
            "status", "completed_at", "result_artifact_sha256", "result_artifact_size_bytes",
            "scientific_result_sha256", "assertions_passed", "assertions_total", "verified", "error_message"
        }
        fields = {k: v for k, v in updates.items() if k in allowed}
        if not fields:
            return self.get_experiment_run(experiment_run_id)
        with self._lock, self._conn:
            assignments = ",".join(f"{key}=?" for key in fields)
            self._conn.execute(
                f"UPDATE experiment_runs SET {assignments} WHERE experiment_run_id=?",
                (*fields.values(), experiment_run_id),
            )
        return self.get_experiment_run(experiment_run_id)

    def get_experiment_run(self, experiment_run_id: str) -> ExperimentRunRecord:
        row = self._one("SELECT * FROM experiment_runs WHERE experiment_run_id=?", (experiment_run_id,))
        return ExperimentRunRecord(**dict(row))

    def list_experiment_runs(self, experiment_id: str) -> list[ExperimentRunRecord]:
        self.get_experiment(experiment_id)
        rows = self._all(
            "SELECT * FROM experiment_runs WHERE experiment_id=? ORDER BY started_at", (experiment_id,)
        )
        return [ExperimentRunRecord(**dict(row)) for row in rows]

    def enqueue_command(self, *, queue_item_id: str, run_id: str, command_type: str, payload: dict[str, Any]) -> QueueItemRecord:
        self.get_run(run_id)
        now = utc_now_iso()
        with self._lock, self._conn:
            row = self._conn.execute("SELECT COALESCE(MAX(sequence_no),0) AS n FROM run_queue WHERE run_id=?", (run_id,)).fetchone()
            sequence_no = int(row["n"]) + 1
            self._conn.execute(
                """INSERT INTO run_queue(queue_item_id,run_id,sequence_no,command_type,payload_json,status,created_at)
                   VALUES(?,?,?,?,?,?,?)""",
                (queue_item_id, run_id, sequence_no, command_type, json.dumps(payload, sort_keys=True, separators=(",", ":")), "queued", now),
            )
        return self.get_queue_item(queue_item_id)

    def get_queue_item(self, queue_item_id: str) -> QueueItemRecord:
        row = self._one("SELECT * FROM run_queue WHERE queue_item_id=?", (queue_item_id,))
        return QueueItemRecord(**dict(row))

    def list_queue(self, run_id: str, *, include_terminal: bool = True) -> list[QueueItemRecord]:
        self.get_run(run_id)
        if include_terminal:
            rows = self._all("SELECT * FROM run_queue WHERE run_id=? ORDER BY sequence_no", (run_id,))
        else:
            rows = self._all("SELECT * FROM run_queue WHERE run_id=? AND status IN ('queued','running') ORDER BY sequence_no", (run_id,))
        return [QueueItemRecord(**dict(row)) for row in rows]

    def next_queued(self, run_id: str) -> QueueItemRecord | None:
        rows = self._all("SELECT * FROM run_queue WHERE run_id=? AND status='queued' ORDER BY sequence_no LIMIT 1", (run_id,))
        return None if not rows else QueueItemRecord(**dict(rows[0]))

    def mark_queue_running(self, queue_item_id: str) -> QueueItemRecord:
        now = utc_now_iso()
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE run_queue SET status='running', started_at=?, error_message=NULL WHERE queue_item_id=? AND status='queued'",
                (now, queue_item_id),
            )
        return self.get_queue_item(queue_item_id)

    def mark_queue_completed(self, queue_item_id: str, result: dict[str, Any]) -> QueueItemRecord:
        now = utc_now_iso()
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE run_queue SET status='completed', completed_at=?, result_json=?, error_message=NULL WHERE queue_item_id=?",
                (now, json.dumps(result, sort_keys=True, separators=(",", ":")), queue_item_id),
            )
        return self.get_queue_item(queue_item_id)

    def mark_queue_failed(self, queue_item_id: str, error_message: str) -> QueueItemRecord:
        now = utc_now_iso()
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE run_queue SET status='failed', completed_at=?, error_message=? WHERE queue_item_id=?",
                (now, error_message, queue_item_id),
            )
        return self.get_queue_item(queue_item_id)

    def requeue_running_items(self, run_id: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE run_queue SET status='queued', started_at=NULL WHERE run_id=? AND status='running'",
                (run_id,),
            )

    def queue_counts(self, run_id: str) -> dict[str, int]:
        rows = self._all("SELECT status, COUNT(*) AS n FROM run_queue WHERE run_id=? GROUP BY status", (run_id,))
        result = {str(row['status']): int(row['n']) for row in rows}
        result['total'] = sum(result.values())
        return result

    def add_event_index(self, event: EventEnvelope, *, ledger_path: str, byte_offset: int, byte_length: int) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """INSERT OR IGNORE INTO events(
                   event_id,run_id,organism_id,engine_cycle,state_revision,event_type,source_command_id,
                   timestamp_utc,payload_sha256,ledger_path,byte_offset,byte_length
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (event.event_id, event.run_id, event.organism_id, event.engine_cycle, event.state_revision,
                 event.event_type, event.source_command_id, event.timestamp_utc, event.payload_sha256,
                 ledger_path, byte_offset, byte_length),
            )

    def list_event_index(self, run_id: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self._all(
            "SELECT rowid AS event_cursor, * FROM events WHERE run_id=? ORDER BY rowid",
            (run_id,),
        )]

    def list_event_index_after(self, run_id: str, cursor: int = 0, *, limit: int = 250) -> list[dict[str, Any]]:
        return [dict(row) for row in self._all(
            "SELECT rowid AS event_cursor, * FROM events WHERE run_id=? AND rowid>? ORDER BY rowid LIMIT ?",
            (run_id, int(cursor), int(limit)),
        )]

    def ancestry(self, run_id: str) -> list[RunRecord]:
        result: list[RunRecord] = []
        seen: set[str] = set()
        current = self.get_run(run_id)
        while True:
            if current.run_id in seen:
                raise RuntimeError("Run ancestry cycle detected.")
            seen.add(current.run_id)
            result.append(current)
            if current.parent_run_id is None:
                break
            current = self.get_run(current.parent_run_id)
        result.reverse()
        return result

    def _one(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row:
        with self._lock:
            row = self._conn.execute(sql, params).fetchone()
        if row is None:
            raise KeyError(params[0] if params else sql)
        return row

    def _all(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._conn.execute(sql, params).fetchall())


class AppendOnlyEventLedger:
    """Durable JSONL event ledger with byte offsets indexed in SQLite."""

    def __init__(self, root: Path | str, repository: WorkbenchRepository) -> None:
        self.root = Path(root)
        self.repository = repository
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def path_for_run(self, run_id: str) -> Path:
        path = self.root / run_id / "events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def append(self, events: Iterable[EventEnvelope]) -> None:
        by_run: dict[str, list[EventEnvelope]] = {}
        for event in events:
            by_run.setdefault(event.run_id, []).append(event)
        for run_id, group in by_run.items():
            path = self.path_for_run(run_id)
            with self._lock, path.open("ab") as handle:
                for event in group:
                    raw = (json.dumps(event.model_dump(mode="json", by_alias=True), sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
                    offset = handle.tell()
                    handle.write(raw)
                    handle.flush()
                    self.repository.add_event_index(
                        event,
                        ledger_path=str(path),
                        byte_offset=offset,
                        byte_length=len(raw),
                    )

    def read_after(self, run_id: str, cursor: int = 0, *, limit: int = 250) -> tuple[int, list[EventEnvelope]]:
        rows = self.repository.list_event_index_after(run_id, cursor, limit=limit)
        if not rows:
            return int(cursor), []
        result: list[EventEnvelope] = []
        for row in rows:
            path = Path(row["ledger_path"])
            with path.open("rb") as handle:
                handle.seek(int(row["byte_offset"]))
                raw = handle.read(int(row["byte_length"]))
            result.append(EventEnvelope.model_validate_json(raw))
        return int(rows[-1]["event_cursor"]), result

    def read_run(self, run_id: str) -> list[EventEnvelope]:
        path = self.path_for_run(run_id)
        if not path.exists():
            return []
        result: list[EventEnvelope] = []
        with path.open("rb") as handle:
            for line in handle:
                if line.strip():
                    result.append(EventEnvelope.model_validate_json(line))
        return result
