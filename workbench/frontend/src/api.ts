export type Project = { project_id: string; name: string; created_at: string; updated_at: string };
export type RunRecord = {
  run_id: string; project_id: string; organism_id: string; status: string;
  created_at: string; updated_at: string; parent_run_id?: string | null;
  parent_checkpoint_id?: string | null; head_checkpoint_id?: string | null;
  latest_state_revision: number; latest_cycle: number; latest_fingerprint: string;
};
export type RunStatus = {
  run: RunRecord;
  descriptor: null | { organism_id:string; run_id:string; kernel_id:string; seed:number; state_dim:number; run_label:string; cycle:number; state_revision:number; fingerprint:string };
  metrics: Record<string, unknown> | null;
  worker_alive: boolean;
  execution: { state:string; last_error?:string|null; active_queue_item_id?:string|null; queue_counts:Record<string,number> };
  dirty: boolean;
  head_checkpoint_id?: string|null;
  saved_state_revision?: number|null;
  saved_cycle?: number|null;
};
export type QueueItem = {
  queue_item_id:string; run_id:string; sequence_no:number; command_type:string; status:string;
  created_at:string; started_at?:string|null; completed_at?:string|null; error_message?:string|null;
  payload:Record<string,unknown>; result?:Record<string,unknown>|null;
};
export type EventEnvelope = {
  schema:string; event_id:string; run_id:string; organism_id:string; engine_cycle:number; state_revision:number;
  event_type:string; source_command_id:string; timestamp_utc:string; payload:Record<string,unknown>; payload_sha256:string;
};

const API = '/api/v1';

async function request<T>(path:string, init?:RequestInit):Promise<T>{
  const res = await fetch(path, {headers:{'Content-Type':'application/json', ...(init?.headers||{})}, ...init});
  if(!res.ok){ let detail = `${res.status} ${res.statusText}`; try{ const body=await res.json(); detail=body.detail||JSON.stringify(body);}catch{} throw new Error(detail); }
  return res.json();
}

export const api = {
  projects: () => request<Project[]>(`${API}/projects`),
  createProject: (name:string) => request<Project>(`${API}/projects`, {method:'POST', body:JSON.stringify({name})}),
  runs: (projectId?:string) => request<RunRecord[]>(`${API}/runs${projectId?`?project_id=${encodeURIComponent(projectId)}`:''}`),
  createRun: (projectId:string, seed:number, stateDim:number, runLabel:string) => request<any>(`${API}/projects/${projectId}/runs`, {method:'POST', body:JSON.stringify({seed,state_dim:stateDim,run_label:runLabel})}),
  status: (runId:string) => request<RunStatus>(`${API}/runs/${runId}/status`),
  reopen: (runId:string) => request<any>(`${API}/runs/${runId}/reopen`, {method:'POST'}),
  close: (runId:string) => request<any>(`${API}/runs/${runId}/close`, {method:'POST'}),
  queue: (runId:string) => request<QueueItem[]>(`${API}/runs/${runId}/queue`),
  queueTeach: (runId:string, contextId:string, labels:string[]) => request<any>(`${API}/runs/${runId}/queue/teach`, {method:'POST', body:JSON.stringify({context_id:contextId, labels})}),
  queueProbe: (runId:string, cueLabels:string[]) => request<any>(`${API}/runs/${runId}/queue/probe`, {method:'POST', body:JSON.stringify({cue_labels:cueLabels})}),
  teachNow: (runId:string, contextId:string, labels:string[], expected?:number) => request<any>(`${API}/runs/${runId}/teach`, {method:'POST', body:JSON.stringify({context_id:contextId,labels,expected_state_revision:expected??null})}),
  probeNow: (runId:string, labels:string[], expected?:number) => request<any>(`${API}/runs/${runId}/probe`, {method:'POST', body:JSON.stringify({cue_labels:labels,expected_state_revision:expected??null})}),
  start: (runId:string) => request<any>(`${API}/runs/${runId}/start`, {method:'POST'}),
  pause: (runId:string) => request<any>(`${API}/runs/${runId}/pause`, {method:'POST'}),
  step: (runId:string) => request<any>(`${API}/runs/${runId}/step`, {method:'POST'}),
  stop: (runId:string) => request<any>(`${API}/runs/${runId}/stop`, {method:'POST'}),
  save: (runId:string,label?:string) => request<any>(`${API}/runs/${runId}/checkpoints`, {method:'POST',body:JSON.stringify({label:label||null})}),
  checkpoints: (runId:string) => request<any[]>(`${API}/runs/${runId}/checkpoints`),
  ancestry: (runId:string) => request<any[]>(`${API}/runs/${runId}/ancestry`),
  snapshot: (runId:string, scope='summary') => request<any>(`${API}/runs/${runId}/snapshot?scope=${encodeURIComponent(scope)}`),
  events: (runId:string, cursor=0, limit=1000) => request<any>(`${API}/runs/${runId}/events?cursor=${cursor}&limit=${limit}`),
  branch: (checkpointId:string) => request<any>(`${API}/checkpoints/${checkpointId}/branch`, {method:'POST'}),
};

export function eventSocket(runId:string, cursor:number, onMessage:(data:any)=>void, onState:(state:string)=>void){
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const socket = new WebSocket(`${proto}://${location.host}${API}/runs/${runId}/events?cursor=${cursor}`);
  socket.onopen=()=>onState('connected');
  socket.onclose=()=>onState('disconnected');
  socket.onerror=()=>onState('error');
  socket.onmessage=(e)=>{ try{ onMessage(JSON.parse(e.data)); }catch{} };
  return socket;
}

export type CurriculumRecord = {
  curriculum_id:string; project_id:string; title:string; version:number; source_format:string;
  source_sha256:string; compiled_sha256:string; artifact_sha256:string; artifact_size_bytes:number;
  item_count:number; state_dim:number; compiler_version:string; created_at:string;
};

export type CurriculumCompileResult = {
  schema:string; compiler_version:string; title:string; source_format:string; source_text:string;
  source_sha256:string; state_dim:number; item_count:number; scaffold_item_count:number; language_scaffold:Record<string,unknown>; parsed_items:any[];
  compiled_commands:any[]; compiled_jsonl:string; compiled_sha256:string; warnings:string[];
  diff_from_baseline?:string|null;
};

export type GrammarStatus = {
  state_revision:number; cycle:number; enabled_rules:string[];
  rules:Array<{rule_id:string;pattern:string;description:string;curriculum_text:string;roles:string[];enabled:boolean}>;
  lexicon:Array<{form:string;lemma:string;category:string}>;
};

Object.assign(api, {
  curricula: (projectId?:string) => request<CurriculumRecord[]>(`${API}/curricula${projectId?`?project_id=${encodeURIComponent(projectId)}`:''}`),
  curriculumTemplateM19: () => request<any>(`${API}/curricula/templates/m19-alien`),
  curriculumTemplateEditable: () => request<any>(`${API}/curricula/templates/editable-teaching-record`),
  compileCurriculum: (body:any) => request<CurriculumCompileResult>(`${API}/curricula/compile`, {method:'POST',body:JSON.stringify(body)}),
  freezeCurriculum: (body:any) => request<CurriculumRecord>(`${API}/curricula/freeze`, {method:'POST',body:JSON.stringify(body)}),
  compileCurriculumPack: (body:any) => request<any>(`${API}/curricula/packs/compile`, {method:'POST',body:JSON.stringify(body)}),
  freezeCurriculumPack: (body:any) => request<CurriculumRecord>(`${API}/curricula/packs/freeze`, {method:'POST',body:JSON.stringify(body)}),
  curriculumDetail: (id:string) => request<any>(`${API}/curricula/${id}`),
  queueCurriculum: (runId:string,id:string) => request<any>(`${API}/runs/${runId}/curricula/${id}/queue`, {method:'POST'}),
  grammar: (runId:string) => request<GrammarStatus>(`${API}/runs/${runId}/grammar`),
  grammarPreview: (runId:string, sentence:string, eventKey:string) => request<any>(`${API}/runs/${runId}/grammar/preview`, {method:'POST',body:JSON.stringify({sentence,event_key:eventKey})}),
  teachGrammarRule: (runId:string, ruleId:string, expected?:number) => request<any>(`${API}/runs/${runId}/grammar/rules/teach`, {method:'POST',body:JSON.stringify({rule_id:ruleId,expected_state_revision:expected??null})}),
  teachLexeme: (runId:string, lemma:string, category:string, forms:string[], expected?:number) => request<any>(`${API}/runs/${runId}/grammar/lexemes/teach`, {method:'POST',body:JSON.stringify({lemma,category,forms,expected_state_revision:expected??null})}),
  teachSentence: (runId:string, sentence:string, eventKey:string, expected?:number) => request<any>(`${API}/runs/${runId}/grammar/sentences/teach`, {method:'POST',body:JSON.stringify({sentence,event_key:eventKey,expected_state_revision:expected??null})}),
});

Object.assign(api, {
  structures: (runId:string) => request<any>(`${API}/runs/${runId}/structures`),
  structureDetail: (runId:string,id:string) => request<any>(`${API}/runs/${runId}/structures/${id}`),
  structureReplay: (runId:string,id:string) => request<any>(`${API}/runs/${runId}/structures/${id}/replay`),
  structureGraph: (runId:string,id:string) => request<any>(`${API}/runs/${runId}/structures/${id}/graph`),
  promoteStructure: (runId:string,id:string,expected?:number) => request<any>(`${API}/runs/${runId}/structure-candidates/${id}/promote`, {method:'POST',body:JSON.stringify({expected_state_revision:expected??null})}),
  ablateStructure: (runId:string,id:string,expected?:number) => request<any>(`${API}/runs/${runId}/structures/${id}/ablate`, {method:'POST',body:JSON.stringify({expected_state_revision:expected??null})}),
  restoreStructure: (runId:string,id:string,expected?:number) => request<any>(`${API}/runs/${runId}/structures/${id}/restore`, {method:'POST',body:JSON.stringify({expected_state_revision:expected??null})}),
  interactStructure: (runId:string,id:string,expected?:number) => request<any>(`${API}/runs/${runId}/structures/${id}/interact`, {method:'POST',body:JSON.stringify({expected_state_revision:expected??null})}),
  causalCompareStructure: (runId:string,id:string,cueLabel?:string) => request<any>(`${API}/runs/${runId}/structures/${id}/causal-compare`, {method:'POST',body:JSON.stringify({cue_label:cueLabel||null})}),
});

Object.assign(api, {
  experiments: (projectId?:string) => request<any[]>(`${API}/experiments${projectId?`?project_id=${encodeURIComponent(projectId)}`:''}`),
  experimentTemplate: (projectId:string) => request<any>(`${API}/experiments/templates/ethomorphism-m19?project_id=${encodeURIComponent(projectId)}`),
  freezeExperiment: (body:any) => request<any>(`${API}/experiments/freeze`, {method:'POST',body:JSON.stringify(body)}),
  experimentDetail: (id:string) => request<any>(`${API}/experiments/${id}`),
  runExperiment: (id:string) => request<any>(`${API}/experiments/${id}/run`, {method:'POST'}),
  experimentRun: (id:string) => request<any>(`${API}/experiment-runs/${id}`),
  verifyExperiment: (id:string) => request<any>(`${API}/experiment-runs/${id}/verify`, {method:'POST'}),
  forkExperiment: (id:string, body:any) => request<any>(`${API}/experiments/${id}/fork`, {method:'POST',body:JSON.stringify(body)}),
});

Object.assign(api, {
  providers: () => request<any[]>(`${API}/providers`),
  providerCaptures: () => request<any[]>(`${API}/provider-captures`),
  captureProviderPaste: (providerId:string, body:any) => request<any>(`${API}/providers/${providerId}/capture-paste`, {method:'POST',body:JSON.stringify(body)}),
  providerCaptureSource: (captureId:string) => request<any>(`${API}/provider-captures/${captureId}/curriculum-source`),
  plugins: () => request<any[]>(`${API}/plugins`),
  diagnostics: () => request<any>(`${API}/engineering/diagnostics`),
  runMetricPlugin: (pluginId:string, runId:string) => request<any>(`${API}/plugins/${pluginId}/metric/${runId}`, {method:'POST'}),
});
