# Verdant Workbench WB-06
## Living Explorer

**Status:** Complete and verified  
**Baseline:** WB-05 Structures + Forensic Explorer / Milestone 19 Verdant engine  
**Purpose:** Turn the same recorded developmental history already exposed forensically into a time-indexed living visualization without allowing the presentation layer to invent cognition.

## Exit criterion

WB-06 was designed around one strict scientific requirement:

> The Living Explorer must animate only record-backed Verdant development, and the historical replay at the current head must agree exactly with a direct live projection of that same canonical state.

The implementation now satisfies that requirement for the current workspace, ECWF/resonance, plasticity, P/Q formation/use, structural challenge and refolding records.

## 1. New Living Explorer projection service

WB-06 adds `verdant_workbench.living`.

The service constructs read-only, time-indexed `verdant.workbench.living-frame.v1` frames and `verdant.workbench.living-timeline.v1` timelines from committed engine records.

A frame can expose:

```text
cycle / live-head status
concepts known by that cycle
recorded resonance scores
workspace foreground / admitted bindings
plastic associations and strengths
P candidate snapshots
promoted P structures and availability
Q candidate snapshots
promoted Q structures and availability
challenge/refold state
recorded event markers
level-of-detail accounting
frame SHA-256
```

The projection is not another state store. Canonical truth remains in Verdant.

## 2. The timeline is reconstructed from actual history

The Explorer does not generate a movie by guessing intermediate states.

Historical frames are keyed to cycles represented by real engine records, including:

```text
RESONANCE
WORKSPACE
PLASTICITY
P_CANDIDATE
P_PROMOTED
P_AVAILABILITY
P_USED
P_INTERACTION
Q_CANDIDATE
Q_PROMOTED
Q_AVAILABILITY
Q_USED
CHALLENGE
REFOLD
```

Concept appearance is bounded by recorded creation cycles. Plasticity uses the complete `proposed_associations` state contained in the applicable plasticity event. P/Q candidate views use their recorded observation snapshots. Promoted structures use their recorded creation cycle and recorded availability history.

Refolding is replayed from the actual refold event, including the parent becoming unavailable/dormant and the resulting child structures becoming visible according to their recorded records.

## 3. Projection is proven non-mutating

Constructing a living frame or an entire replay timeline is an inspection operation.

The projection service fingerprints the canonical organism before and after timeline construction.

Controlled WB-06 P timeline:

```text
canonical fingerprint before
4897c121114cdb0d0e85266ef3dc7de2d196135eeec4610f4f078eef85f32790

canonical fingerprint after
4897c121114cdb0d0e85266ef3dc7de2d196135eeec4610f4f078eef85f32790
```

Therefore:

```text
Living Explorer timeline construction -> canonical mutation = FALSE
```

This extends the WB-05 forensic-replay rule from individual structures to the whole time-indexed living view.

## 4. Live head and replay head are the same projection

The most important WB-06 consistency gate compares two independent paths:

```text
recorded history -> final replay frame

versus

current canonical state -> direct live frame
```

For the controlled P run, both produced the same frame hash:

```text
7576deeb87ce7db71cb2ed1169ecb947f7eb5fd9a37344239660b1013696ceae
```

So:

```text
H(final replay projection) = H(direct live-head projection)
```

This means live mode and replay mode are not separate visual stories with subtly different semantics. They terminate on the same view-model representation of the same organism.

## 5. Record-backed visual layers

The runnable browser Explorer uses an HTML canvas. Its main visual encodings are deliberately narrow and auditable.

### Concepts and resonance

A visible concept corresponds to a real concept record known by the selected cycle.

Node size can respond to the latest recorded resonance score available at that cycle. The node is not moved around to imply unrecorded semantic attraction.

### Workspace

A gold workspace highlight corresponds to an actual admitted/foreground workspace binding in the recorded workspace assessment for that cycle.

### Plasticity

A rendered plastic edge corresponds to a real bounded plastic association. Edge width maps to its recorded strength.

The view can visually distinguish an association that was newly created or reinforced at the selected recorded frame, but it does not synthesize intermediate learning events.

### P folds

A promoted-P boundary is drawn only from actual recorded P membership available at that frame. The boundary is presentation geometry surrounding known members; it is not a claim that Verdant internally stores that 2D shape.

### Q, challenge and refolding

Q promotions, structural challenges and refolding appear in the timeline only when their canonical events/records exist.

## 6. Presentation geometry is not cognitive geometry

WB-06 intentionally does **not** claim that a 2D canvas position is Verdant's internal manifold.

Concept coordinates are generated by a deterministic UI layout keyed from identifiers so that the same frame remains visually stable enough to inspect.

The application explicitly labels this:

```text
layout: deterministic display projection
```

and the Explorer text states that node placement is a display layout rather than internal cognitive geometry.

This distinction matters because the current engine has a continuous relational interface and field state, but WB-06 would be scientifically wrong to convert a convenient screen layout into a claim about the internal space.

ADR-013 records this rule.

## 7. Living controls

The Explorer now supports:

```text
PLAY RECORDING
PAUSE
PREVIOUS FRAME
NEXT FRAME
SCRUB TIMELINE
LIVE HEAD
```

Playback advances through recorded/projected frames only.

The frame inspector exposes at minimum:

```text
cycle
frame SHA-256
live/replay mode
counts
recorded event markers
workspace foreground
selected concept details
LOD accounting
```

When the Workbench receives new live events while the Explorer is open, it refreshes the timeline through the backend projection rather than inventing frontend-only cognitive state.

## 8. Explicit level of detail

Large graphs cannot be rendered naïvely forever, so WB-06 introduces bounded visualization without hiding that bounding occurred.

The living projection accepts `max_nodes` and `max_edges`.

Priority is given to current workspace-active concepts and members of promoted structures, followed by the remaining display candidates.

Every frame reports:

```text
total nodes
total edges
rendered nodes
rendered edges
omitted nodes
omitted edges
priority-node count
```

Controlled LOD proof deliberately requested only two nodes and one edge from a three-node/three-edge P state:

```text
total nodes       3
rendered nodes    2
omitted nodes     1

total edges       3
rendered edges    1
omitted edges     2
```

So rendering omission can never be confused with absence from Verdant.

## 9. Controlled developmental proof

The WB-06 machine proof exercises three different developmental stories.

### P development

The promoted P proof generated a 31-frame timeline.

Its recorded marker classes include:

```text
WORKSPACE
RESONANCE
PLASTICITY
P_CANDIDATE
P_PROMOTED
P_USED
```

At the head:

```text
concepts recorded through cycle   3
plastic associations              3
P candidates                      1
promoted P                        1
workspace active                  3
```

This verifies that the major low-level and fold-development layers visible in the Living Explorer are all backed by real records.

### Q development

A real M17 hierarchy checkpoint was projected into a 140-frame timeline.

The actual promoted object:

```text
layered_structure_6fff321a318a9ffefae1e723
```

appears at the recorded Q promotion point and remains visible at the head.

### Refolding

A real M18 refolding checkpoint was projected into a 187-frame timeline.

The timeline contains an actual `REFOLD` marker. At the final frame:

```text
parent available   false
child structures   2
```

for parent:

```text
structure_c9a28c27f80de00fe0ffa9a3
```

So the Living Explorer can already show a recorded mature fold becoming dormant and its two lineage-preserving children taking its place.

## 10. API surface

WB-06 adds two primary read-only routes:

```text
GET /api/v1/runs/{run_id}/explorer/frame
GET /api/v1/runs/{run_id}/explorer/timeline
```

Supported projection controls include:

```text
cycle
max_nodes
max_edges
max_frames
include_frames
```

These routes go through the existing run service and isolated engine worker boundary. They do not expose a second mutable state object inside FastAPI.

## 11. User interface implementation

The dependency-free browser build remains the runnable reference frontend in this environment because the available npm registry does not expose the selected React/Vite dependencies.

WB-06 upgrades that runnable UI with:

- canvas Living Explorer;
- live/replay state;
- time controls;
- event markers;
- workspace/resonance/plastic/P visual layers;
- forensic frame overlay;
- concept selection;
- explicit LOD reporting;
- frame hashes;
- automatic refresh when recorded events advance the organism.

React/TypeScript source remains retained as the intended frontend architecture, but the dependency-free served build is the version that was actually exercised here.

## 12. Verification

WB-06 adds seven dedicated Living Explorer tests covering:

1. non-mutating timeline projection and live/replay head agreement;
2. record-backed workspace/plasticity/P candidate/promotion/use visibility;
3. explicit LOD omission accounting;
4. actual Q promotion visibility;
5. actual refold visibility with dormant parent and two children;
6. API frame/timeline routes and hash agreement;
7. served Living Explorer canvas/time/forensic UI.

The WB-06 tests were verified in fresh partitions:

```text
3 passed   core living projection / P / LOD
2 passed   API + browser UI
1 passed   Q hierarchy projection
1 passed   refold projection
--------------------------------------
7 passed
```

The preceding Workbench suite was reverified in fresh partitions:

```text
29 prior Workbench tests passed
```

Therefore:

```text
Workbench integration tests   36
```

The unchanged Verdant M19 engine regression suite was also reverified:

```text
124 passed   core/kernel/media/workspace/etc.
 32 passed   M12-M15
 16 passed   M16-M17
  9 passed   M18
  5 passed   first M19 benchmark partition
  3 passed   second M19 benchmark partition
---------------------------------------------
189 engine tests
```

Combined verified project state:

```text
189 engine + 36 Workbench = 225 passing tests
```

As in earlier milestones, one very long all-in-one pytest process can slow excessively in this container. The logical suites were therefore verified in clean partitions; there were no observed failures.

## 13. Machine proof gates

`workbench/artifacts/wb06_living_explorer_proof.json` records eight passing gates:

```text
live_head_equals_replay_head       PASS
lod_reports_omission               PASS
p_development_is_visible           PASS
plasticity_layer_is_recorded       PASS
q_promotion_is_visible             PASS
refolding_is_visible               PASS
timeline_projection_is_non_mutating PASS
workspace_layer_is_recorded        PASS
```

`all_gates_pass` is `true`.

## 14. Scientific boundary

WB-06 supports the statement:

> Verdant Workbench can reconstruct a time-indexed visual history of the currently recorded developmental mechanisms, animate that history without mutating the organism, and make the final replay state agree exactly with the direct live projection while preserving explicit forensic references and rendering omissions.

WB-06 does **not** establish that the canvas layout is Verdant's true cognitive geometry, that visual proximity implies semantic distance, or that interpolated screen motion is itself an engine event.

## 15. Next target

### WB-07 — Experiment Manager / Verification Packages

WB-06 gives us the oscilloscope. WB-07 turns the existing M19 protocol into a general laboratory instrument.

The next exit criterion is:

```text
immutable .vexp manifest
+ locked engine/curriculum/seed/config
+ isolated multi-arm execution
+ declared interventions
+ recorded results/claims
+ reproduce / verify / fork / export
```

The four-arm M19 Ethomorphism benchmark should be runnable and independently verifiable through the Workbench without hand-editing Python.
