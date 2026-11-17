"""Observer (read-only): in two saved organisms, how much is still held about things that should fade?
Usage: python run_observer_should_fade.py OLD_STATE.json NEW_STATE.json  (expectations path is set inside)."""
# Read-only: in the final organism, what is still held about things that SHOULD have faded?
import sys, json, collections
sys.path[:0]=['.','workbench/backend','curriculum_packs']
from pathlib import Path
from verdant_kernel import VerdantKernel
from verdant_kernel.models import KernelState
from verdant_compilation import VerdantCompilationPipeline
from sidecar_acceleration import install_long_life_acceleration; install_long_life_acceleration()
from sidecar_bond_clock import install_changes_only; install_changes_only()
exp=json.load(open('/home/claude/audit_life/verdant_long_life_curriculum_400_seed9001.expectations.json'))
for name,path in (("engine as it was",sys.argv[1]),("full system, today",sys.argv[2])):
    k=VerdantKernel.from_state(KernelState.model_validate_json(Path(path).read_text())); s=k.state
    lab={c:x.label for c,x in s.concepts.items()}; ids={v:c for c,v in lab.items()}; recall=VerdantCompilationPipeline()
    rows=collections.OrderedDict()
    for f in exp['families']:
        g=rows.setdefault(f['group'],collections.Counter()); m=set(f['members']); mid={ids[x] for x in m if x in ids}
        g['n']+=1; alive=[a.strength for a in s.plasticity_associations.values() if set(a.concept_ids)<=mid]
        g['bonds_alive']+=len(alive); g['family_has_a_bond']+=bool(alive)
        for cue in sorted(m):
            got={lab[c] for c in recall.inspect(k,[ids[cue]]).reconstructed_concept_ids} if cue in ids else set()
            g['cues']+=1; g['cue_recalls_a_partner']+=bool(got & (m-{cue}))
    d=set(exp['distractor_concepts']); dids={ids[x] for x in d if x in ids}
    dbonds=[a for a in s.plasticity_associations.values() if set(a.concept_ids)<=dids]
    print(f"\n{name}: living bonds {len(s.plasticity_associations)}, among random noise pairs {len(dbonds)}")
    for g,v in rows.items():
        if g in ('once','under_exposed','single_context','pairs_only','massed','spaced_long'):
            print(f"  {g:15s} families with a living bond {v['family_has_a_bond']:3d}/{v['n']:<3d}  cues that still call up a partner {v['cue_recalls_a_partner']:3d}/{v['cues']}")
