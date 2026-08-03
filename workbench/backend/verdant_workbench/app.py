from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from .curriculum import (
    CurriculumCompileRequest, CurriculumCompilerError, CurriculumFreezeRequest,
    CurriculumPackCompileRequest, CurriculumPackFreezeRequest,
)
from .experiments import ExperimentAuthorRequest, ExperimentForkRequest
from .models import (
    GrammarPreviewRequest,
    GrammarRuleTeachRequest,
    LanguageSentenceTeachRequest,
    LexemeTeachRequest,
    OrganismConfig,
    ProbeRequest,
    TeachingRequest,
)
from .run_service import DurableRunService, RunNotActiveError, RunServiceError
from .version import API_SCHEMA_VERSION, WORKBENCH_VERSION
from .release_identity import source_build_identity
from .providers import ProviderConfiguration, ProviderProposalRequest, ProviderError
from .plugins import PluginError


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateProjectRequest(ApiModel):
    name: str = "Verdant Project"


class CreateRunRequest(ApiModel):
    project_id: str | None = None
    seed: int = 7741
    state_dim: int = 128
    run_label: str = "verdant-workbench"


class TeachApiRequest(ApiModel):
    context_id: str
    labels: list[str]
    feature_vector: list[float] | None = None
    event_key: str | None = None
    expected_state_revision: int | None = None


class ProbeApiRequest(ApiModel):
    cue_labels: list[str]
    expected_state_revision: int | None = None


class QueueTeachRequest(ApiModel):
    context_id: str
    labels: list[str]
    feature_vector: list[float] | None = None
    event_key: str | None = None


class QueueProbeRequest(ApiModel):
    cue_labels: list[str]


class SaveCheckpointRequest(ApiModel):
    label: str | None = None


class GrammarPreviewApiRequest(ApiModel):
    sentence: str
    event_key: str = "workbench-grammar-preview"


class GrammarRuleApiRequest(ApiModel):
    rule_id: str
    event_key: str | None = None
    expected_state_revision: int | None = None


class LexemeApiRequest(ApiModel):
    lemma: str
    category: str
    forms: list[str]
    attributes: dict[str, Any] = {}
    event_key: str | None = None
    expected_state_revision: int | None = None


class LanguageSentenceApiRequest(ApiModel):
    sentence: str
    event_key: str
    expected_state_revision: int | None = None


class StructureMutationApiRequest(ApiModel):
    expected_state_revision: int | None = None


class StructureChallengeApiRequest(ApiModel):
    concept_ids: list[str]
    evidence_ref: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    expected_state_revision: int | None = None


class CausalCompareApiRequest(ApiModel):
    cue_label: str | None = None


class ExperimentFreezeApiRequest(ApiModel):
    project_id: str
    title: str = "Ethomorphism M19 Verification"
    seed: int = 1901
    state_dim: int = Field(default=16, ge=4)
    repeats_per_edge: int = Field(default=2, ge=1, le=20)
    noise_concepts: int = Field(default=16, ge=4, le=512)
    noise_repeats: int = Field(default=1, ge=1, le=20)
    relation_type: str = "linked"


class ExperimentForkApiRequest(ApiModel):
    title: str | None = None
    seed: int | None = None
    state_dim: int | None = Field(default=None, ge=4)
    repeats_per_edge: int | None = Field(default=None, ge=1, le=20)
    noise_concepts: int | None = Field(default=None, ge=4, le=512)
    noise_repeats: int | None = Field(default=None, ge=1, le=20)
    relation_type: str | None = None
    keep_expected_assertions: bool = True




class ProviderPasteApiRequest(ApiModel):
    prompt: str
    raw_response: str
    system_prompt: str | None = None
    settings: dict[str, Any] = {}


class ProviderCallApiRequest(ApiModel):
    prompt: str
    system_prompt: str | None = None
    settings: dict[str, Any] = {}


class WorkbenchRuntime:
    def __init__(self, home: Path | str | None = None) -> None:
        default_home = os.environ.get("VERDANT_WORKBENCH_HOME", ".verdant-workbench")
        self.home = Path(home or default_home)
        self._service: DurableRunService | None = None
        self._lock = Lock()

    @property
    def service(self) -> DurableRunService:
        with self._lock:
            if self._service is None:
                self._service = DurableRunService(self.home)
            return self._service

    def default_project_id(self) -> str:
        project_id = "proj_default"
        try:
            self.service.repository.get_project(project_id)
        except KeyError:
            self.service.create_project("Default Project", project_id=project_id)
        return project_id

    def create_run(self, request: CreateRunRequest) -> dict[str, Any]:
        project_id = request.project_id or self.default_project_id()
        return self.service.create_run(
            project_id,
            OrganismConfig(seed=request.seed, state_dim=request.state_dim, run_label=request.run_label),
        )

    def close(self) -> None:
        with self._lock:
            service = self._service
            self._service = None
        if service is not None:
            service.close()

    def reset(self, home: Path | str) -> None:
        self.close()
        self.home = Path(home)


runtime = WorkbenchRuntime()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        runtime.close()


app = FastAPI(title="Verdant Workbench", version=WORKBENCH_VERSION, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    service = runtime.service
    active = sum(1 for item in service.repository.list_runs() if item.status == "active")
    return {
        "status": "ok",
        "workbench_version": WORKBENCH_VERSION,
        "api_schema": API_SCHEMA_VERSION,
        "active_runs": active,
        "home": str(service.root),
    }


@app.get("/api/v1/projects")
def list_projects():
    return [item.__dict__ for item in runtime.service.repository.list_projects()]


@app.post("/api/v1/projects")
def create_project(request: CreateProjectRequest):
    return runtime.service.create_project(request.name).__dict__


@app.get("/api/v1/runs")
def list_runs(project_id: str | None = None):
    return [item.__dict__ for item in runtime.service.repository.list_runs(project_id)]


@app.get("/api/v1/projects/{project_id}")
def get_project(project_id: str):
    try:
        project = runtime.service.repository.get_project(project_id)
        runs = runtime.service.repository.list_runs(project_id)
        return {"project": project.__dict__, "runs": [item.__dict__ for item in runs]}
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")


@app.post("/api/v1/runs")
def create_run(request: CreateRunRequest):
    try:
        return runtime.create_run(request)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")


@app.post("/api/v1/projects/{project_id}/runs")
def create_project_run(project_id: str, request: CreateRunRequest):
    request = request.model_copy(update={"project_id": project_id})
    return create_run(request)


@app.get("/api/v1/runs/{run_id}/status")
def run_status(run_id: str):
    try:
        return runtime.service.status(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")


@app.get("/api/v1/runs/{run_id}/queue")
def queue_items(run_id: str):
    try:
        return runtime.service.list_queue(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")


@app.post("/api/v1/runs/{run_id}/queue/teach")
def queue_teach(run_id: str, request: QueueTeachRequest):
    try:
        item = runtime.service.enqueue_teaching(
            run_id,
            TeachingRequest(
                context_id=request.context_id,
                labels=tuple(request.labels),
                feature_vector=tuple(request.feature_vector) if request.feature_vector is not None else None,
                event_key=request.event_key,
            ),
        )
        data = item.__dict__.copy()
        data["payload"] = item.payload()
        data.pop("payload_json", None)
        return data
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")


@app.post("/api/v1/runs/{run_id}/queue/probe")
def queue_probe(run_id: str, request: QueueProbeRequest):
    try:
        item = runtime.service.enqueue_probe(run_id, ProbeRequest(cue_labels=tuple(request.cue_labels)))
        data = item.__dict__.copy()
        data["payload"] = item.payload()
        data.pop("payload_json", None)
        return data
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")


@app.post("/api/v1/runs/{run_id}/start")
def start_run_queue(run_id: str):
    try:
        return runtime.service.start_queue(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except (RunNotActiveError, RunServiceError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/v1/runs/{run_id}/pause")
def pause_run_queue(run_id: str):
    try:
        return runtime.service.pause_queue(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")


@app.post("/api/v1/runs/{run_id}/step")
def step_run_queue(run_id: str):
    try:
        return runtime.service.step_queue(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except (RunNotActiveError, RunServiceError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/v1/runs/{run_id}/stop")
def stop_run_queue(run_id: str):
    try:
        return runtime.service.stop_queue(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")


@app.post("/api/v1/runs/{run_id}/teach")
def teach(run_id: str, request: TeachApiRequest):
    try:
        teaching = TeachingRequest(
            context_id=request.context_id,
            labels=tuple(request.labels),
            feature_vector=tuple(request.feature_vector) if request.feature_vector is not None else None,
            event_key=request.event_key,
        )
        return runtime.service.teach(
            run_id,
            teaching,
            expected_state_revision=request.expected_state_revision,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except RunNotActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/v1/runs/{run_id}/probe")
def probe(run_id: str, request: ProbeApiRequest):
    try:
        return runtime.service.probe(
            run_id,
            ProbeRequest(cue_labels=tuple(request.cue_labels)),
            expected_state_revision=request.expected_state_revision,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except RunNotActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/v1/runs/{run_id}/checkpoints")
def save_checkpoint(run_id: str, request: SaveCheckpointRequest | None = None):
    try:
        record = runtime.service.save_checkpoint(run_id, label=None if request is None else request.label)
        return record.__dict__
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except RunNotActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.get("/api/v1/runs/{run_id}/checkpoints")
def list_checkpoints(run_id: str):
    try:
        runtime.service.repository.get_run(run_id)
        return [item.__dict__ for item in runtime.service.repository.list_checkpoints(run_id)]
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")


@app.post("/api/v1/runs/{run_id}/close")
def close_run(run_id: str):
    try:
        return runtime.service.close_run(run_id).__dict__
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")


@app.post("/api/v1/runs/{run_id}/reopen")
def reopen_run(run_id: str):
    try:
        return runtime.service.reopen_run(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except RunServiceError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/v1/checkpoints/{checkpoint_id}/branch")
def branch_checkpoint(checkpoint_id: str):
    try:
        return runtime.service.branch_from_checkpoint(checkpoint_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    except RunServiceError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.get("/api/v1/runs/{run_id}/ancestry")
def ancestry(run_id: str):
    try:
        return runtime.service.ancestry(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")


@app.get("/api/v1/runs/{run_id}/events")
def events(run_id: str, cursor: int = 0, limit: int = 250):
    try:
        runtime.service.repository.get_run(run_id)
        next_cursor, items = runtime.service.events.read_after(run_id, cursor, limit=max(1, min(limit, 1000)))
        return {
            "cursor": next_cursor,
            "events": [item.model_dump(mode="json", by_alias=True) for item in items],
        }
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")


@app.websocket("/api/v1/runs/{run_id}/events")
async def events_ws(websocket: WebSocket, run_id: str):
    try:
        runtime.service.repository.get_run(run_id)
    except KeyError:
        await websocket.close(code=4404, reason="Run not found")
        return
    await websocket.accept()
    try:
        cursor = int(websocket.query_params.get("cursor", "0"))
    except ValueError:
        cursor = 0
    try:
        while True:
            cursor, items = runtime.service.events.read_after(run_id, cursor, limit=250)
            if items:
                await websocket.send_json({
                    "kind": "events",
                    "cursor": cursor,
                    "events": [item.model_dump(mode="json", by_alias=True) for item in items],
                })
            await websocket.send_json({"kind": "status", "status": runtime.service.status(run_id), "cursor": cursor})
            await asyncio.sleep(0.35)
    except WebSocketDisconnect:
        return
    except Exception as exc:
        try:
            await websocket.send_json({"kind": "error", "detail": str(exc), "cursor": cursor})
        except Exception:
            pass
        try:
            await websocket.close(code=1011)
        except Exception:
            pass


@app.get("/api/v1/runs/{run_id}/snapshot")
def snapshot(run_id: str, scope: str = "summary"):
    try:
        return runtime.service.snapshot(run_id, scope=scope)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except RunNotActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.get("/api/v1/curricula/templates/editable-teaching-record")
def editable_teaching_template():
    return runtime.service.editable_teaching_template()


@app.get("/api/v1/curricula/templates/m19-alien")
def m19_curriculum_template():
    return runtime.service.m19_curriculum_template()


@app.post("/api/v1/curricula/compile")
def compile_curriculum(request: CurriculumCompileRequest):
    try:
        return runtime.service.compile_curriculum(request)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project or baseline curriculum not found")
    except CurriculumCompilerError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/api/v1/curricula/freeze")
def freeze_curriculum(request: CurriculumFreezeRequest):
    try:
        return runtime.service.freeze_curriculum(request).__dict__
    except KeyError:
        raise HTTPException(status_code=404, detail="Project or baseline curriculum not found")
    except CurriculumCompilerError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except RunServiceError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/v1/curricula/packs/compile")
def compile_curriculum_pack(request: CurriculumPackCompileRequest):
    try:
        return runtime.service.compile_curriculum_pack(request)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project or baseline curriculum not found")
    except CurriculumCompilerError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/api/v1/curricula/packs/freeze")
def freeze_curriculum_pack(request: CurriculumPackFreezeRequest):
    try:
        return runtime.service.freeze_curriculum_pack(request).__dict__
    except KeyError:
        raise HTTPException(status_code=404, detail="Project or baseline curriculum not found")
    except CurriculumCompilerError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except RunServiceError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.get("/api/v1/curricula")
def list_curricula(project_id: str | None = None):
    try:
        return [item.__dict__ for item in runtime.service.repository.list_curricula(project_id)]
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")


@app.get("/api/v1/curricula/{curriculum_id}")
def curriculum_detail(curriculum_id: str):
    try:
        return runtime.service.curriculum_detail(curriculum_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Curriculum not found")
    except (CurriculumCompilerError, FileNotFoundError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/v1/runs/{run_id}/curricula/{curriculum_id}/queue")
def queue_curriculum(run_id: str, curriculum_id: str):
    try:
        return runtime.service.queue_curriculum(run_id, curriculum_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run or curriculum not found")
    except RunServiceError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.get("/api/v1/runs/{run_id}/grammar")
def grammar_status(run_id: str):
    try:
        return runtime.service.grammar_status(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except RunNotActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/v1/runs/{run_id}/grammar/preview")
def grammar_preview(run_id: str, request: GrammarPreviewApiRequest):
    try:
        return runtime.service.grammar_preview(
            run_id, GrammarPreviewRequest(sentence=request.sentence, event_key=request.event_key)
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except RunNotActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/v1/runs/{run_id}/grammar/rules/teach")
def teach_grammar_rule(run_id: str, request: GrammarRuleApiRequest):
    try:
        return runtime.service.teach_grammar_rule(
            run_id,
            GrammarRuleTeachRequest(rule_id=request.rule_id, event_key=request.event_key),
            expected_state_revision=request.expected_state_revision,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except RunNotActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/api/v1/runs/{run_id}/grammar/lexemes/teach")
def teach_lexeme(run_id: str, request: LexemeApiRequest):
    try:
        return runtime.service.teach_lexeme(
            run_id,
            LexemeTeachRequest(
                lemma=request.lemma, category=request.category, forms=tuple(request.forms),
                attributes=request.attributes, event_key=request.event_key,
            ),
            expected_state_revision=request.expected_state_revision,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except RunNotActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/api/v1/runs/{run_id}/grammar/sentences/teach")
def teach_language_sentence(run_id: str, request: LanguageSentenceApiRequest):
    try:
        return runtime.service.teach_language_sentence(
            run_id,
            LanguageSentenceTeachRequest(sentence=request.sentence, event_key=request.event_key),
            expected_state_revision=request.expected_state_revision,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except RunNotActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/api/v1/runs/{run_id}/structures")
def forensic_structures(run_id: str):
    try:
        return runtime.service.forensic_structures(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except RunNotActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.get("/api/v1/runs/{run_id}/structures/{structure_id}")
def forensic_structure_detail(run_id: str, structure_id: str):
    try:
        return runtime.service.forensic_structure_detail(run_id, structure_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run or structure not found")
    except RunNotActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/api/v1/runs/{run_id}/structures/{structure_id}/replay")
def forensic_structure_replay(run_id: str, structure_id: str):
    try:
        return runtime.service.forensic_structure_replay(run_id, structure_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run or structure not found")
    except RunNotActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/api/v1/runs/{run_id}/structures/{structure_id}/graph")
def forensic_structure_graph(run_id: str, structure_id: str):
    try:
        return runtime.service.forensic_structure_graph(run_id, structure_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run or structure not found")
    except RunNotActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/v1/runs/{run_id}/structure-candidates/{candidate_id}/promote")
def promote_structure_candidate(run_id: str, candidate_id: str, request: StructureMutationApiRequest | None = None):
    try:
        return runtime.service.promote_structure(run_id, candidate_id, expected_state_revision=None if request is None else request.expected_state_revision)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except (RunNotActiveError, RunServiceError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/v1/runs/{run_id}/structures/{structure_id}/ablate")
def ablate_structure(run_id: str, structure_id: str, request: StructureMutationApiRequest | None = None):
    try:
        return runtime.service.ablate_structure(run_id, structure_id, expected_state_revision=None if request is None else request.expected_state_revision)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except (RunNotActiveError, RunServiceError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/v1/runs/{run_id}/structures/{structure_id}/restore")
def restore_structure(run_id: str, structure_id: str, request: StructureMutationApiRequest | None = None):
    try:
        return runtime.service.restore_structure(run_id, structure_id, expected_state_revision=None if request is None else request.expected_state_revision)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except (RunNotActiveError, RunServiceError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/v1/runs/{run_id}/structures/{structure_id}/interact")
def interact_structure(run_id: str, structure_id: str, request: StructureMutationApiRequest | None = None):
    try:
        return runtime.service.interact_structure(run_id, structure_id, expected_state_revision=None if request is None else request.expected_state_revision)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except (RunNotActiveError, RunServiceError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/v1/runs/{run_id}/structures/{structure_id}/challenge")
def challenge_structure(run_id: str, structure_id: str, request: StructureChallengeApiRequest):
    if len(request.concept_ids) != 2 or request.concept_ids[0] == request.concept_ids[1]:
        raise HTTPException(status_code=422, detail="Challenge requires exactly two distinct concept IDs")
    try:
        return runtime.service.challenge_structure(
            run_id, structure_id, tuple(sorted((request.concept_ids[0], request.concept_ids[1]))),
            request.evidence_ref, request.confidence, expected_state_revision=request.expected_state_revision,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except (RunNotActiveError, RunServiceError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/v1/runs/{run_id}/structures/{structure_id}/refold")
def refold_structure(run_id: str, structure_id: str, request: StructureMutationApiRequest | None = None):
    try:
        return runtime.service.refold_structure(run_id, structure_id, expected_state_revision=None if request is None else request.expected_state_revision)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except (RunNotActiveError, RunServiceError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/v1/runs/{run_id}/structures/{structure_id}/causal-compare")
def causal_compare_structure(run_id: str, structure_id: str, request: CausalCompareApiRequest | None = None):
    try:
        return runtime.service.causal_compare_structure(run_id, structure_id, None if request is None else request.cue_label)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except (RunNotActiveError, RunServiceError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.get("/api/v1/runs/{run_id}/explorer/frame")
def living_explorer_frame(run_id: str, cycle: int | None = None, max_nodes: int = 240, max_edges: int = 500):
    try:
        return runtime.service.living_explorer_frame(run_id, cycle, max_nodes=max_nodes, max_edges=max_edges)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except RunNotActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/api/v1/runs/{run_id}/explorer/timeline")
def living_explorer_timeline(run_id: str, max_frames: int = 240, max_nodes: int = 240, max_edges: int = 500, include_frames: bool = True):
    try:
        return runtime.service.living_explorer_timeline(
            run_id, max_frames=max_frames, max_nodes=max_nodes, max_edges=max_edges, include_frames=include_frames
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except RunNotActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/api/v1/runs/{run_id}/hierarchy/observe")
def observe_hierarchy(run_id: str, request: StructureMutationApiRequest | None = None):
    try:
        return runtime.service.observe_hierarchy(run_id, expected_state_revision=None if request is None else request.expected_state_revision)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except (RunNotActiveError, RunServiceError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/v1/runs/{run_id}/hierarchy-candidates/{candidate_id}/promote")
def promote_hierarchy_candidate(run_id: str, candidate_id: str, request: StructureMutationApiRequest | None = None):
    try:
        return runtime.service.promote_hierarchy(run_id, candidate_id, expected_state_revision=None if request is None else request.expected_state_revision)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")
    except (RunNotActiveError, RunServiceError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.get("/api/v1/experiments")
def list_experiments(project_id: str | None = None):
    try:
        return [item.__dict__ for item in runtime.service.repository.list_experiments(project_id)]
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")


@app.get("/api/v1/experiments/templates/ethomorphism-m19")
def experiment_template(project_id: str):
    try:
        return runtime.service.experiment_template(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")


@app.post("/api/v1/experiments/freeze")
def freeze_experiment(request: ExperimentFreezeApiRequest):
    try:
        record = runtime.service.freeze_experiment(ExperimentAuthorRequest(**request.model_dump()))
        return record.__dict__
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")
    except (RunServiceError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/api/v1/experiments/{experiment_id}")
def experiment_detail(experiment_id: str):
    try:
        return runtime.service.experiment_detail(experiment_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Experiment not found")
    except (RunServiceError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/api/v1/experiments/{experiment_id}/run")
def start_experiment(experiment_id: str):
    try:
        return runtime.service.start_experiment(experiment_id).__dict__
    except KeyError:
        raise HTTPException(status_code=404, detail="Experiment not found")
    except (RunServiceError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/api/v1/experiment-runs/{experiment_run_id}")
def experiment_run_status(experiment_run_id: str):
    try:
        return runtime.service.experiment_run_detail(experiment_run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Experiment run not found")
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/api/v1/experiment-runs/{experiment_run_id}/verify")
def verify_experiment_run(experiment_run_id: str):
    try:
        return runtime.service.verify_experiment_run(experiment_run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Experiment run not found")
    except (RunServiceError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/v1/experiments/{experiment_id}/fork")
def fork_experiment(experiment_id: str, request: ExperimentForkApiRequest):
    try:
        record = runtime.service.fork_experiment(experiment_id, ExperimentForkRequest(**request.model_dump()))
        return record.__dict__
    except KeyError:
        raise HTTPException(status_code=404, detail="Experiment not found")
    except (RunServiceError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/api/v1/experiments/{experiment_id}/package")
def download_experiment_package(experiment_id: str):
    try:
        path = runtime.service.experiment_artifact_path(experiment_id)
        return FileResponse(path, media_type="application/vnd.verdant.experiment+zip", filename=f"{experiment_id}.vexp")
    except KeyError:
        raise HTTPException(status_code=404, detail="Experiment not found")


@app.get("/api/v1/experiment-runs/{experiment_run_id}/package")
def download_experiment_run_package(experiment_run_id: str):
    try:
        path = runtime.service.experiment_run_artifact_path(experiment_run_id)
        return FileResponse(path, media_type="application/vnd.verdant.experiment+zip", filename=f"{experiment_run_id}-verification.vexp")
    except KeyError:
        raise HTTPException(status_code=404, detail="Experiment run not found")
    except RunServiceError as exc:
        raise HTTPException(status_code=409, detail=str(exc))



# ---------------------------------------------------------------------------
# WB-08 Provider Connections

@app.get("/api/v1/providers")
def list_providers():
    return runtime.service.list_providers()


@app.post("/api/v1/providers")
def save_provider(config: ProviderConfiguration):
    try:
        return runtime.service.save_provider(config)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/api/v1/providers/{provider_id}/capture-paste")
def capture_provider_paste(provider_id: str, request: ProviderPasteApiRequest):
    try:
        proposal = ProviderProposalRequest(prompt=request.prompt, system_prompt=request.system_prompt, settings=request.settings)
        return runtime.service.capture_provider_paste(provider_id, proposal, request.raw_response)
    except KeyError:
        raise HTTPException(status_code=404, detail="Provider not found")
    except ProviderError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/api/v1/providers/{provider_id}/propose")
def call_provider(provider_id: str, request: ProviderCallApiRequest):
    try:
        proposal = ProviderProposalRequest(prompt=request.prompt, system_prompt=request.system_prompt, settings=request.settings)
        return runtime.service.call_provider(provider_id, proposal)
    except KeyError:
        raise HTTPException(status_code=404, detail="Provider not found")
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/api/v1/provider-captures")
def list_provider_captures():
    return runtime.service.list_provider_captures()


@app.get("/api/v1/provider-captures/{capture_id}")
def provider_capture_detail(capture_id: str):
    try:
        return runtime.service.provider_capture_detail(capture_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Provider capture not found")


@app.get("/api/v1/provider-captures/{capture_id}/curriculum-source")
def provider_capture_curriculum_source(capture_id: str):
    try:
        return runtime.service.provider_capture_curriculum_source(capture_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Provider capture not found")
    except RunServiceError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.get("/api/v1/provider-captures/{capture_id}/package")
def provider_capture_package(capture_id: str):
    try:
        detail = runtime.service.provider_capture_detail(capture_id)
        path = runtime.service.artifacts.resolve(detail["record"]["artifact_sha256"], verify=True)
        return FileResponse(path, media_type="application/vnd.verdant.provider-capture+zip", filename=f"{capture_id}.vpcap")
    except KeyError:
        raise HTTPException(status_code=404, detail="Provider capture not found")


# ---------------------------------------------------------------------------
# WB-09 Plugin SDK / Engineering hardening

@app.get("/api/v1/plugins")
def list_plugins():
    return runtime.service.list_plugins()


@app.post("/api/v1/plugins/{plugin_id}/metric/{run_id}")
def invoke_metric_plugin(plugin_id: str, run_id: str):
    try:
        return runtime.service.invoke_metric_plugin(plugin_id, run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run or plugin not found")
    except (RunNotActiveError, PluginError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.get("/api/v1/engineering/integrity")
def integrity_scan():
    return runtime.service.integrity_scan()


@app.get("/api/v1/engineering/diagnostics")
def diagnostics():
    service = runtime.service
    return {
        "schema": "verdant.workbench.diagnostics.v1",
        "workbench_version": WORKBENCH_VERSION,
        "api_schema": API_SCHEMA_VERSION,
        "home": str(service.root),
        "project_count": len(service.repository.list_projects()),
        "run_count": len(service.repository.list_runs()),
        "provider_count": len(service.list_providers()),
        "provider_capture_count": len(service.list_provider_captures()),
        "plugin_count": len(service.list_plugins()),
        "build_identity": source_build_identity(),
        "integrity": service.integrity_scan(),
    }

_frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="workbench-ui")
