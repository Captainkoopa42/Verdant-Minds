"""Observer-only: sequential-lesson interference, Verdant kernel vs a small neural network.

The same ordered lessons (sections of a curriculum pack, 20 items each) are given to
  V-web      Verdant, living plastic web only, no promotion
  V-P        Verdant, eligible candidates that exactly match a taught family are
             promoted through the Council at the end of the section that taught them
  N-same     one-hidden-layer network, one gradient step per (cue, family) per exposure
  N-crit     same network trained on each section until it recalls that section exactly
  N-replay   N-crit, but every earlier lesson is stored and replayed (the standard fix)

Test, identical for all arms: give ONE concept as cue, ask for the set that goes with
it. Correct only if the returned set equals the cue's taught family mates exactly.
Verdant's answer is its own read-only recall operation
(VerdantCompilationPipeline.inspect: use an available P, else bounded traversal of
plastic associations at the policy threshold). A threshold-free readout of the living
web (the k strongest neighbours) is reported beside it.

R[i][j] = accuracy on section j's cues after section i was taught.
final average = mean_j R[T][j];  backward transfer = mean_{j<T} (R[T][j] - R[j][j]).

Nothing here changes canonical state beyond ordinary teaching and governed promotion
inside the script's own throwaway kernels. No engine source is modified.
"""
from __future__ import annotations
import argparse, collections, json, pathlib, sys, time
import numpy as np

REPO = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(REPO), str(REPO / "workbench" / "backend")]
from verdant_workbench.curriculum import (CurriculumCompiler, CurriculumCompileRequest,
    curriculum_pack_bundle_source, curriculum_pack_selection_title)
from verdant_kernel import VerdantKernel, ExperienceCommand
from verdant_development import VerdantDevelopmentPipeline
from verdant_structures import VerdantStructurePipeline
from verdant_compilation import VerdantCompilationPipeline


def load_sections(pack_path: str, per_section: int):
    text = pathlib.Path(pack_path).read_text(encoding="utf-8")
    pack, bundle, selected, probes, source = curriculum_pack_bundle_source(text, ())
    result = CurriculumCompiler().compile(CurriculumCompileRequest(project_id="observer",
        title=curriculum_pack_selection_title(pack, selected), source_format="teaching_bundle_json",
        source_text=source, state_dim=pack.state_dim))
    cmds = [ExperienceCommand.model_validate(c) for c in result.compiled_commands]
    return pack.state_dim, [cmds[i:i + per_section] for i in range(0, len(cmds), per_section)]


def family(cmd) -> frozenset:
    return frozenset(p.label for p in cmd.concept_proposals)


def expected_mates(families_so_far):
    mates = collections.defaultdict(set)
    for fam in families_so_far:
        for c in fam:
            mates[c] |= fam
    return mates


# ---------------------------------------------------------------- Verdant arms
class VerdantArm:
    def __init__(self, seed, state_dim, promote):
        self.kernel = VerdantKernel(seed=seed, state_dim=state_dim, run_label="interference-observer")
        self.pipe = VerdantDevelopmentPipeline(); self.structs = VerdantStructurePipeline()
        self.recall = VerdantCompilationPipeline(); self.promote = promote; self.promoted = 0

    def label_ids(self):
        return {c.label: cid for cid, c in self.kernel.state.concepts.items()}

    def teach_section(self, cmds):
        for c in cmds:
            self.pipe.advance(self.kernel, c)
        if self.promote:
            fams = {family(c) for c in cmds}; st = self.kernel.state
            for cid, cand in sorted(st.structure_candidates.items()):
                if cand.status.value != "eligible":
                    continue
                if frozenset(st.concepts[m].label for m in cand.member_concept_ids) in fams:
                    try:
                        self.structs.promote(self.kernel, cid); self.promoted += 1
                    except Exception as exc:  # report, never hide
                        print("   promotion refused:", type(exc).__name__, str(exc)[:120], flush=True)

    def answer(self, cue_label):
        ids = self.label_ids(); st = self.kernel.state
        rep = self.recall.inspect(self.kernel, [ids[cue_label]])
        return {st.concepts[c].label for c in rep.reconstructed_concept_ids}

    def answer_neighbours(self, cue_label, k):
        ids = self.label_ids(); st = self.kernel.state; cue = ids[cue_label]; near = []
        for a in st.plasticity_associations.values():
            if cue in a.concept_ids:
                other = a.concept_ids[0] if a.concept_ids[1] == cue else a.concept_ids[1]
                near.append((-a.strength, st.concepts[other].label))
        return {cue_label} | {lab for _, lab in sorted(near)[:k]}

    def bond_strengths(self, fam):
        ids = self.label_ids(); want = {ids[c] for c in fam if c in ids}; out = []
        for a in self.kernel.state.plasticity_associations.values():
            if set(a.concept_ids) <= want:
                out.append(round(a.strength, 6))
        return sorted(out)


# ---------------------------------------------------------------- network arms
class Net:
    def __init__(self, n, hidden, seed, lr):
        r = np.random.default_rng(seed); self.lr = lr
        self.W1 = r.normal(0, 0.3, (hidden, n)); self.b1 = np.zeros(hidden)
        self.W2 = r.normal(0, 0.3, (n, hidden)); self.b2 = np.zeros(n)

    def forward(self, x):
        h = np.tanh(self.W1 @ x + self.b1); y = 1 / (1 + np.exp(-(self.W2 @ h + self.b2))); return h, y

    def step(self, x, t):
        h, y = self.forward(x); dy = y - t; dh = (self.W2.T @ dy) * (1 - h * h)
        self.W2 -= self.lr * np.outer(dy, h); self.b2 -= self.lr * dy
        self.W1 -= self.lr * np.outer(dh, x); self.b1 -= self.lr * dh

    def answer(self, idx, cue, names):
        x = np.zeros(len(names)); x[idx[cue]] = 1; _, y = self.forward(x)
        return {names[i] for i in np.nonzero(y > 0.5)[0]}


def examples(cmds, idx, n):
    out = []
    for c in cmds:
        fam = family(c); t = np.zeros(n); t[[idx[m] for m in fam]] = 1
        for m in sorted(fam):
            x = np.zeros(n); x[idx[m]] = 1; out.append((x, t))
    return out


def score(answer_fn, section_fams, mates):
    cues = sorted({c for fam in section_fams for c in fam})
    return sum(answer_fn(c) == mates[c] for c in cues) / len(cues)


def summarise(R):
    T = len(R); final = float(np.mean(R[-1])); bwt = float(np.mean([R[-1][j] - R[j][j] for j in range(T - 1)])) if T > 1 else 0.0
    return {"final_average": round(final, 4), "backward_transfer": round(bwt, 4), "learned_when_taught": round(float(np.mean([R[j][j] for j in range(T)])), 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", required=True); ap.add_argument("--sections", type=int, default=6)
    ap.add_argument("--per-section", type=int, default=20); ap.add_argument("--seed", type=int, default=2301)
    ap.add_argument("--net-seeds", type=int, default=5); ap.add_argument("--hidden", type=int, default=64)
    ap.add_argument("--accelerate", action="store_true"); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.accelerate:
        from sidecar_acceleration import install_fingerprint_cache; install_fingerprint_cache()
    state_dim, secs = load_sections(a.pack, a.per_section); secs = secs[:a.sections]; T = len(secs)
    sec_fams = [sorted({family(c) for c in s}, key=sorted) for s in secs]
    names = sorted({c for fams in sec_fams for fam in fams for c in fam}); idx = {n: i for i, n in enumerate(names)}
    shared = [n for n in names if sum(n in fam for fams in sec_fams for fam in fams) > 1]
    print(f"sections {T} | items {sum(map(len, secs))} | families {sum(map(len, sec_fams))} | concepts {len(names)} | concepts in more than one family: {len(shared)}", flush=True)

    R = {k: [] for k in ("V-web", "V-web-neighbours", "V-P")}
    arms = {"V-web": VerdantArm(a.seed, state_dim, False), "V-P": VerdantArm(a.seed, state_dim, True)}
    decay = []; t0 = time.perf_counter()
    for i, cmds in enumerate(secs):
        for arm in arms.values():
            arm.teach_section(cmds)
        mates = expected_mates([f for fams in sec_fams[:i + 1] for f in fams])
        k_of = lambda c: len(mates[c]) - 1
        R["V-web"].append([score(arms["V-web"].answer, sec_fams[j], mates) for j in range(i + 1)])
        R["V-web-neighbours"].append([score(lambda c: arms["V-web"].answer_neighbours(c, k_of(c)), sec_fams[j], mates) for j in range(i + 1)])
        R["V-P"].append([score(arms["V-P"].answer, sec_fams[j], mates) for j in range(i + 1)])
        decay.append({"after_section": i + 1, "cycle": arms["V-web"].kernel.state.cycle,
                      "section1_mean_bond": round(float(np.mean([s for f in sec_fams[0] for s in arms["V-web"].bond_strengths(f)] or [0.0])), 4),
                      "section1_living_bonds": sum(len(arms["V-web"].bond_strengths(f)) for f in sec_fams[0])})
        print(f"after section {i+1}: V-web {R['V-web'][-1]}  neighbours {R['V-web-neighbours'][-1]}  V-P {R['V-P'][-1]}  promoted {arms['V-P'].promoted}  ({time.perf_counter()-t0:.0f}s)", flush=True)

    net_runs = {k: [] for k in ("N-same", "N-crit", "N-replay")}; epochs_used = {"N-crit": [], "N-replay": []}
    for s in range(a.net_seeds):
        nets = {k: Net(len(names), a.hidden, 1000 + s, 0.2) for k in net_runs}; Rn = {k: [] for k in net_runs}
        rng = np.random.default_rng(5000 + s); memory = []
        for i, cmds in enumerate(secs):
            ex = examples(cmds, idx, len(names)); mates = expected_mates([f for fams in sec_fams[:i + 1] for f in fams])
            for x, t in ex:
                nets["N-same"].step(x, t)
            for name, pool in (("N-crit", ex), ("N-replay", memory + ex)):
                done = 0
                for ep in range(1, 2001):
                    for q in rng.permutation(len(pool)):
                        nets[name].step(*pool[q])
                    done = ep
                    if score(lambda c: nets[name].answer(idx, c, names), sec_fams[i], mates) == 1.0:
                        break
                epochs_used[name].append(done)
            memory += ex
            for name in net_runs:
                Rn[name].append([score(lambda c: nets[name].answer(idx, c, names), sec_fams[j], mates) for j in range(i + 1)])
        for name in net_runs:
            net_runs[name].append(Rn[name])

    report = {"schema": "verdant.observer.interference_vs_network.v0", "claim_boundary": "OBSERVED on this pack prefix, this seed, this toy network; not a general benchmark result",
              "pack": pathlib.Path(a.pack).name, "sections": T, "items": sum(map(len, secs)), "concepts": len(names), "shared_concepts": shared,
              "kernel_seed": a.seed, "final_cycle": arms["V-web"].kernel.state.cycle, "promoted_structures": arms["V-P"].promoted,
              "compilation_policy_minimum_association_strength": arms["V-web"].kernel.state.compilation_policy.minimum_association_strength,
              "arms": {}, "section1_bond_decay_in_living_web": decay,
              "network": {"hidden": a.hidden, "seeds": a.net_seeds, "learning_rate": 0.2,
                          "mean_epochs_per_section": {k: round(float(np.mean(v)), 1) for k, v in epochs_used.items()},
                          "replay_examples_stored_at_end": sum(len(examples(s, idx, len(names))) for s in secs)}}
    for k, v in R.items():
        report["arms"][k] = {**summarise(v), "R": v}
    for k, runs in net_runs.items():
        per = [summarise(r) for r in runs]
        report["arms"][k] = {m: round(float(np.mean([p[m] for p in per])), 4) for m in per[0]}
        report["arms"][k]["final_average_min_max"] = [min(p["final_average"] for p in per), max(p["final_average"] for p in per)]
        report["arms"][k]["R_mean"] = [[round(float(np.mean([r[i][j] for r in runs])), 3) for j in range(i + 1)] for i in range(T)]
    pathlib.Path(a.out).write_text(json.dumps(report, indent=1), encoding="utf-8")
    print("\narm                 learned-when-taught   final-average   backward-transfer")
    for k, v in report["arms"].items():
        print(f"{k:18s}  {v['learned_when_taught']:>10.3f}          {v['final_average']:>8.3f}        {v['backward_transfer']:>+8.3f}")
    print("section-1 bonds in the living web:", [(d['after_section'], d['section1_mean_bond'], d['section1_living_bonds']) for d in decay])
    print("network epochs per section:", report["network"]["mean_epochs_per_section"], "| report:", a.out)


if __name__ == "__main__":
    main()
