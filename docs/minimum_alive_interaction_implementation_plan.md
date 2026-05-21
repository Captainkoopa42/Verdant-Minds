# Verdant-Minds: Minimum Alive Interaction Implementation Plan

This is a practical build plan to cross the first meaningful "alive" threshold:

> A person sends text -> Verdant processes through its actual graph/thermo/basin pipeline ->
> Verdant returns a response grounded in that state -> the interaction is persisted and shapes the
> next interaction with that same person.

The goal is not polish. The goal is a reliable, architecture-faithful loop.

---

## 1) Minimum viable input adapter (architecture-faithful)

### 1.1 Design rule

Input must become **graph activations first**, not "LLM answer first".

### 1.2 Minimal input pipeline

Implement a `TextInputAdapter` with these stages:

1. **Normalize text**
   - lowercase (except proper nouns if available), trim whitespace, simple punctuation split.
2. **Extract candidate concept tokens**
   - n-grams (1-3) + noun-like tokens + detected named entities (optional lightweight heuristic).
3. **Resolve tokens to graph nodes**
   - exact match alias table first,
   - fallback fuzzy match (thresholded string similarity),
   - unresolved tokens become provisional nodes (`seed:<token>`).
4. **Build activation packet**
   - `{node_id, base_weight, source='human_text', person_id, ts}` list.
5. **Inject packet into attention buffer + spreading activation entrypoint**
   - no direct semantic bypass.

### 1.3 Data contract (v0)

```python
@dataclass
class InputActivationPacket:
    person_id: str
    session_id: str
    text: str
    ts_utc: str
    candidates: list[dict]  # token, node_id, confidence
    activations: list[dict] # node_id, weight
    metadata: dict
```

### 1.4 Non-negotiable for v0

- Token->node resolution must happen before pipeline processing.
- Any unknown concept must still enter memory as provisional (not dropped).
- Every packet must carry `person_id` and timestamp for future relational partition migration.

---

## 2) Minimum viable output adapter (state-grounded)

### 2.1 Design rule

Output text should be generated from **post-cycle state summary**, not independent LLM completion.

### 2.2 Minimal output strategy

Implement `StateToTextAdapter` that renders a constrained response from:

- top-k activated concepts,
- dominant basin(s),
- coherence/thermo flags,
- attention focus,
- optional recalled relational anchors for this `person_id`.

Template-first generation (v0):

1. **Acknowledge** interpreted intent using top concept cluster.
2. **Reflect** one dominant internal state signal (e.g., uncertainty/high conflict vs stable coherence).
3. **Respond** with one action/proposal tied to active concepts.
4. **Memory hook**: one short sentence that references persisted continuity when available.

### 2.3 Data contract (v0)

```python
@dataclass
class OutputRenderContext:
    person_id: str
    cycle: int
    top_nodes: list[tuple[str, float]]
    top_basins: list[dict]
    coherence: dict
    thermodynamics: dict
    attention_items: list[dict]
    retrieved_relational: list[dict]
```

### 2.4 Why template-first

- Guarantees architecture grounding.
- Avoids accidental "graph ignored, LLM answered" behavior.
- Makes debugging transparent for first live loop.

(LLM paraphrase can be optional later, fed only with this context.)

---

## 3) Minimum viable interaction loop (end-to-end)

### 3.1 Ordered cycle

1. Receive `{person_id, text}`.
2. Build `InputActivationPacket`.
3. Inject into Verdant pipeline entry (`process_input`/attention path).
4. Run one cognition cycle (activation -> memory -> basin/thermo updates).
5. Capture post-cycle state summary.
6. Render response via `StateToTextAdapter`.
7. Persist interaction record + memory event ledger.
8. Return response.

### 3.2 What can be deferred

- Rich NLU parsing.
- LLM stylistic rewriting.
- Advanced episodic summarization.
- Full partition router.

### 3.3 What is non-negotiable

- Real graph activation path is executed.
- Response is derived from resulting state.
- Interaction is durably written with `person_id` and timestamps.
- Next interaction reads that persisted record and can reference it.

---

## 4) Memory bootstrapping (compatible with future partitions)

Before full partition system, add **bootstrapped relational event log** that future migration can
consume directly.

### 4.1 Write two artifacts per interaction

1. `interactions/<person_id>/events.jsonl`
   - append-only per turn record.
2. `interactions/<person_id>/state_index.json`
   - compact rolling summary (last_seen, top recurring concepts, trust/valence sketch, anchors).

### 4.2 Event schema (v0 forward-compatible)

```json
{
  "event_id": "evt_uuid",
  "person_id": "p_123",
  "session_id": "s_abc",
  "ts_utc": "...",
  "input_text": "...",
  "resolved_nodes": [{"node_id": "n:care", "w": 0.72}],
  "top_nodes_post": [{"node_id": "n:trust", "a": 0.88}],
  "top_basins_post": [{"basin_id": "b3", "score": 0.77}],
  "coherence": {"h1_valid": true, "hci": 0.12},
  "thermo": {"t_g": 0.63, "entropy": 0.41},
  "response_text": "...",
  "relational_tags": ["supportive", "repair"],
  "schema_version": "interaction-v0"
}
```

### 4.3 Why this is enough now

- Durable continuity starts immediately.
- Compatible with future episodic/relational partition loader.
- Avoids throwaway prototype data.

---

## 5) Recommended build order (fastest path to alive)

### Step 1 — Input adapter + contracts (Day 1)

- Add `TextInputAdapter` and `InputActivationPacket`.
- Wire into existing pipeline entrypoint.
- Unit test: text -> non-empty activation packet -> graph receives activations.

### Step 2 — Output adapter + deterministic renderer (Day 1-2)

- Add `StateToTextAdapter` and `OutputRenderContext`.
- Render from top nodes/basins/thermo/coherence only.
- Unit test: fixed state snapshot -> deterministic response.

### Step 3 — Interaction service loop (Day 2)

- Add `InteractionService.handle_turn(person_id, text)`.
- Sequence input->process->render->persist->return.
- Integration test with 2-turn conversation.

### Step 4 — Memory bootstrap persistence (Day 2-3)

- Write per-person `events.jsonl` + `state_index.json` updates.
- Read last N events on next turn for continuity cues.
- Test: restart kernel, continue conversation, memory still present.

### Step 5 — Colab live harness (Day 3)

- Minimal notebook cell/UI loop (`input()`/print or tiny Gradio textbox).
- Persist to Drive path.
- Smoke test 10-turn session with one person.

### Step 6 — Guardrails & observability (Day 3-4)

- Add counters: activation coverage, unresolved token rate, write latency.
- Add invariants: `person_id` required, write success required before response finalize.

---

## 6) Minimal module map (suggested)

- `verdant/io/input_adapter.py`
- `verdant/io/output_adapter.py`
- `verdant/io/interaction_service.py`
- `verdant/io/schemas.py`
- `verdant/io/persistence.py`

No major refactor required; bolt on cleanly to current runtime.

---

## 7) Acceptance criteria for "alive v0"

System is "alive" at minimum meaningful threshold when all are true:

1. Human text causes measurable graph activation changes.
2. Response text is derived from those changes.
3. Turn events are persisted per person.
4. Restarting runtime does not lose continuity.
5. Turn N+1 can reference information from prior persisted turns for the same person.

If any one fails, alive threshold is not met yet.

---

## 8) First implementation cuts to avoid (for now)

- Do **not** start with full partition router.
- Do **not** start with LLM-only NLU/NLG wrappers.
- Do **not** add multi-human concurrency first.
- Do **not** optimize file format before loop reliability is proven.

Get the loop alive first, then scale architecture layers already designed.
