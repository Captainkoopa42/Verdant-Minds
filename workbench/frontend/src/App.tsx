import React, {useEffect, useMemo, useRef, useState} from 'react';
import {api, EventEnvelope, eventSocket, Project, QueueItem, RunRecord, RunStatus} from './api';

const nav = ['Organism','Cultivate','Curriculum','Grammar','Explorer','Structures','Evidence','Experiments','Timeline','Connections','Engineering'];
const implemented = new Set(['Organism','Cultivate','Curriculum','Grammar','Explorer','Structures','Evidence','Experiments','Timeline','Connections','Engineering']);

function short(value?:string|null, n=12){ return value ? (value.length>n ? value.slice(0,n)+'…' : value) : '—'; }
function words(raw:string){ return raw.split(/[\s,]+/).map(x=>x.trim()).filter(Boolean); }
function provenance(type:string){
  if(type==='EVIDENCE_ACCEPTED') return 'OBSERVED';
  if(type==='PLASTICITY_CHANGED') return 'ASSOCIATED';
  if(type.includes('CANDIDATE')) return 'MANUFACTURED';
  if(type.includes('PROMOTED')) return 'PROMOTED';
  if(type.includes('USED') || type.includes('INTERACTION')) return 'USED';
  if(type.includes('CHALLENGE')) return 'CHALLENGED';
  if(type.includes('REFOLD')) return 'REFOLDED';
  if(type.startsWith('RUN_') || type==='CHECKPOINT_SAVED') return 'PROGRAMMED';
  return 'ENGINE';
}

export function App(){
  const [page,setPage]=useState('Organism');
  const [projects,setProjects]=useState<Project[]>([]);
  const [runs,setRuns]=useState<RunRecord[]>([]);
  const [selectedRun,setSelectedRun]=useState<string>(()=>localStorage.getItem('verdant.selectedRun')||'');
  const [status,setStatus]=useState<RunStatus|null>(null);
  const [queue,setQueue]=useState<QueueItem[]>([]);
  const [events,setEvents]=useState<EventEnvelope[]>([]);
  const [cursor,setCursor]=useState(0);
  const [socketState,setSocketState]=useState('disconnected');
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const [newProject,setNewProject]=useState('Verdant Lab');
  const [runSeed,setRunSeed]=useState(7741);
  const [runDim,setRunDim]=useState(128);
  const [runLabel,setRunLabel]=useState('verdant-workbench');
  const [projectId,setProjectId]=useState('');
  const [context,setContext]=useState('manual');
  const [lesson,setLesson]=useState('kren tar vel');
  const [probe,setProbe]=useState('kren');
  const [checkpointLabel,setCheckpointLabel]=useState('');
  const cursorRef=useRef(0);

  const refreshLab=async()=>{
    const ps=await api.projects(); setProjects(ps);
    if(!projectId && ps[0]) setProjectId(ps[0].project_id);
    const rs=await api.runs(); setRuns(rs);
  };
  const refreshRun=async()=>{
    if(!selectedRun) return;
    try{
      const [s,q]=await Promise.all([api.status(selectedRun),api.queue(selectedRun)]);
      setStatus(s); setQueue(q); setError('');
    }catch(e:any){ setError(e.message); }
  };
  useEffect(()=>{ refreshLab().catch(e=>setError(e.message)); },[]);
  useEffect(()=>{ if(selectedRun){ localStorage.setItem('verdant.selectedRun',selectedRun); refreshRun(); } },[selectedRun]);
  useEffect(()=>{
    if(!selectedRun) return;
    setEvents([]); setCursor(0); cursorRef.current=0;
    let closed=false; let ws:WebSocket|undefined; let retry:any;
    const connect=()=>{
      if(closed) return;
      ws=eventSocket(selectedRun,cursorRef.current,(msg)=>{
        if(msg.kind==='events'){
          cursorRef.current=msg.cursor||cursorRef.current; setCursor(cursorRef.current);
          setEvents(prev=>[...prev,...(msg.events||[])].slice(-500));
        }
        if(msg.kind==='status'){ setStatus(msg.status); if(msg.cursor){cursorRef.current=msg.cursor;setCursor(msg.cursor);} }
      },(state)=>{
        setSocketState(state);
        if(state==='disconnected' && !closed) retry=setTimeout(connect,900);
      });
    };
    connect();
    return ()=>{ closed=true; if(retry) clearTimeout(retry); ws?.close(); };
  },[selectedRun]);
  useEffect(()=>{ if(!selectedRun) return; const t=setInterval(()=>{api.queue(selectedRun).then(setQueue).catch(()=>{});},1000); return()=>clearInterval(t); },[selectedRun]);

  const activeRun=useMemo(()=>runs.find(r=>r.run_id===selectedRun),[runs,selectedRun]);
  const execute=async(fn:()=>Promise<any>, refresh=true)=>{ setBusy(true); setError(''); try{ const out=await fn(); if(refresh){await refreshRun();await refreshLab();} return out;}catch(e:any){setError(e.message); throw e;}finally{setBusy(false);} };

  const createProject=async()=>{ const p=await execute(()=>api.createProject(newProject)); setProjectId(p.project_id); };
  const createRun=async()=>{
    if(!projectId){setError('Create or select a project first.');return;}
    const d=await execute(()=>api.createRun(projectId,runSeed,runDim,runLabel)); setSelectedRun(d.run_id); setPage('Cultivate');
  };
  const reopen=async()=>{
    if(!selectedRun)return;
    const descriptor=await execute(()=>api.reopen(selectedRun));
    if(descriptor?.run_id && descriptor.run_id!==selectedRun){
      setSelectedRun(descriptor.run_id);
      setPage('Cultivate');
    }
  };
  const queueLesson=async()=>{ if(!selectedRun)return; await execute(()=>api.queueTeach(selectedRun,context,words(lesson))); };
  const teachNow=async()=>{ if(!selectedRun)return; await execute(()=>api.teachNow(selectedRun,context,words(lesson),status?.descriptor?.state_revision)); };
  const probeNow=async()=>{ if(!selectedRun)return; await execute(()=>api.probeNow(selectedRun,words(probe),status?.descriptor?.state_revision)); };
  const save=async()=>{ if(!selectedRun)return; await execute(()=>api.save(selectedRun,checkpointLabel)); setCheckpointLabel(''); };
  const fork=async()=>{ if(!status?.head_checkpoint_id){setError('Save a checkpoint before branching.');return;} const d=await execute(()=>api.branch(status.head_checkpoint_id)); setSelectedRun(d.run_id); setPage('Cultivate'); };

  return <div className="shell">
    <aside>
      <div className="brand"><h1>Verdant</h1><div className="sub">WORKBENCH 1.0.1 · V5</div></div>
      {nav.map(item=><button key={item} onClick={()=>implemented.has(item)&&setPage(item)} className={`${page===item?'active':''} ${!implemented.has(item)?'disabled':''}`}>{item}{!implemented.has(item)&&<span>later</span>}</button>)}
      <div className="aside-foot"><div className={`dot ${socketState}`}></div>{selectedRun?short(selectedRun,18):'No run selected'}</div>
    </aside>
    <main>
      <header>
        <div><strong>LOCAL DEVELOPMENTAL AI LAB</strong><span>{activeRun ? activeRun.run_id : 'No organism selected'}</span></div>
        <div className="header-actions">
          {status?.dirty && <div className="pill warning">● UNSAVED DEVELOPMENT</div>}
          <div className={`pill ${status?.worker_alive?'ok':''}`}>{status?.worker_alive?'ENGINE ONLINE':'ENGINE OFFLINE'}</div>
        </div>
      </header>
      {error&&<div className="errorbar"><strong>Workbench:</strong> {error}<button onClick={()=>setError('')}>×</button></div>}
      {page==='Organism'?<OrganismPage projects={projects} runs={runs} projectId={projectId} setProjectId={setProjectId} selectedRun={selectedRun} setSelectedRun={setSelectedRun} status={status} newProject={newProject} setNewProject={setNewProject} createProject={createProject} createRun={createRun} runSeed={runSeed} setRunSeed={setRunSeed} runDim={runDim} setRunDim={setRunDim} runLabel={runLabel} setRunLabel={setRunLabel} reopen={reopen} busy={busy}/>
      :page==='Cultivate'?<CultivatePage status={status} queue={queue} events={events} context={context} setContext={setContext} lesson={lesson} setLesson={setLesson} probe={probe} setProbe={setProbe} checkpointLabel={checkpointLabel} setCheckpointLabel={setCheckpointLabel} queueLesson={queueLesson} teachNow={teachNow} probeNow={probeNow} save={save} fork={fork} busy={busy} selectedRun={selectedRun} execute={execute} refreshRun={refreshRun} cursor={cursor}/>
      :page==='Curriculum'?<CurriculumPage projectId={projectId} selectedRun={selectedRun} runStateDim={status?.descriptor?.state_dim||runDim} execute={execute}/>
      :page==='Grammar'?<GrammarPage selectedRun={selectedRun} status={status} execute={execute} refreshRun={refreshRun}/>
      :page==='Structures'?<ForensicPage selectedRun={selectedRun} status={status} execute={execute} mode="structures"/>
      :page==='Explorer'?<ForensicPage selectedRun={selectedRun} status={status} execute={execute} mode="explorer"/>
      :page==='Evidence'?<EvidencePage selectedRun={selectedRun}/>
      :page==='Experiments'?<ExperimentsPage projectId={projectId} execute={execute}/>
      :page==='Timeline'?<TimelinePage selectedRun={selectedRun}/>
      :page==='Connections'?<ConnectionsPage execute={execute}/>
      :page==='Engineering'?<EngineeringPage selectedRun={selectedRun} execute={execute}/>
      :null}
    </main>
  </div>;
}


function EvidencePage({selectedRun}:any){
  const a:any=api; const [snap,setSnap]=useState<any>(null); const [query,setQuery]=useState('');
  useEffect(()=>{if(selectedRun)a.snapshot(selectedRun,'full_debug').then(setSnap).catch(()=>setSnap(null));},[selectedRun]);
  if(!selectedRun)return <div className="page"><section className="title"><h2>Select an organism to inspect evidence.</h2></section></div>;
  const st=snap?.payload?.state||{}; const groups:any[]=[['Evidence',st.evidence],['Concepts',st.concepts],['Relations',st.relations],['Claims',st.claims],['Contradictions',st.contradictions],['Structural challenges',st.structural_challenges]];
  return <div className="page"><section className="title compact"><div className="eyebrow">EVIDENCE / KNOWLEDGE INSPECTOR · 1.0.1</div><h2>Canonical records, searchable and read-only.</h2></section><section className="panel"><input placeholder="search records" value={query} onChange={e=>setQuery(e.target.value)}/></section><div className="studio-grid">{groups.map(([name,obj])=>{const vals:any[]=Array.isArray(obj)?obj:Object.values(obj||{});const shown=query?vals.filter(v=>JSON.stringify(v).toLowerCase().includes(query.toLowerCase())):vals;return <section className="panel" key={name}><h3>{name} · {shown.length}/{vals.length}</h3><pre className="inspector tall">{JSON.stringify(shown.slice(0,80),null,2)}</pre></section>})}</div></div>;
}

function TimelinePage({selectedRun}:any){
  const a:any=api; const [data,setData]=useState<any>({checkpoints:[],ancestry:[],events:[]});
  useEffect(()=>{if(selectedRun)Promise.all([a.checkpoints(selectedRun),a.ancestry(selectedRun),a.events(selectedRun,0,1000)]).then(([checkpoints,ancestry,ev]:any)=>setData({checkpoints,ancestry,events:ev.events||[]})).catch(()=>setData({checkpoints:[],ancestry:[],events:[]}));},[selectedRun]);
  if(!selectedRun)return <div className="page"><section className="title"><h2>Select a run to inspect its timeline.</h2></section></div>;
  return <div className="page"><section className="title compact"><div className="eyebrow">TIMELINE / BRANCH HISTORY · 1.0.1</div><h2>Recorded development and immutable ancestry.</h2></section><div className="studio-grid"><section className="panel"><h3>Run ancestry</h3><pre className="inspector">{JSON.stringify(data.ancestry,null,2)}</pre></section><section className="panel"><h3>Checkpoints</h3><pre className="inspector">{JSON.stringify(data.checkpoints,null,2)}</pre></section></div><section className="panel"><h3>Committed events</h3><pre className="inspector tall">{JSON.stringify(data.events.slice(-300),null,2)}</pre></section></div>;
}

function ConnectionsPage({execute}:any){
  const a:any=api; const [providers,setProviders]=useState<any[]>([]); const [captures,setCaptures]=useState<any[]>([]);
  const [prompt,setPrompt]=useState('Convert this teaching goal into verdant.teaching.bundle.v1.'); const [raw,setRaw]=useState(''); const [source,setSource]=useState<any>(null);
  const load=async()=>{setProviders(await a.providers());setCaptures(await a.providerCaptures());}; useEffect(()=>{load().catch(()=>{})},[]);
  const template=async()=>{const t=await a.curriculumTemplateEditable();setRaw(t.source_text)};
  const capture=async()=>{const x=await execute(()=>a.captureProviderPaste('provider_paste',{prompt,raw_response:raw,settings:{}}),false);await load();if(x.capture_id)setSource(await a.providerCaptureSource(x.capture_id));};
  return <div className="page"><section className="title compact"><div className="eyebrow">PROVIDER CONNECTIONS · WORKBENCH 1.0.1</div><h2>Capture external teaching assistance without attaching it to Verdant cognition.</h2></section><div className="studio-grid"><section className="panel"><label>Prompt<textarea value={prompt} onChange={e=>setPrompt(e.target.value)}/></label><label>External model response<textarea className="tall" value={raw} onChange={e=>setRaw(e.target.value)}/></label><button onClick={template}>Load editable template</button><button className="primary" onClick={capture}>Capture immutably</button></section><section className="panel"><h3>Providers</h3><pre className="inspector">{JSON.stringify(providers,null,2)}</pre><h3>Captures</h3><pre className="inspector">{JSON.stringify(captures,null,2)}</pre></section></div>{source&&<section className="panel"><h3>Replayable curriculum source</h3><pre className="inspector">{JSON.stringify(source,null,2)}</pre></section>}</div>;
}

function EngineeringPage({selectedRun,execute}:any){
  const a:any=api; const [plugins,setPlugins]=useState<any[]>([]);const [diag,setDiag]=useState<any>(null);const [result,setResult]=useState<any>(null);
  const load=async()=>{setPlugins(await a.plugins());setDiag(await a.diagnostics());};useEffect(()=>{load().catch(()=>{})},[]);
  const metric=async()=>{if(selectedRun)setResult(await execute(()=>a.runMetricPlugin('example_metric',selectedRun),false));};
  return <div className="page"><section className="title compact"><div className="eyebrow">ENGINEERING · WORKBENCH 1.0.1 / V5</div><h2>Integrity, plugin contracts and diagnostics.</h2></section><div className="studio-grid"><section className="panel"><h3>Diagnostics</h3><pre className="inspector">{JSON.stringify(diag,null,2)}</pre><button onClick={load}>Refresh / verify</button></section><section className="panel"><h3>Plugin SDK</h3><pre className="inspector">{JSON.stringify(plugins,null,2)}</pre>{selectedRun&&<button className="primary" onClick={metric}>Run example metric</button>}<pre className="inspector">{result?JSON.stringify(result,null,2):''}</pre></section></div></div>;
}

function ExperimentsPage({projectId,execute}:any){
  const a:any=api;
  const [items,setItems]=useState<any[]>([]);
  const [selected,setSelected]=useState('');
  const [detail,setDetail]=useState<any>(null);
  const [runDetail,setRunDetail]=useState<any>(null);
  const [title,setTitle]=useState('Ethomorphism M19 Verification');
  const [seed,setSeed]=useState(1901);
  const load=async()=>{
    if(!projectId){setItems([]);return;}
    const xs=await a.experiments(projectId); setItems(xs);
    const id=selected || xs[0]?.experiment_id || '';
    if(id){setSelected(id); const d=await a.experimentDetail(id); setDetail(d); const runs=d.runs||[]; if(runs.length)setRunDetail(await a.experimentRun(runs[runs.length-1].experiment_run_id));}
  };
  useEffect(()=>{load().catch(()=>{});},[projectId,selected]);
  const freeze=async()=>{const x=await execute(()=>a.freezeExperiment({project_id:projectId,title,seed,state_dim:16,noise_concepts:16}),false);setSelected(x.experiment_id);await load();};
  const run=async()=>{if(!selected)return;const r=await execute(()=>a.runExperiment(selected),false);setRunDetail(await a.experimentRun(r.experiment_run_id));await load();};
  const verify=async()=>{if(!runDetail?.record?.experiment_run_id)return;await execute(()=>a.verifyExperiment(runDetail.record.experiment_run_id),false);setRunDetail(await a.experimentRun(runDetail.record.experiment_run_id));};
  return <div className="page"><section className="title compact"><div className="eyebrow">EXPERIMENT MANAGER · WORKBENCH 1.0.1</div><h2>Freeze, run and reproduce the protocol.</h2><p>.vexp artifacts lock inputs and assertions; completed results can be verified by rerunning the same scientific protocol.</p></section><div className="studio-grid"><section className="panel"><div className="panel-head"><h3>Author / freeze</h3><span>ethomorphism.m19.v1</span></div><label>Title<input value={title} onChange={e=>setTitle(e.target.value)}/></label><label>Seed<input type="number" value={seed} onChange={e=>setSeed(Number(e.target.value))}/></label><button className="primary" disabled={!projectId} onClick={freeze}>Freeze .vexp</button><div className="curr-list">{items.map(x=><button className={`curr-row ${selected===x.experiment_id?'selected':''}`} key={x.experiment_id} onClick={()=>setSelected(x.experiment_id)}><div><strong>{x.title} @{x.version}</strong><small>{x.protocol_id}</small></div><code>{short(x.artifact_sha256)}</code></button>)}</div>{selected&&<button className="primary" onClick={run}>RUN EXPERIMENT</button>}</section><section className="panel"><div className="panel-head"><h3>Manifest / verification</h3><span>{detail?short(detail.record.manifest_sha256):'—'}</span></div><pre className="inspector">{detail?JSON.stringify(detail.manifest,null,2):'No experiment selected.'}</pre>{runDetail?.record?.status==='completed'&&<button className="primary" onClick={verify}>VERIFY BY REPRODUCTION</button>}<pre className="inspector">{runDetail?JSON.stringify({record:runDetail.record,verification:runDetail.verification,assertions:runDetail.assertions},null,2):'No experiment result yet.'}</pre></section></div></div>;
}

function OrganismPage(props:any){
  const {projects,runs,projectId,setProjectId,selectedRun,setSelectedRun,status,newProject,setNewProject,createProject,createRun,runSeed,setRunSeed,runDim,setRunDim,runLabel,setRunLabel,reopen,busy}=props;
  return <div className="page">
    <section className="title"><div className="eyebrow">ORGANISM / LAB HOME</div><h2>Operate a lineage, not a session.</h2><p>Projects and runs are Workbench laboratory identity. Canonical cognition remains inside verified Verdant checkpoints.</p></section>
    <div className="two-col">
      <section className="panel"><div className="panel-head"><h3>Projects & runs</h3><span>{runs.length} runs</span></div>
        <div className="row gap"><select value={projectId} onChange={e=>setProjectId(e.target.value)}><option value="">Select project</option>{projects.map((p:Project)=><option key={p.project_id} value={p.project_id}>{p.name}</option>)}</select><input value={newProject} onChange={e=>setNewProject(e.target.value)}/><button onClick={createProject} disabled={busy}>New project</button></div>
        <div className="run-list">{runs.filter((r:RunRecord)=>!projectId||r.project_id===projectId).map((r:RunRecord)=><button key={r.run_id} className={`run-row ${selectedRun===r.run_id?'selected':''}`} onClick={()=>setSelectedRun(r.run_id)}><div><strong>{r.run_id}</strong><small>{r.status} · cycle {r.latest_cycle} · rev {r.latest_state_revision}</small></div><code>{short(r.latest_fingerprint)}</code></button>)}{!runs.length&&<div className="empty">No runs yet.</div>}</div>
      </section>
      <section className="panel"><div className="panel-head"><h3>Create organism</h3><span>explicit configuration</span></div>
        <label>Seed<input type="number" value={runSeed} onChange={e=>setRunSeed(Number(e.target.value))}/></label>
        <label>Field dimension<input type="number" value={runDim} onChange={e=>setRunDim(Number(e.target.value))}/></label>
        <label>Run label<input value={runLabel} onChange={e=>setRunLabel(e.target.value)}/></label>
        <button className="primary wide" onClick={createRun} disabled={busy||!projectId}>Create & load Verdant</button>
      </section>
    </div>
    {status&&<section className="panel status-panel"><div className="panel-head"><h3>Selected organism</h3><span>{status.worker_alive?'authoritative worker active':'checkpoint only'}</span></div><MetricGrid status={status}/>{!status.worker_alive&&<button className="primary" onClick={reopen} disabled={busy||!status.head_checkpoint_id}>Reopen from head checkpoint</button>}</section>}
  </div>;
}

function CultivatePage(props:any){
  const {status,queue,events,context,setContext,lesson,setLesson,probe,setProbe,checkpointLabel,setCheckpointLabel,queueLesson,teachNow,probeNow,save,fork,busy,selectedRun,execute,cursor}=props;
  if(!selectedRun) return <div className="page"><section className="title"><h2>Select or create an organism first.</h2></section></div>;
  const running=status?.execution?.state==='running';
  return <div className="page cultivate">
    <section className="title compact"><div className="eyebrow">LIVE CULTIVATION</div><h2>Teach, queue, run, observe.</h2><p>STEP executes one queued command item. It is not a fabricated no-input cognitive tick.</p></section>
    <MetricGrid status={status}/>
    <section className="toolbar panel">
      <div className="control-group"><button className="run" disabled={busy||running} onClick={()=>execute(()=>api.start(selectedRun))}>▶ RUN</button><button disabled={busy} onClick={()=>execute(()=>api.pause(selectedRun))}>Ⅱ PAUSE</button><button disabled={busy||running} onClick={()=>execute(()=>api.step(selectedRun))}>STEP ITEM</button><button className="danger" disabled={busy} onClick={()=>execute(()=>api.stop(selectedRun))}>■ STOP</button></div>
      <div className="state-readout"><span>EXECUTION</span><strong>{status?.execution?.state||'—'}</strong><small>{status?.execution?.queue_counts?.queued||0} queued · cursor {cursor}</small></div>
    </section>
    <div className="cult-grid">
      <div className="stack">
        <section className="panel"><div className="panel-head"><h3>Teaching input</h3><span>human-authored primitives</span></div><label>Context<input value={context} onChange={e=>setContext(e.target.value)}/></label><label>Labels / primitive symbols<textarea rows={4} value={lesson} onChange={e=>setLesson(e.target.value)}/></label><div className="row"><button className="primary" disabled={busy||!lesson.trim()} onClick={queueLesson}>Add to queue</button><button disabled={busy||running||!lesson.trim()} onClick={teachNow}>Teach now</button></div></section>
        <section className="panel"><div className="panel-head"><h3>Probe</h3><span>bounded compilation probe</span></div><div className="row"><input value={probe} onChange={e=>setProbe(e.target.value)}/><button disabled={busy||running||!probe.trim()} onClick={probeNow}>Probe now</button><button disabled={busy||!probe.trim()} onClick={()=>execute(()=>api.queueProbe(selectedRun,words(probe)))}>Queue probe</button></div></section>
        <section className="panel"><div className="panel-head"><h3>Checkpoint / fork</h3><span>{status?.dirty?'unsaved state differs from checkpoint':'head matches live state'}</span></div><div className="row"><input placeholder="checkpoint label (optional)" value={checkpointLabel} onChange={e=>setCheckpointLabel(e.target.value)}/><button disabled={busy||!status?.worker_alive} onClick={save}>Save checkpoint</button><button disabled={busy||!status?.head_checkpoint_id} onClick={fork}>Fork head</button></div><small className="muted">Head: {status?.head_checkpoint_id||'none'} · saved cycle {status?.saved_cycle??'—'}</small></section>
      </div>
      <div className="stack">
        <section className="panel queue-panel"><div className="panel-head"><h3>Command queue</h3><span>persistent execution order</span></div><div className="queue-list">{queue.slice(-20).map((q:QueueItem)=><div className="queue-row" key={q.queue_item_id}><span className={`qstatus ${q.status}`}>{q.status}</span><strong>#{q.sequence_no} {q.command_type}</strong><small>{q.command_type==='TEACH' ? `${(q.payload.labels as string[]||[]).join(' ')} · ${q.payload.context_id||''}` : (q.payload.cue_labels as string[]||[]).join(' ')}</small></div>)}{!queue.length&&<div className="empty">Queue is empty. Add teaching items, then RUN or STEP ITEM.</div>}</div></section>
        <section className="panel event-panel"><div className="panel-head"><h3>Committed event stream</h3><span>{events.length} buffered · {status?.descriptor?`cycle ${status.descriptor.cycle}`:'offline'}</span></div><div className="event-list">{[...events].reverse().map((ev:EventEnvelope)=><div className="event-row" key={ev.event_id}><span className={`prov ${provenance(ev.event_type).toLowerCase()}`}>{provenance(ev.event_type)}</span><div><strong>{ev.event_type}</strong><small>cycle {ev.engine_cycle} · rev {ev.state_revision} · {short(ev.event_id,18)}</small></div></div>)}{!events.length&&<div className="empty">Waiting for recorded events…</div>}</div></section>
      </div>
    </div>
  </div>;
}

function MetricGrid({status}:{status:RunStatus|null}){
  const m:any=status?.metrics||{};
  const cards=[['Cycle',status?.descriptor?.cycle??status?.run?.latest_cycle??'—'],['Revision',status?.descriptor?.state_revision??status?.run?.latest_state_revision??'—'],['Concepts',m.concept_count??'—'],['Relations',m.relation_count??'—'],['Plastic',m.plasticity_association_count??'—'],['P structures',m.promoted_structure_count??'—'],['Q structures',m.layered_structure_count??'—'],['Workspace',m.workspace_active_item_count??'—']];
  return <div className="metrics">{cards.map(([k,v])=><div className="metric" key={k as string}><span>{k}</span><strong>{String(v)}</strong></div>)}</div>;
}


function CurriculumPage({projectId,selectedRun,runStateDim,execute}:any){
  const a:any=api;
  const [studioMode,setStudioMode]=useState<'manual'|'pack'>('manual');
  const [title,setTitle]=useState('New Curriculum');
  const [format,setFormat]=useState('primitive_lines');
  const [stateDim,setStateDim]=useState(runStateDim||128);
  const [source,setSource]=useState(`# Explicit curriculum\nPRESENCE lesson-1 kren tar vel\nEDGE lesson-1 kren linked tar | weight=0.8\nEDGE lesson-1 tar linked vel | weight=0.8\n`);
  const [preview,setPreview]=useState<any>(null);
  const [curricula,setCurricula]=useState<any[]>([]);
  const [selected,setSelected]=useState('');
  const [baseline,setBaseline]=useState('');
  const [builder,setBuilder]=useState({
    itemId:'lesson-001', contextId:'manual', sentence:'The kren moves toward the tar.',
    concepts:'kren\ntar', relations:'kren | moves_toward | tar | true | 0.8 | 1.0', claims:'',
    grammar:'{"subject":"kren","predicate":"move","relation":"toward","object":"tar"}',
    lexicon:'[{"surface":"kren","role":"noun"},{"surface":"moves","lemma":"move","role":"verb"},{"surface":"toward","role":"relation"},{"surface":"tar","role":"noun"}]',
    provenance:'{"author":"human"}', scaffoldRules:'transitive_svo', scaffoldLexicon:'the | determiner | the\nmove | verb | move,moves,moved'
  });
  const defaultPack=JSON.stringify({
    schema:'verdant.curriculum.pack.v1',
    title:'New Curriculum Pack',
    description:'Organize many explicit teaching records into selectable, reusable sections.',
    state_dim:Number(runStateDim||128),
    language_scaffold:{grammar_rules:[],lexicon:[],notes:''},
    sections:[
      {section_id:'physics',title:'Physical World',description:'Example section. Replace or extend items in bulk.',enabled:true,language_scaffold:{grammar_rules:[],lexicon:[],notes:''},items:[
        {item_id:'physics-001',context_id:'physics',source_text:'Gravity pulls objects with mass downward.',concepts:[{label:'gravity'},{label:'mass'},{label:'pulls'},{label:'downward'}],relations:[{source:'gravity',relation:'linked',target:'mass',directed:true,weight:0.8,confidence:1.0},{source:'gravity',relation:'linked',target:'pulls',directed:true,weight:0.9,confidence:1.0},{source:'pulls',relation:'linked',target:'downward',directed:true,weight:0.7,confidence:1.0}],claims:[],confidence:1.0,provenance:{author:'human',source:'curriculum-pack-template'},grammar_annotation:{},lexicon_annotation:[]}
      ],tests:[{test_id:'physics-probe-001',cue_labels:['gravity','mass'],notes:'Recorded structure-use probe after cultivation.'}]}
    ],
    notes:'Curriculum packs are Workbench organization. Selected sections are flattened into verdant.teaching.bundle.v1 before compilation.'
  },null,2);
  const [packText,setPackText]=useState(defaultPack);
  const [pack,setPack]=useState<any>(null);
  const [selectedSections,setSelectedSections]=useState<string[]>([]);
  const [packPreview,setPackPreview]=useState<any>(null);
  const fileRef=useRef<HTMLInputElement>(null);

  const refresh=async()=>{ if(projectId) setCurricula(await a.curricula(projectId)); else setCurricula([]); };
  useEffect(()=>{refresh().catch(()=>{});},[projectId]);
  const body=()=>({project_id:projectId,title,source_format:format,source_text:source,state_dim:Number(stateDim),baseline_curriculum_id:baseline||null});
  const compile=async()=>setPreview(await execute(()=>a.compileCurriculum(body()),false));
  const freeze=async()=>{const out=await execute(()=>a.freezeCurriculum({...body(),expected_compiled_sha256:preview?.compiled_sha256||null}),false);setSelected(out.curriculum_id);await refresh();};
  const loadTemplate=async()=>{const t=await execute(()=>a.curriculumTemplateM19(),false);setTitle(t.title);setFormat(t.source_format);setStateDim(t.state_dim);setSource(t.source_text);setPreview(null);setStudioMode('manual');};
  const loadEditable=async()=>{const t=await execute(()=>a.curriculumTemplateEditable(),false);setTitle(t.title);setFormat(t.source_format);setStateDim(t.state_dim);setSource(t.source_text);setPreview(null);setStudioMode('manual');};
  const loadFrozen=async()=>{if(!selected)return;const d=await execute(()=>a.curriculumDetail(selected),false);setTitle(d.record.title);setFormat(d.record.source_format);setStateDim(d.record.state_dim);setSource(d.source_text);setPreview(null);setStudioMode('manual');};
  const queue=async()=>{if(selectedRun&&selected)await execute(()=>a.queueCurriculum(selectedRun,selected));};
  const lines=(raw:string)=>raw.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
  const buildBundle=()=>{
    const parseJson=(raw:string,fallback:any)=>{try{return raw.trim()?JSON.parse(raw):fallback}catch{throw new Error('Builder JSON field is invalid.')}};
    const grammarRules=builder.scaffoldRules.split(',').map(x=>x.trim()).filter(Boolean);
    const lexicon=lines(builder.scaffoldLexicon).map(line=>{const [lemma,category,forms]=line.split('|').map(x=>x.trim());if(!lemma||!category||!forms)throw new Error('Scaffold lexicon lines use: lemma | category | form1,form2');return {lemma,category,forms:forms.split(',').map(x=>x.trim()).filter(Boolean),attributes:{}}});
    const concepts=lines(builder.concepts).map(line=>{const [label,attrs]=line.split('|',2).map(x=>x.trim());return {label,attributes:attrs?parseJson(attrs,{}):{}}});
    const relations=lines(builder.relations).map(line=>{const [src,rel,tgt,directed='true',weight='0.8',confidence='1.0']=line.split('|').map(x=>x.trim());if(!src||!rel||!tgt)throw new Error('Relation lines use: source | relation | target | directed | weight | confidence');return {source:src,relation:rel,target:tgt,directed:directed.toLowerCase()!=='false',weight:Number(weight),confidence:Number(confidence)}});
    const claims=lines(builder.claims).map(line=>{const [subject,predicate,object,polarity='affirmed',source_class='human_testimony',confidence='1.0']=line.split('|').map(x=>x.trim());if(!subject||!predicate||!object)throw new Error('Claim lines use: subject | predicate | object | polarity | source_class | confidence');return {subject,predicate,object,polarity,source_class,confidence:Number(confidence),rationale:'',attributes:{}}});
    const bundle={schema:'verdant.teaching.bundle.v1',language_scaffold:{grammar_rules:grammarRules,lexicon,notes:'Explicit author-supplied language scaffold.'},items:[{item_id:builder.itemId,context_id:builder.contextId,source_text:builder.sentence,concepts,relations,claims,confidence:1.0,provenance:parseJson(builder.provenance,{}),grammar_annotation:parseJson(builder.grammar,{}),lexicon_annotation:parseJson(builder.lexicon,[])}],notes:'Source text and annotations are not interpreted automatically; concepts/relations/claims are the explicit teaching plan.'};
    setFormat('teaching_bundle_json');setSource(JSON.stringify(bundle,null,2));setPreview(null);setStudioMode('manual');
  };

  const parsePack=(raw:string)=>{
    let value:any;
    try{value=JSON.parse(raw);}catch{throw new Error('Curriculum Pack JSON is invalid.');}
    if(value?.schema!=='verdant.curriculum.pack.v1')throw new Error("Curriculum Pack must declare schema 'verdant.curriculum.pack.v1'.");
    if(!Array.isArray(value.sections)||!value.sections.length)throw new Error('Curriculum Pack needs at least one section.');
    const ids=value.sections.map((x:any)=>String(x.section_id||''));
    if(ids.some((x:string)=>!x))throw new Error('Every pack section needs section_id.');
    if(new Set(ids).size!==ids.length)throw new Error('Curriculum Pack section_id values must be unique.');
    for(const section of value.sections){if(!Array.isArray(section.items)||!section.items.length)throw new Error(`Section ${section.section_id} needs at least one teaching item.`);}
    return value;
  };
  const loadPack=(raw=packText)=>{const value=parsePack(raw);setPack(value);setPackText(JSON.stringify(value,null,2));setSelectedSections(value.sections.filter((x:any)=>x.enabled!==false).map((x:any)=>x.section_id));setPackPreview(null);};
  const importPack=async(file:File)=>{const raw=await file.text();loadPack(raw);};
  const exportPack=()=>{const value=parsePack(packText);const blob=new Blob([JSON.stringify(value,null,2)+'\n'],{type:'application/json'});const url=URL.createObjectURL(blob);const link=document.createElement('a');const slug=String(value.title||'curriculum-pack').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')||'curriculum-pack';link.href=url;link.download=`${slug}.vcpack`;document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(url);};
  const packRequest=(ids=selectedSections)=>({project_id:projectId,pack_text:packText,selected_section_ids:ids,baseline_curriculum_id:baseline||null});
  const compilePack=async(ids=selectedSections)=>{
    if(!projectId)throw new Error('Create or select a project first.');
    if(!pack)loadPack(packText);
    const out=await execute(()=>a.compileCurriculumPack(packRequest(ids)),false);
    setPackPreview(out);setTitle(out.curriculum.title);setFormat('teaching_bundle_json');setStateDim(out.curriculum.state_dim);setSource(out.bundle_source_text);setPreview(out.curriculum);
    return out;
  };
  const freezePack=async(ids=selectedSections)=>{
    const out=await compilePack(ids);
    const frozen=await execute(()=>a.freezeCurriculumPack({...packRequest(ids),expected_compiled_sha256:out.curriculum.compiled_sha256}),false);
    setSelected(frozen.curriculum_id);await refresh();return {out,frozen};
  };
  const queuePack=async(ids=selectedSections,start=false,withTests=false)=>{
    if(!selectedRun)throw new Error('Select an organism before queueing a curriculum pack.');
    const {out,frozen}=await freezePack(ids);
    await execute(()=>a.queueCurriculum(selectedRun,frozen.curriculum_id),false);
    if(withTests){for(const test of (out.tests||[])){await execute(()=>a.queueProbe(selectedRun,test.cue_labels||[]),false);}}
    if(start)await execute(()=>a.start(selectedRun),false);
    return out;
  };
  const toggleSection=(id:string,checked:boolean)=>setSelectedSections(prev=>checked?[...prev.filter(x=>x!==id),id]:prev.filter(x=>x!==id));
  const packSections=pack?.sections||[];
  const selectedItemCount=packSections.filter((x:any)=>selectedSections.includes(x.section_id)).reduce((n:number,x:any)=>n+(x.items?.length||0),0);
  const selectedTestCount=packSections.filter((x:any)=>selectedSections.includes(x.section_id)).reduce((n:number,x:any)=>n+(x.tests?.length||0),0);

  return <div className="page">
    <section className="title compact"><div className="eyebrow">CURRICULUM STUDIO · WB-11</div><h2>Hand-author one record or cultivate from a whole curriculum pack.</h2><p>The manual builder stays available. Curriculum Packs add bulk organization, section selection, import/export and batch execution while still flattening through the same reviewed <code>verdant.teaching.bundle.v1</code> compiler path.</p></section>
    <section className="panel"><div className="panel-head"><h3>Authoring mode</h3><span>same canonical compiler underneath</span></div><div className="row wrap"><button className={studioMode==='manual'?'primary':''} onClick={()=>setStudioMode('manual')}>Manual Builder</button><button className={studioMode==='pack'?'primary':''} onClick={()=>setStudioMode('pack')}>Curriculum Packs</button></div></section>

    {studioMode==='manual'?<section className="panel teaching-builder"><div className="panel-head"><h3>Editable Teaching Record Builder</h3><span>precision tool · no hidden parser</span></div>
      <div className="builder-grid">
        <label>Source sentence<textarea rows={2} value={builder.sentence} onChange={e=>setBuilder({...builder,sentence:e.target.value})}/></label>
        <label>Item / context<div className="row"><input value={builder.itemId} onChange={e=>setBuilder({...builder,itemId:e.target.value})}/><input value={builder.contextId} onChange={e=>setBuilder({...builder,contextId:e.target.value})}/></div></label>
        <label>Concepts <small>one per line: label | optional JSON attributes</small><textarea rows={5} value={builder.concepts} onChange={e=>setBuilder({...builder,concepts:e.target.value})}/></label>
        <label>Relations <small>source | relation | target | directed | weight | confidence</small><textarea rows={5} value={builder.relations} onChange={e=>setBuilder({...builder,relations:e.target.value})}/></label>
        <label>Claims / contradictions <small>subject | predicate | object | polarity | source_class | confidence</small><textarea rows={4} value={builder.claims} onChange={e=>setBuilder({...builder,claims:e.target.value})}/></label>
        <label>Grammar annotation JSON<textarea rows={4} value={builder.grammar} onChange={e=>setBuilder({...builder,grammar:e.target.value})}/></label>
        <label>Lexicon annotation JSON<textarea rows={4} value={builder.lexicon} onChange={e=>setBuilder({...builder,lexicon:e.target.value})}/></label>
        <label>Provenance JSON<textarea rows={4} value={builder.provenance} onChange={e=>setBuilder({...builder,provenance:e.target.value})}/></label>
        <label>Executable parser scaffold rules <small>existing engine rule IDs, comma separated</small><input value={builder.scaffoldRules} onChange={e=>setBuilder({...builder,scaffoldRules:e.target.value})}/></label>
        <label>Executable scaffold lexicon <small>lemma | category | forms</small><textarea rows={4} value={builder.scaffoldLexicon} onChange={e=>setBuilder({...builder,scaffoldLexicon:e.target.value})}/></label>
      </div>
      <div className="row wrap"><button className="primary" onClick={buildBundle}>Build editable bundle source</button><button onClick={loadEditable}>Load full editable template</button><span className="muted inline-note">False, fictional or mutually contradictory teaching is allowed. The validator checks schema, not truth.</span></div>
    </section>:
    <section className="panel"><div className="panel-head"><h3>Curriculum Pack Builder / Loader</h3><span>verdant.curriculum.pack.v1</span></div>
      <p className="muted">A pack is organization only. Selected sections are deterministically flattened into the existing editable teaching-bundle format before they can reach Verdant.</p>
      <input ref={fileRef} type="file" accept=".vcpack,.json,application/json" style={{display:'none'}} onChange={e=>{const f=e.target.files?.[0];if(f)importPack(f).catch(err=>{throw err;});e.currentTarget.value='';}}/>
      <div className="row wrap"><button onClick={()=>fileRef.current?.click()}>Import .vcpack / JSON</button><button onClick={()=>loadPack(packText)}>Load / validate pasted pack</button><button onClick={exportPack}>Export .vcpack</button><button onClick={()=>{setPackText(defaultPack);setPack(null);setSelectedSections([]);setPackPreview(null)}}>New pack template</button></div>
      <label>Pack JSON<textarea className="codearea" rows={16} value={packText} onChange={e=>{setPackText(e.target.value);setPack(null);setPackPreview(null)}}/></label>
      {pack&&<><div className="panel-head subhead"><h3>{pack.title}</h3><span>{packSections.length} sections · {selectedItemCount} selected items · {selectedTestCount} probes</span></div>
        <div className="curr-list">{packSections.map((section:any)=><div className="curr-row" key={section.section_id}><div style={{flex:1}}><label className="row gap"><input type="checkbox" checked={selectedSections.includes(section.section_id)} onChange={e=>toggleSection(section.section_id,e.target.checked)}/><strong>{section.title}</strong></label><small>{section.section_id} · {section.items?.length||0} teaching items · {section.tests?.length||0} probes</small><small>{section.description||''}</small></div><div className="row wrap"><button onClick={()=>compilePack([section.section_id])}>Preview</button><button onClick={()=>freezePack([section.section_id])}>Freeze</button><button disabled={!selectedRun} onClick={()=>queuePack([section.section_id],false,false)}>Queue</button><button className="primary" disabled={!selectedRun} onClick={()=>queuePack([section.section_id],true,true)}>Run + probes</button></div></div>)}</div>
        <div className="row wrap"><button onClick={()=>setSelectedSections(packSections.map((x:any)=>x.section_id))}>Select all</button><button onClick={()=>setSelectedSections([])}>Select none</button><button className="primary" disabled={!selectedSections.length} onClick={()=>compilePack()}>Compile selected</button><button disabled={!selectedSections.length} onClick={()=>freezePack()}>Freeze selected .vcurr</button><button disabled={!selectedRun||!selectedSections.length} onClick={()=>queuePack(selectedSections,false,false)}>Queue selected</button><button className="primary" disabled={!selectedRun||!selectedSections.length} onClick={()=>queuePack(selectedSections,true,true)}>Run selected + probes</button></div>
        <div className="callout">Batch execution queues the frozen curriculum through the normal run queue. “Run + probes” appends each selected section's test cues as ordinary recorded probes; it does not manufacture a pass/fail score.</div>
      </>}
    </section>}

    <div className="studio-grid">
      <div className="stack">
        <section className="panel"><div className="panel-head"><h3>Canonical authoring source</h3><span>{format}</span></div>
          <div className="row"><input value={title} onChange={e=>setTitle(e.target.value)}/><select value={format} onChange={e=>setFormat(e.target.value)}><option value="teaching_bundle_json">Editable teaching bundle JSON</option><option value="primitive_lines">Primitive lines</option><option value="experience_jsonl">ExperienceCommand JSONL</option></select><input type="number" value={stateDim} onChange={e=>setStateDim(Number(e.target.value))}/></div>
          <label>Source<textarea className="codearea" rows={18} value={source} onChange={e=>setSource(e.target.value)}/></label>
          <div className="row wrap"><button onClick={loadTemplate}>Load M19 reference</button><button className="primary" onClick={compile}>Compile preview</button><button disabled={!preview} onClick={freeze}>Freeze reviewed .vcurr</button></div>
          {preview&&<small className="muted">source {short(preview.source_sha256,20)} · compiled {short(preview.compiled_sha256,20)} · {preview.item_count} experiences · {preview.scaffold_item_count||0} scaffold items</small>}
          {packPreview&&<pre className="inspector">{JSON.stringify({pack:packPreview.pack,selected_sections:packPreview.selected_sections,tests:packPreview.tests},null,2)}</pre>}
        </section>
        <section className="panel"><div className="panel-head"><h3>Frozen curricula</h3><span>immutable project artifacts</span></div>
          <div className="curr-list">{curricula.map(c=><button key={c.curriculum_id} className={`curr-row ${selected===c.curriculum_id?'selected':''}`} onClick={()=>setSelected(c.curriculum_id)}><div><strong>{c.title} @{c.version}</strong><small>{c.item_count} experiences · {c.source_format}</small></div><code>{short(c.compiled_sha256)}</code></button>)}{!curricula.length&&<div className="empty">No frozen curricula in this project.</div>}</div>
          {selected&&<div className="row gap"><button onClick={loadFrozen}>Load frozen source</button><button className="primary" disabled={!selectedRun} onClick={queue}>Queue into selected run</button><button onClick={()=>{setBaseline(selected);setPreview(null)}}>Use as diff baseline</button></div>}
        </section>
      </div>
      <div className="stack">
        <section className="panel"><div className="panel-head"><h3>Language scaffold</h3><span>explicit executable grammar / lexicon only</span></div><pre className="inspector">{preview?JSON.stringify(preview.language_scaffold,null,2):'Editable bundles may optionally teach the existing parser scaffold before world-teaching items.'}</pre></section>
        <section className="panel"><div className="panel-head"><h3>Parsed</h3><span>compiler interpretation</span></div><pre className="inspector">{preview?JSON.stringify(preview.parsed_items,null,2):'Compile source to inspect parsed items.'}</pre></section>
        <section className="panel"><div className="panel-head"><h3>Compiled</h3><span>exact engine commands</span></div><pre className="inspector tall">{preview?.compiled_jsonl||'No compiled commands yet.'}</pre></section>
        <section className="panel"><div className="panel-head"><h3>Diff</h3><span>{baseline?'against frozen baseline':'no baseline selected'}</span></div><pre className="inspector">{preview?.diff_from_baseline||'Select a frozen curriculum as baseline and compile again.'}</pre></section>
      </div>
    </div>
  </div>;
}

function GrammarPage({selectedRun,status,execute,refreshRun}:any){
  const a:any=api;
  const [grammar,setGrammar]=useState<any>(null);
  const [sentence,setSentence]=useState('dog chases child.');
  const [eventKey,setEventKey]=useState('grammar-preview-001');
  const [preview,setPreview]=useState<any>(null);
  const [lemma,setLemma]=useState('dog');
  const [category,setCategory]=useState('noun');
  const [forms,setForms]=useState('dog');
  const load=async()=>{if(selectedRun)setGrammar(await a.grammar(selectedRun));};
  useEffect(()=>{load().catch(()=>{});},[selectedRun]);
  if(!selectedRun)return <div className="page"><section className="title"><h2>Select an active organism for the Grammar Lab.</h2></section></div>;
  const teachRule=async(ruleId:string)=>{await execute(()=>a.teachGrammarRule(selectedRun,ruleId,status?.descriptor?.state_revision));await load();};
  const teachLexeme=async()=>{await execute(()=>a.teachLexeme(selectedRun,lemma,category,forms.split(',').map((x:string)=>x.trim()).filter(Boolean),status?.descriptor?.state_revision));await load();};
  const inspect=async()=>setPreview(await execute(()=>a.grammarPreview(selectedRun,sentence,eventKey),false));
  const teachSentence=async()=>{await execute(()=>a.teachSentence(selectedRun,sentence,eventKey,status?.descriptor?.state_revision));await load();await refreshRun();};
  return <div className="page">
    <section className="title compact"><div className="eyebrow">LANGUAGE / GRAMMAR LAB</div><h2>Teach rules explicitly. Preview semantics without mutation.</h2><p>This is the existing deterministic, evidence-gated grammar path exposed as a laboratory instrument.</p></section>
    <div className="grammar-grid">
      <div className="stack">
        <section className="panel"><div className="panel-head"><h3>Grammar rules</h3><span>teacher-supplied scaffold</span></div><div className="rule-list">{(grammar?.rules||[]).map((r:any)=><div className="rule-row" key={r.rule_id}><div><strong>{r.rule_id}</strong><small>{r.pattern} · {r.enabled?'ENABLED':'not taught'}</small></div><button disabled={r.enabled} onClick={()=>teachRule(r.rule_id)}>Teach rule</button></div>)}</div></section>
        <section className="panel"><div className="panel-head"><h3>Lexicon</h3><span>{grammar?.lexicon?.length||0} recognized forms</span></div><div className="row"><input value={lemma} onChange={e=>setLemma(e.target.value)}/><select value={category} onChange={e=>setCategory(e.target.value)}><option>noun</option><option>verb</option><option>adjective</option><option>determiner</option><option>copula</option><option>negator</option><option>temporal_marker</option></select><input value={forms} onChange={e=>setForms(e.target.value)}/><button onClick={teachLexeme}>Teach lexeme</button></div><div className="lex-list">{(grammar?.lexicon||[]).map((x:any)=><span key={`${x.form}:${x.category}`}><strong>{x.form}</strong> → {x.lemma} <em>{x.category}</em></span>)}</div></section>
      </div>
      <div className="stack">
        <section className="panel"><div className="panel-head"><h3>Parse / semantic-plan preview</h3><span>pure inspection</span></div><textarea rows={3} value={sentence} onChange={e=>setSentence(e.target.value)}/><div className="row gap"><input value={eventKey} onChange={e=>setEventKey(e.target.value)}/><button className="primary" onClick={inspect}>Preview only</button><button onClick={teachSentence}>Teach reviewed sentence</button></div><pre className="inspector tall">{preview?JSON.stringify(preview,null,2):'Preview a sentence. The adapter verifies preview does not change fingerprint or revision.'}</pre></section>
        <section className="panel"><div className="panel-head"><h3>Enabled state</h3><span>cycle {grammar?.cycle??'—'} · rev {grammar?.state_revision??'—'}</span></div><code className="blockcode">{(grammar?.enabled_rules||[]).join('\n')||'No grammar rules enabled.'}</code></section>
      </div>
    </div>
  </div>;
}

function ForensicPage({selectedRun,status,execute,mode}:any){
  const a:any=api;
  const [index,setIndex]=useState<any>(null);
  const [selected,setSelected]=useState('');
  const [detail,setDetail]=useState<any>(null);
  const [replay,setReplay]=useState<any>(null);
  const [graph,setGraph]=useState<any>(null);
  const [causal,setCausal]=useState<any>(null);
  const [qQuery,setQQuery]=useState('');
  const [qExpectation,setQExpectation]=useState<'family_match'|'negative_control'>('family_match');
  const load=async()=>{
    if(!selectedRun)return;
    const idx=await a.structures(selectedRun); setIndex(idx);
    if(
      (!qQuery || !idx.p_structures?.some((item:any)=>item.id===qQuery))
      && idx.p_structures?.[0]
    ) setQQuery(idx.p_structures[0].id);
    const all=[...(idx.p_structures||[]),...(idx.q_structures||[])];
    const sid=selected&&all.some((x:any)=>x.id===selected)?selected:(all[0]?.id||'');
    if(sid){ setSelected(sid); setDetail(await a.structureDetail(selectedRun,sid)); setGraph(await a.structureGraph(selectedRun,sid)); }
  };
  useEffect(()=>{load().catch(()=>{});},[selectedRun]);
  useEffect(()=>{
    let cancelled=false;
    if(selectedRun&&selected){
      setDetail(null);setGraph(null);
      Promise.all([a.structureDetail(selectedRun,selected),a.structureGraph(selectedRun,selected)])
        .then(([d,g]:any)=>{if(!cancelled){setDetail(d);setGraph(g);}})
        .catch(()=>{});
    }
    return()=>{cancelled=true;};
  },[selectedRun,selected]);
  if(!selectedRun)return <div className="page"><section className="title"><h2>Select an active organism first.</h2></section></div>;
  const objects=[...(index?.p_structures||[]),...(index?.q_structures||[])];
  const pCandidates=(index?.p_candidates||[]).filter((x:any)=>!x.promoted_structure_id);
  const qCandidates=(index?.q_candidates||[]).filter((x:any)=>!x.promoted_layered_structure_id);
  const runReplay=async()=>setReplay(await a.structureReplay(selectedRun,selected));
  const ablate=async()=>{await execute(()=>a.ablateStructure(selectedRun,selected,status?.descriptor?.state_revision));await load();};
  const restore=async()=>{await execute(()=>a.restoreStructure(selectedRun,selected,status?.descriptor?.state_revision));await load();};
  const interact=async()=>{await execute(()=>a.interactStructure(selectedRun,selected,status?.descriptor?.state_revision));await load();};
  const observeHierarchy=async()=>{await execute(()=>a.observeHierarchy(selectedRun,status?.descriptor?.state_revision));await load();};
  const promoteP=async(id:string)=>{await execute(()=>a.promoteStructure(selectedRun,id,status?.descriptor?.state_revision));await load();};
  const promoteQ=async(id:string)=>{await execute(()=>a.promoteHierarchy(selectedRun,id,status?.descriptor?.state_revision));await load();};
  const compare=async()=>setCausal(await execute(()=>a.causalCompareStructure(selectedRun,selected,detail?.member_concepts?.[0]?.display_label),false));
  const probeQ=async()=>{setCausal(await execute(()=>a.probeHierarchy(selectedRun,selected,qQuery,status?.descriptor?.state_revision),false));await load();};
  const ablateQ=async()=>{await execute(()=>a.ablateHierarchy(selectedRun,selected,status?.descriptor?.state_revision));await load();};
  const restoreQ=async()=>{await execute(()=>a.restoreHierarchy(selectedRun,selected,status?.descriptor?.state_revision));await load();};
  const compareQ=async()=>{setCausal(await execute(()=>a.causalCompareHierarchy(selectedRun,selected,qQuery,qExpectation),false));await load();};
  return <div className="page">
    <section className="title compact"><div className="eyebrow">{mode==='explorer'?'EXPLORER / LIVING VIEW · WORKBENCH 1.0.1':'STRUCTURES / FORENSIC INSPECTOR'}</div><h2>{mode==='explorer'?'Recorded cognition, moving under the glass.':'Trace a manufactured object back to its evidence.'}</h2><p>WB-06 keeps the forensic inspector and adds a record-backed Living Explorer. The dependency-free browser build is the runnable reference UI in this environment.</p></section>
    <div className="forensic-grid"><section className="panel"><div className="panel-head"><h3>P / Q structures</h3><span>{objects.length}</span></div><div className="structure-list">{objects.map((x:any)=><button key={x.id} className={`structure-row ${selected===x.id?'selected':''}`} onClick={()=>setSelected(x.id)}><div><strong>{x.kind} · {x.opaque_name}</strong><small>cycle {x.created_cycle} · {x.member_count} members</small></div><code>{short(x.id,16)}</code></button>)}</div><div className="row wrap"><button className="primary" disabled={(index?.p_structures||[]).length<3} onClick={observeHierarchy}>Observe Q candidates</button><small className="muted">Interact with at least three available P structures, then inspect their verified relationships for a higher-order candidate.</small></div><div className="panel-head subhead"><h3>Promotion candidates</h3><span>explicit operator action</span></div><div className="candidate-list">{pCandidates.map((x:any)=><div className="candidate-row" key={x.id}><div><strong>{x.status}</strong><small>{x.member_labels?.join(', ')}</small></div><button onClick={()=>promoteP(x.id)}>Promote P</button></div>)}{qCandidates.map((x:any)=><div className="candidate-row" key={x.id}><div><strong>Q {x.status}</strong><small>{x.member_count} P members</small></div><button onClick={()=>promoteQ(x.id)}>Promote Q</button></div>)}</div></section>
      <div className="stack">{!detail?<section className="panel"><div className="empty">Loading selected structure…</div></section>:<><section className="panel"><div className="panel-head"><h3>{detail.record?.opaque_name}</h3><span>{detail.available?'AVAILABLE':'DORMANT'}</span></div><code className="blockcode">{detail.id}</code><div className="row wrap">{detail.kind==='P'&&<button onClick={detail.available?ablate:restore}>{detail.available?'Ablate P':'Restore P'}</button>}{detail.kind==='P'&&<button onClick={interact}>Interact</button>}{detail.kind==='P'&&<button onClick={compare}>Causal compare</button>}{detail.kind==='Q'&&<button onClick={detail.available?ablateQ:restoreQ}>{detail.available?'Ablate Q':'Restore Q'}</button>}<button onClick={runReplay}>Replay formation</button></div></section>
      {detail.kind==='Q'&&<section className="panel"><div className="panel-head"><h3>Q causal laboratory</h3><span>present / ablated / restored</span></div><div className="row wrap"><select value={qQuery} onChange={e=>setQQuery(e.target.value)}>{(index?.p_structures||[]).map((p:any)=><option key={p.id} value={p.id}>{p.opaque_name} · {detail.member_structures?.some((m:any)=>m.structure_id===p.id)?'member':'held-out'}</option>)}</select><select value={qExpectation} onChange={e=>setQExpectation(e.target.value as 'family_match'|'negative_control')}><option value="family_match">Expected family match</option><option value="negative_control">Negative control</option></select><button onClick={probeQ} disabled={!qQuery}>Probe Q</button><button className="primary" onClick={compareQ} disabled={!qQuery||!detail.available}>Run controlled comparison</button></div><small className="muted">Choose any P. Member and held-out queries are recorded separately; negative controls must remain outside this Q family.</small></section>}
      {mode==='explorer'?<section className="panel"><div className="panel-head"><h3>Graph payload</h3><span>renderer source</span></div><pre className="inspector tall">{JSON.stringify(graph,null,2)}</pre></section>:<><section className="panel"><div className="panel-head"><h3>Evidence / formation</h3><span>{detail.evidence?.length||0} evidence records</span></div><pre className="inspector tall">{JSON.stringify({quality:detail.record?.quality_at_promotion,lineage:detail.lineage,evidence:detail.evidence,candidate_history:detail.candidate_history},null,2)}</pre></section>{causal&&<section className="panel"><div className="panel-head"><h3>Causal ablation result</h3><span>with / ablate / restore</span></div><pre className="inspector">{JSON.stringify(causal,null,2)}</pre></section>}</>}
      {replay&&<section className="panel"><div className="panel-head"><h3>Replay Formation</h3><span>{replay.mutated?'MUTATION ERROR':'pure inspection'}</span></div><pre className="inspector tall">{JSON.stringify(replay,null,2)}</pre></section>}</>}</div></div>
  </div>;
}
