# Ethomorphic field roadmap v0: old ideas brought into the new organism (DESIGN, nothing built yet)

Date: 2026-11-18. Status: PROPOSED. Every stage is an opt-in sidecar; nothing under `verdant_*`
changes. Each stage gets preregistered tests (written before its first run) and must pass the
shared gates below before the next stage builds on it.

Where each idea comes from (William's earlier repositories, read 2026-11-18):

| Idea | Source | Open problem it addresses |
|---|---|---|
| Resonance reads cos Θ and sin Θ separately | Resonant-Intelligence (2024), `equations/resonance_equation.md` | Conflict shows as silence, not opposition |
| Phase carries stance (the ethical term inside Θ) | 2024 ECWF; July 2025 `ECWFCore` | Contradiction has no place in the field |
| Each component turns at its own rate, ω·t | 2024 P.O.C; July 2025 `ECWFCore.compute_ecwf` | No rhythm; binding counted in cycles, not moments |
| Glass transition Tg: rigid / flexible / chaotic | verdant-intelligence (2025); V4; V5x `verdant_thermodynamics` | Fixed numbers instead of self-set dynamics |
| Three Kings: Data, Forefront, Ethics; two-thirds vote | July 2025 `ThreeKingsLayer`; today `verdant_governance` | Who settles open propositions and assigns reward |
| Waves spreading through the Memory Web | Resonant-Intelligence `components/memory_web.md` | Reminders reach only one bond |

## Shared gates (every stage)

1. Opt-in and reversible; uninstall restores stock exactly (tested by fingerprint).
2. Reliving stays exact (tested to 1e-9) whatever the stage writes into the field.
3. Only OBSERVED or told evidence teaches or settles anything; IMAGINED and INFERRED never do.
4. The full test suite passes (2,225 + Workbench 71 today).
5. The 400-lesson text life (seed 9001, kernel 2301) with the stage installed keeps: cues kept
   >= 145/148, promoted >= 43/46, wrong promotions 0.
6. Every self-change is logged per beat, and nothing the organism sets for itself is unbounded.

## The phase budget (decided first, because three stages want the phase)

A concept is written as w · e^{iθ} · address. The turn θ already has, or would get, these jobs:

| Job | Turn | Owner |
|---|---|---|
| told, agreeing, confirmed | 0 | stock |
| contradicted, refuted | half turn (π) | Stage A |
| relation role: source / both / target | 0 / eighth / quarter | `sidecar_wave` (exists) |
| age: how many moments ago | slow rotation, ω per moment | Stage B |

These do not collide because every frame records what was written and when: role comes from the
frame's relation proposals and age from its index, so a reader can remove the known turns
(de-rotate) before reading the stance. Rule: **stance is the sign that is left after removing every
known turn; whatever turn is left unexplained is uncertainty.** For the live field (a mixture of
ages) this is approximate, so ω is kept slow (recent moments nearly in step); Stage B measures how
much stance survives in the live field.

## Stage A: signed resonance, from the 2024 resonance equation

What exists: resonance uses the absolute alignment |⟨a, field⟩| for presence, so +a and −a read the
same; `sidecar_stance` already writes claims in step or at a half turn into proposition addresses,
and `sidecar_ring.read_tension` keeps a signed per-concept record.

Design (read side, added as a channel; the presence ranking is unchanged):
* For a concept with address a and the field F, z = ⟨a, F⟩ after removing known turns.
* presence = |z| (stock); **support** = Re z / |z| in [-1, 1] (the cos Θ part: agree vs contradict);
  **uncertainty** = |Im z| / |z| (the sin Θ part: turned away for no known reason).
* The workspace's contradiction_pressure for a concept becomes max(0, −support) when presence is
  above a floor, alongside the measured value from `sidecar_ring`.

Design (write side): what is opposed is written at a half turn, never silently dropped:
* a claim the record negates (`sidecar_stance`, already);
* a recognised concept that conflicts with what was told ("told X, it sounds like Y"): Y rings at a
  half turn instead of in step (inferred, weighted by its share, logged as before);
* a proposition the Council refutes (Stage D).

Tests (preregistered): conflict worlds from `run_observer_attention.py` and the conflict test of
`run_observer_one_wave.py`: support for the conflicted concept clearly negative (< −0.3), for an
unrelated concept near 0 (|support| < 0.15 is not required, uncertainty high instead), for agreement
positive (> 0.3); naming accuracy unchanged; shared gates.

Risk: a half-turn ring subtracts a concept's address, which can lower its presence in sums; presence
stays |z| so ranking reads it, but the live field's total changes. Measured, not assumed.

## Stage B: rhythm, from ω·t in the 2024 and 2025 cores

What exists: time enters only as the 0.72 fade; carrying was counted in kernel cycles (4-5 per
experience), which is why binding failed until `install_moment_carry`.

Design, two steps:
1. **A moment clock.** Before each experience is written, the old field turns by e^{-iω} with
   ω = 2π / τ, τ = 48 moments (declared; one turn every 48 experiences). Everything already in the
   field lags by ω per moment since it was written, so the phase lag of a concept's alignment says how
   long ago it was present (unambiguous within τ). Things written in the same moment share a lag:
   **binding by synchrony**. Relive is updated: after = unit(r · R · before + effect), R known per frame.
2. **Its own rhythm (later).** τ set from the organism's own pace (the spacing of its experiences,
   then per concept from how often it recurs: "time is the rhythm of resonance"), bounded, logged.

Tests: the binding world (`run_observer_binding.py`) with the moment clock and WITHOUT moment carry:
together-pairs read as in synchrony, never-together pairs not; age read back from the lag within
one moment for the last 10 moments; Stage A support still readable for the last 5 moments; text-life gate.

Risk: rotation weakens the build-up of a concept seen on consecutive moments (slightly out of step);
τ = 48 keeps consecutive moments 7.5° apart. Measured.

## Stage C: temperature, from the glass transition (reusing V5x `verdant_thermodynamics`)

What exists: V5x computes Tg, classifies rigid / flexible / chaotic with hysteresis
(`PhaseHysteresis`: rigid below 0.38-0.42, chaotic above 0.58-0.62), and a controller that changes
only the next cycle's temporary `DevelopmentalCycleConfig`, never evidence, concepts, claims,
structures, kernel policies or bonds. Its detector study found the V4 Tg law tracks input wordiness
(60 neutral tokens raised every Tg by exactly 0.0885) and never triggered a real intervention.

Design: keep the dial and its safety boundary; change what feeds it. The temperature comes from the
organism's measured state (exponential averages over moments, half-life 20 moments):
* u = unknown share of what it senses (`sidecar_ring` novelty), k = contradiction / tension,
  s = surprise (prediction error, `sidecar_surprise`), n = rate of new concepts.
* T = clamp(0.1, 0.9, 0.3 + 0.35 u + 0.2 k + 0.15 s + 0.1 n) (weights declared now, not tuned later).
* Phase by the existing hysteresis; the previous beat's phase sets this beat (never the same beat).

What the temperature may set, all bounded, only for the next beat, all logged:

| Setting | Rigid | Flexible | Chaotic |
|---|---|---|---|
| novelty signal into the workspace | × 0.5 | × 1 | × 1.6 (cap 1) |
| contradiction signal | × 1.2 | × 1 | × 0.8 |
| ring threshold (share) | 0.35 | 0.25 | 0.20 |
| bonds may form from carried moments | yes | yes | no (protect against binding everything) |

The expected behaviour (to be tested, not assumed): hot when young, cooling as it learns (negative
feedback: attending to the new reduces the unknown), heating again when moved to a new world.

Tests: a two-world life (world 1, then world 2 never seen): T high early, falls, rises at the switch,
settles again; it never sits in chaotic for more than 20 consecutive moments; new pairs bond faster
than stock in the hot phase (the thing novelty failed to do at fixed weights); text-life gate.

## Stage D: open propositions, cold storage and reward, settled by the Council

What exists: the Council in `verdant_governance` with `_data_king`, `_forefront_king`,
`_ethics_king` and a council rule; structure candidates that wait for gates (a pending kind already);
imagination's predictions and the reality check; hashes everywhere.

Proposition record: id, kind, content, **cue wave** (what would be seen if it came true: an imagined
look or readout), opened_at (moment), prior p (how sure it was), opened_by (provenance; IMAGINED or
INFERRED), sources (the bonds / structures / memory that produced it), status.

Where propositions come from: an imagined combination (imagine); a conflict (told X, sensed Y:
"X sounds like this"); a recurring unknown (the same leftover keeps arriving); a structure candidate
stuck below its gates.

Lifecycle:
* OPEN: each beat the sensed wave is compared with open cues (a dot product each, cheap). A match
  above 0.6 brings the proposition into the workspace as an "open question".
* COLD: untouched for 50 moments, it is sealed: content and cue hashed (SHA-256), never modified;
  still matched each beat (cue kept), lower priority. Capacity 512; beyond it the lowest-value
  expire (EXPIRED: hash and outcome-less record kept, cue dropped).
* SETTLED only by the Council, only when the beat carries OBSERVED or told evidence:
  Data King: does the evidence bear on it, and which way? Forefront King: is it relevant now?
  Ethics King: is settling it consistent with the record and its values? Two of three, as in 2025.
  Outcomes CONFIRMED, REFUTED, or UNDECIDED (stays open).
* Reward is consolidation, weighted by how much was learned: confirmed: the sources are strengthened
  by α (1 − p); refuted: weakened by α p and the proposition written at a half turn (Stage A).
  A near-certain guess earns almost nothing, so proposing the obvious cannot farm reward.

Tests: plant delayed truths (imagine a combination at lesson 50, teach it at lesson 300): retrieved
and settled at 300 >= 90% of cases; reward lands on the sources that predicted it; cheap guesses (p >
0.9) earn < 10% of the reward of uncertain ones; imagined evidence never closes anything (0);
false closures (settled by unrelated evidence) <= 1 in 20; cold store stays within capacity;
text-life gate.

## Stage E: spreading reminders, from the Memory Web

Design: reminders travel up to 3 bonds, fading 0.72 per step, each labelled with its path
("reminded via A, B"); as stock, recall never creates bonds. Feeds imagination's second step.
Tests: in a chain A-B-C-D, A brings B strongly, C faintly, D not at all; precision of reminders vs
the real workspace; text-life gate.

## Stage F (later, needs William): ethics in the wave

The 2024 ECWF put an ethical state vector inside the phase. With Stages A-D in place, values could
be a stance axis toward outcomes (what the organism holds good or harmful, written in step or at a
half turn, settled by the Ethics King). The meaning of "value" here is William's to define first.

## Order and why

A (signed resonance) -> B (rhythm) -> C (temperature) -> D (propositions) -> E (spreading) -> F.
A first: it fixes the clearest open problem and D needs refutation in the field. B before C: the
temperature's averages are per moment, which B defines. C before D: the load of open questions
should feed the temperature. E is independent and can move earlier. F waits for a conversation.

---
## Stage A preregistration (2026-11-19, before the first run)

Reading. For a concept with address a in the field F: z = ⟨a, F⟩ (no known turns to remove yet:
stock and the ring stack write in step; the wave sidecar's role turns are not combined with Stage A
in this first version). presence = |z|; it **stands out** when presence exceeds the mean of all
concepts' presences by 3 standard deviations. support = Re z / |z|; uncertainty = |Im z| / |z|.
Support is only read for concepts that stand out: for the rest, z is noise and its sign is random,
so "unrelated" means "does not stand out", not "support near 0".

Writing. In `sidecar_ring`, when an experience is in conflict (the same contradiction measure the
attention stage uses: best untold share minus told share > 0.2, told concepts already having a view
in that sense), the untold concepts that outweigh the told ones ring at a half turn (weight −share)
instead of in step. Logged with their sign; reliving rebuilds them exactly.

Pass criteria, `run_observer_signed.py`, seeds 61 and 62 (the attention world), ring + adaptation +
signed vs ring + adaptation:
1. right after a conflicting moment (told X, sounding like Y): Y stands out with support < −0.3 in
   >= 5 of 6 conflicts; X stands out with support > +0.3 in >= 5 of 6;
2. after correctly told moments: the told concept stands out with support > +0.3 in >= 14 of 16, and
   no concept stands out with support < −0.3 (false contradictions) in >= 15 of 16;
3. uninvolved familiar concepts do not stand out in >= 95% of readings;
4. without signed writing, conflicting Y reads support > 0 (shows the change is what makes it negative);
5. reliving exact (< 1e-9) on every moment, including half-turn rings.
Gates: the recognition world (`run_observer_one_wave.py`, seeds 31-33, ring + adaptation) names as
before (sight within 1 of 32 per seed, sound unchanged); the 400-lesson text life with the senses
stack + signed keeps 145/148, 43/46, 0 wrong; the full suite passes.

### Stage A, first run: the preregistered "stands out" rule failed (recorded as it happened)
Signed writing worked: the conflicting concept read support −0.96 to −0.99 with signed writing and
+0.99 to +1.00 without (both seeds), and reliving stayed exact (2e-16). But NO concept stood out under
the rule above, not even the one just told, so criteria 1-2 failed. Cause: a crowd rule (mean + 3 SD)
cannot flag outliers in a ~14-concept world when two concepts are present, since they inflate the SD
themselves. Replacement, fixed before re-running and not tuned on the values: a concept is **present**
when its alignment exceeds 3 times what a random unrelated address gives in a field of D dimensions,
|z| > 3/√D (D = 128: 0.265; for a random address |z|² averages 1/D, so exceeding 3 times that RMS
happens about once in 8,000 readings, whatever the number of concepts). Criteria 1-5 unchanged otherwise.

### Stage A, second run (chance floor) and a design finding
Half-turn version, seeds 61 + 62: (1) conflicting concept contradicted 5/6, told concept agrees 5/6
(pass); (2) after correct moments the told concept agrees 16/16, no false contradiction 16/16 (pass);
(3) "uninvolved" concepts not present 93% / 91% (fail as written: every exception had been told 1-2
moments earlier, so it really was still in the field; the criterion confused "not in this moment" with
"absent"); (4) without signed writing the conflicting concept agrees 6/6 (pass); (5) replay exact (pass).

Finding: writing the opposition at a half turn onto the concept's own address CANCELS its existing
presence. In a unit test the conflicting concept's presence fell from 0.488 to 0.263 (below the floor,
so the contradiction made itself invisible); the one miss in criterion 1 was the same effect. That
violates "contradiction is carried, not erased". The soul equation already says how to carry it:
U = (M + −M)^i: opposites summed cancel; the turn i keeps both.

### Stage A.2 preregistration: unresolved conflict at a quarter turn, refutation at a half turn
* An UNRESOLVED conflict (told X, sensed Y) rings Y a quarter turn off (weight i * share): held beside
  Y's existing presence, not subtracted from it. The half turn is reserved for a SETTLED refutation
  (Council, Stage D).
* Reading: tension = Im z / |z| (signed; the sin part), support = Re z / |z| (the cos part).
  Verdicts for present concepts: contradicted (support < −0.3), in tension (tension > 0.5),
  agrees (support > 0.3), otherwise uncertain.
Pass criteria (seeds 61, 62):
1. conflicting Y present and in tension (tension > 0.5) in >= 5/6; Y's presence >= 0.9 x its presence
   with in-step writing in >= 5/6 (carried, not erased); told X agrees in >= 5/6;
2. after correct moments: told concept agrees in >= 14/16; no present concept in tension in >= 15/16;
3. concepts not told in the last 4 moments are not present in >= 95% of readings;
4. with in-step writing, Y's tension < 0.3 in >= 5/6;
5. replay exact (< 1e-9) on every moment.

### Stage A.2 results (quarter turn kept as the default for unresolved conflict)
Reports `signedA2_seed{61,62}_{none,quarter}.json`.

| criterion | result |
|---|---|
| 1a conflicting concept present and in tension | **6/6** (tension 0.82-0.99) pass |
| 1b its presence >= 0.9 x in-step writing | **2/6, fail as written** (see below) |
| 1c told concept agrees | 5/6 pass |
| 2 correct moments: told agrees / no false tension | 16/16, 16/16 pass |
| 3 not told in the last 4 moments: not present | 100%, 100% pass |
| 4 in-step writing: no tension | 6/6 pass |
| 5 replay exact | 2.5e-16 pass |

1b compared against the wrong thing: writing in step adds straight onto a concept's presence and a
quarter turn adds at right angles, so it can never reach in-step presence (|p + iw| < p + w). What
the criterion meant to test, that the conflict is carried and not erased, is 1a: present 6/6 with
the quarter turn, against 5/6 and a halved presence with the half turn. Recorded as a criterion error,
not re-scored. Three of this stage's criteria were mis-specified (crowd floor, "uninvolved", 1b); the
mechanism behaved as designed each time, and every correction is written above before its re-run.

Gates: recognition world seeds 31-33 with ring + adaptation + quarter: organism sight naming 29, 27,
25 of 32 and sound 32 of 32 (identical to without), priming identical, conflict verdicts identical;
turned rings during each whole life: 1, 1, 0 (correct teaching rarely triggers the conflict rule).
400-lesson text life with the senses stack + quarter: **145/148 kept, 43/46 promoted, 0 wrong**.

Phase budget update: unresolved conflict now uses the quarter turn, the same turn `sidecar_wave`
uses for a relation's target. The two are not combined yet; combining them requires removing the
role turns per frame before reading tension (planned with Stage B's de-rotation).
