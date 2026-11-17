"""Observer: does the wave carry what the organism was told, independently of the claims engine?

Six kinds of proposition, 8 of each, mixed among ordinary lessons in one life:
  true        told true 4 times             false       told false 4 times
  contested   true, false, true, false      reversed    told true twice early, false twice late
  once        told true once                never       subject and object taught, nothing claimed
With ``sidecar_stance`` installed (and optionally the rest of the experimental stack), the field
keeps its own account. It is compared with the kind each proposition really is and with the
claims engine's own records (status, contradiction, current belief), which the sidecar never
touches. Tension is checked as an attention signal: do contested and reversed propositions
rank above settled ones?
"""
from __future__ import annotations

import argparse, collections, hashlib, json, random, sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent
sys.path[:0] = [str(REPO), str(REPO / "curriculum_packs")]
from generate_controls_pack_v0 import RELATIONS, TEMPLATES, Tokens, text_features  # noqa: E402
from verdant_development import VerdantDevelopmentPipeline  # noqa: E402
from verdant_kernel import ConceptProposal, ExperienceCommand, VerdantKernel  # noqa: E402
from verdant_kernel.models import ClaimProposal, EvidenceKind  # noqa: E402

DIM = 128
KINDS = {"true": "++++", "false": "----", "contested": "+-+-", "reversed": "++--", "once": "+", "never": ""}


def build(seed: int):
    rng = random.Random(seed); tokens = Tokens(rng); props, stream = [], []
    for kind, seq in KINDS.items():
        for i in range(8):
            s, o = tokens.new(), tokens.new(); props.append({"kind": kind, "subject": s, "object": o, "seq": seq})
            stream.append((rng.uniform(0, 0.3), ("mention", s, o)))                 # every subject/object is taught first
            for j, sign in enumerate(seq):
                at = rng.uniform(0.75, 1.0) if (kind == "reversed" and j >= 2) else rng.uniform(0.3, 0.7)
                stream.append((at, ("claim", s, o, sign)))
    for i in range(60):                                                             # ordinary lessons in between
        m = [tokens.new() for _ in range(3)]
        for e in range(2):
            stream.append((rng.uniform(0, 1), ("family", m, e)))
    stream.sort(key=lambda x: x[0]); commands = []
    for n, (_t, item) in enumerate(stream):
        if item[0] == "family":
            m, e = item[1], item[2]; text = TEMPLATES[e % len(TEMPLATES)].format(clauses=f"the {m[0]} {RELATIONS[0]} the {m[1]} and the {m[1]} {RELATIONS[1]} the {m[2]}")
            labels, claims, kind = m, [], None
        elif item[0] == "mention":
            text = f"The {item[1]} is near the {item[2]}."; labels, claims, kind = [item[1], item[2]], [], None
        else:
            _c, s, o, sign = item; text = f"A teacher reports that the {s} {'holds' if sign == '+' else 'does not hold'} the {o}."
            labels = [s, o]; kind = EvidenceKind.TESTIMONY
            claims = [ClaimProposal(subject_label=s, predicate="holds", object_label=o, polarity="affirmed" if sign == "+" else "negated",
                                    source_class="human_testimony", confidence=0.9)]
        commands.append(ExperienceCommand(event_key=f"stance-{seed}-{n:04d}", source_ref="stance-observer", modality="text",
                                          feature_vector=text_features(text, DIM), payload_sha256=hashlib.sha256(text.encode()).hexdigest(),
                                          concept_proposals=[ConceptProposal(label=x) for x in labels], claim_proposals=claims,
                                          semantic_evidence_kind=kind, metadata={"context_id": f"c{n % 4}"}))
    return props, commands


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=2301); ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--stack", action="store_true", help="Also install the wave sidecar and use the experimental heartbeat stack.")
    a = ap.parse_args()
    from sidecar_acceleration import install_long_life_acceleration; install_long_life_acceleration()
    if a.stack:
        from sidecar_wave import install_wave; install_wave()
    from sidecar_stance import install_stance, proposition_key, read_stance
    install_stance()
    props, commands = build(a.seed)
    kernel = VerdantKernel(seed=a.seed, state_dim=DIM, run_label="stance"); pipe = VerdantDevelopmentPipeline()
    if a.stack:
        from run_observer_long_life import build_pipeline
        pipe, _structures = build_pipeline("reunion")
    for c in commands:
        pipe.advance(kernel, c)
    field = read_stance(kernel); st = kernel.state; rows = []
    for p in props:
        key = proposition_key(p["subject"], "holds", p["object"]); f = field.get(key)
        claims = [c for c in st.claims.values() if c.claim_key == key]
        belief = kernel.current_belief_by_key(key)
        rows.append({"kind": p["kind"], "field": f,
                     "engine": {"claims": {c.polarity.value: c.status.value for c in claims},
                                "contradiction": any(x.claim_key == key for x in st.contradictions.values()),
                                "belief": belief.polarity.value if belief else None}})

    def field_says(f):
        if f is None:
            return "never"
        if f["net"] < 0.5 * f["said"]:
            return "conflicted"
        return "true" if math_cos(f["lifelong_turns"]) > 0 else "false"
    math_cos = lambda turns: float(np.cos(2 * np.pi * turns))
    expect = {"true": "true", "false": "false", "contested": "conflicted", "reversed": "conflicted", "once": "true", "never": "never"}
    by_kind = collections.OrderedDict()
    for r in rows:
        k = r["kind"]; g = by_kind.setdefault(k, collections.Counter()); f = r["field"]
        g["n"] += 1; g["field_reads_it_right"] += field_says(f) == expect[k]
        if f:
            g["recent_says_false"] += math_cos(f["recent_turns"]) < 0
        g["engine_contradiction"] += r["engine"]["contradiction"]; g["engine_belief_" + str(r["engine"]["belief"])] += 1
        for t in ("net", "tension"):
            g[t + "_sum"] += f[t] if f else 0.0
    summary = {k: {"field_reads_it_right": f"{g['field_reads_it_right']}/{g['n']}", "mean_net": round(g["net_sum"] / g["n"], 3),
                   "mean_tension": round(g["tension_sum"] / g["n"], 3), "recent_stance_is_false": f"{g['recent_says_false']}/{g['n']}",
                   "engine_contradiction_records": f"{g['engine_contradiction']}/{g['n']}",
                   "engine_current_belief": {b[len('engine_belief_'):]: v for b, v in g.items() if b.startswith("engine_belief_")}}
               for k, g in by_kind.items()}
    agree = sum((r["engine"]["contradiction"]) == (field_says(r["field"]) == "conflicted") for r in rows if r["kind"] != "never")
    conflicted = [r["field"]["tension"] if r["field"] else 0.0 for r in rows if r["kind"] in ("contested", "reversed")]
    settled = [r["field"]["tension"] if r["field"] else 0.0 for r in rows if r["kind"] in ("true", "false", "once", "never")]
    report = {"schema": "verdant.observer.stance.v0", "seed": a.seed, "stack": a.stack, "lessons": len(commands),
              "by_kind": summary, "field_and_engine_agree_on_conflict": f"{agree}/{sum(r['kind'] != 'never' for r in rows)}",
              "tension_ranks_conflicted_above_settled": round(float(np.mean([[c > s for s in settled] for c in conflicted])), 3),
              "claim_records_untouched_by_sidecar": all("stance" not in json.dumps(c.attributes) for c in st.claims.values())}
    a.out.write_text(json.dumps(report, indent=1), encoding="utf-8"); print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
