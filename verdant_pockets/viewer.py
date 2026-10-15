"""Offline HTML replay for a validated pocket lifecycle.

The diagram positions are viewer-chosen, never canonical spatial coordinates.
No network, remote JS, external fonts, or writeback. SVG stays sandboxed in
a single local HTML file; all source labels are inserted as textContent.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .lifecycle import load_lifecycle, validate_lifecycle


_PAGE = r'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Verdant Native Cognitive Pocket Laboratory</title>
<style>
:root{font-family:system-ui,"Segoe UI",sans-serif;color:#dce8fb;background:#0d1525}
*{box-sizing:border-box}body{margin:0;padding:18px;max-width:1500px;margin-inline:auto}
h1{margin:0 0 6px;font-size:25px}p{margin:0 0 12px;color:#aebdd7;line-height:1.5}
small,.sub{color:#a8b8d0}.wrap{display:grid;grid-template-columns:minmax(500px,1.5fr) minmax(280px,.75fr);gap:14px}
.panel{background:#141f33;border:1px solid #2e4461;border-radius:12px;padding:14px;margin-bottom:14px}
.top{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
label{font-size:13px}select,input{background:#21314c;color:#f2f6ff;border:1px solid #5a6f91;border-radius:7px;padding:7px}
input[type=range]{flex:1;min-width:170px}.metric{display:inline-block;margin:6px 14px 4px 0}
.metric strong{font-size:20px;color:#81d9e7}.t{font-size:13px;color:#aebdd7}
svg{width:100%;height:auto;background:#101b2e;border-radius:10px;display:block}
.node{cursor:pointer}hr{border:0;border-top:1px solid #35435e}
#trail{max-height:280px;overflow:auto;white-space:pre-wrap;font-size:12px}
#detail{font-size:13px;overflow-wrap:anywhere;white-space:pre-wrap}
.note{font-size:12px;color:#edca93}code{color:#a5d5d8}
@media(max-width:900px){.wrap{grid-template-columns:1fr}body{padding:10px}}
</style></head><body>
<h1>Verdant Cognitive Pocket Laboratory</h1>
<p>Replay from actual Council-promoted P/Q memories. Local activations and hypothetical links are experimental numeric states, <strong>not native facts, semantic understanding, or evidence of a mind</strong>.</p>
<div class="panel top">
 <label>Stimulated P <select id="source"></select></label>
 <label>Experimental arm <select id="arm"></select></label>
 <label>Round <span id="tick">0</span></label>
 <input id="slider" type="range" min="0" max="8" value="0">
</div>
<div class="wrap"><main>
<div class="panel"><svg id="web" viewBox="0 0 1000 640" aria-label="Cognitive pocket replay"></svg>
<div class="top" style="margin:10px 0 0">
 <span style="color:#86dbf3">● Active / native memory</span>
 <span style="color:#e7b578">● Stimulus</span>
 <span style="color:#bc86ec">━━ Hypothetical role</span>
 <span style="color:#67d69c">━━ Evidenced cross-P</span>
</div></div>
<div class="panel"><strong>Round-level transfer trace</strong><div id="trail"></div></div>
</main><aside>
<div class="panel" id="metrics"></div>
<div class="panel"><strong>Selected concept / edge</strong><hr><div id="detail">Select a node or edge.</div></div>
<div class="panel"><strong>Integrity and scope</strong><hr><div id="scope"></div></div>
</aside></div>
<script>
const DATA=__POCKET_DATA__;
const p=DATA.parent_pocket, c=DATA.matched_cohort;
const labels=Object.fromEntries(p.concepts.map(n=>[n.id,n.label]));
const owners=Object.fromEntries(p.concepts.map(n=>[n.id,n.owner_p_ids]));
const P=Object.fromEntries(p.p_snapshots.map(x=>[x.id,x]));
const source=document.getElementById('source'), arm=document.getElementById('arm'),
slider=document.getElementById('slider'), tick=document.getElementById('tick'),
web=document.getElementById('web'), trail=document.getElementById('trail'),
detail=document.getElementById('detail'), metrics=document.getElementById('metrics'),
scope=document.getElementById('scope');
function option(select,value,name){const o=document.createElement('option');o.value=value;o.textContent=name;select.append(o)}
p.p_ids.forEach((pid,i)=>option(source,pid,'P '+(i+1)+' · '+P[pid].members.map(x=>labels[x]).join(', ')));
c.arms.forEach(x=>option(arm,x,x.replaceAll('_',' ')));
arm.value='role_aligned';
const positions={};const total=p.p_ids.length;
p.p_ids.forEach((pid,i)=>{
 const ang=2*Math.PI*i/total-Math.PI/2,cx=500+360*Math.cos(ang),cy=320+215*Math.sin(ang);
 P[pid].members.forEach((nid,j)=>{
  const a=2*Math.PI*j/P[pid].members.length-Math.PI/2;
  positions[nid]=[cx+42*Math.cos(a),cy+42*Math.sin(a)];
 });
});
function svgEl(tag,attrs={},txt=null){
 const e=document.createElementNS('http://www.w3.org/2000/svg',tag);
 Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));
 if(txt!==null)e.textContent=txt;web.append(e);return e;
}
function chosen(){return c.trials.find(t=>t.source_p_id===source.value && t.arm===arm.value)}
function redraw(){
 const t=chosen();if(!t)return;slider.max=t.rounds;
 const n=Math.min(+slider.value,t.rounds);slider.value=n;tick.textContent=n;
 const frame=t.frames[n];web.replaceChildren();
 p.p_ids.forEach((pid,i)=>{
  const angle=2*Math.PI*i/total-Math.PI/2;
  const x=500+360*Math.cos(angle),y=320+215*Math.sin(angle);
  svgEl('circle',{cx:x,cy:y,r:72,fill:'#20304b','fill-opacity':'.30',stroke:'#527396','stroke-dasharray':'4 6'});
  svgEl('text',{x:x,y:y+72,'text-anchor':'middle',fill:'#acc8e5','font-size':'15'},'P '+(i+1));
 });
 t.links.forEach(e=>{
   const [x1,y1]=positions[e.source],[x2,y2]=positions[e.target];
   const color=e.kind.startsWith('hypothetical')?'#bc86ec':e.kind==='evidenced_cross_p'?'#67d69c':'#4b668b';
   const line=svgEl('line',{x1,y1,x2,y2,stroke:color,'stroke-width':e.kind==='native_plastic'?1.7:2.2,
     'stroke-opacity':.45+Math.min(.5,e.strength),'stroke-dasharray':e.kind.startsWith('hypothetical')?'4 5':''});
   line.style.cursor='pointer';
   line.onclick=()=>detail.textContent=[
    'From: '+labels[e.source], 'To: '+labels[e.target],
    'Channel: '+e.kind,'Simulated weight: '+e.strength,
    'Native evidence-backed relation: '+(e.relation_id||'NONE'),
    'Hypothetical connection cannot authorize a canonical fact.'
   ].join('\n');
 });
 p.concepts.forEach(cpt=>{
  const [x,y]=positions[cpt.id],a=frame.activation[cpt.id]||0;
  const seed=cpt.id===t.seed_concept_id;
  const node=svgEl('circle',{cx:x,cy:y,r:7+Math.sqrt(a)*14,
   fill:seed?'#e7b578':'#86dbf3','fill-opacity':.15+.85*a,stroke:'#dbf8ff','stroke-width':1.2});
  node.setAttribute('class','node');
  node.onclick=()=>detail.textContent=[
    'Concept: '+cpt.label, 'Canonical ID: '+cpt.id,
    'Source P: '+cpt.owner_p_ids.join(', '),
    'Original concept evidence refs: '+cpt.evidence_refs.length,
    'Private numeric activation: '+a.toFixed(6),
    'This circle position is a viewer-chosen layout, not native spatial memory.'
  ].join('\n');
  svgEl('text',{x,y:y-23,'text-anchor':'middle','font-size':'11',fill:'#e0eaf5'},cpt.label);
 });
 const ext=frame.active_non_source_p;
 metrics.replaceChildren();
 const facts=[
 ['Original P memories',p.p_ids.length],['Concepts',p.concepts.length],
 ['Local round',n],['Non-source nodes active',ext],
 ['Attempted transfers',frame.transfer_attempts.length],
 ['Total numeric activation',frame.total_activation.toFixed(5)],
 ['Experimental daughters',DATA.experimental_daughters.daughters.length],
 ['Native relation records',p.current_member_relations.length+p.evidenced_cross_p_relations.length],
 ['Dictionary byte reduction',Math.round(10000*DATA.native_relation_dictionary.receipt.reduction_fraction)/100+'%'],
 ['Local plasticity sessions',DATA.local_plasticity.events.length],
 ['Measured held-out numeric adaptation effect',String(DATA.local_plasticity.held_out?.measurable_local_plasticity_effect??false)],
 ];
 facts.forEach(([k,v])=>{
  const box=document.createElement('div');box.className='metric';
  const a=document.createElement('div');a.className='t';a.textContent=k;
  const b=document.createElement('strong');b.textContent=String(v);box.append(a,b);metrics.append(box);
 });
 trail.textContent=frame.transfer_attempts.length?frame.transfer_attempts.slice(0,55).map(e=>
   labels[e.source]+' → '+labels[e.target]+' · '+e.channel+' · '+e.amount.toFixed(5)
 ).join('\n'):'No transfer attempted this round.';
}
source.onchange=()=>{slider.value=0;redraw()};
arm.onchange=()=>{slider.value=0;redraw()};
slider.oninput=redraw;
scope.textContent=[
 'Source VDK fingerprint: '+p.canonical_fingerprint,
 'Q context: '+p.q_context_id,
 'Lifecycle seal: '+DATA.lifecycle_id,
 'Event history records: '+DATA.history.length,
 'Native canonical writes: NONE',
 'Role relationships: hypothetical only',
 'Original knowledge/graph: unchanged',
 'Daughter partitions: experimental, not native V4 physical mitosis',
 'Byte/dictionary compression: exactly reconstructable; no learned semantic compression claim',
].join('\n');
scope.style.whiteSpace='pre-wrap';scope.style.overflowWrap='anywhere';
redraw();
</script></body></html>'''


def render_lifecycle_html(lifecycle: dict) -> str:
    validate_lifecycle(lifecycle)
    serialized = json.dumps(lifecycle, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    # HTML data safety: never allow source labels to terminate <script>.
    serialized = serialized.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return _PAGE.replace("__POCKET_DATA__", serialized)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lifecycle", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.lifecycle.resolve() == args.out.resolve():
        parser.error("Viewer output must not replace the sealed source")
    html = render_lifecycle_html(load_lifecycle(args.lifecycle))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as f:
        f.write(html)
    print(f"Viewer created: {args.out}")


if __name__ == "__main__":
    main()
