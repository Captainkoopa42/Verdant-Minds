# Verdant Workbench — WB-04 Engineering Report

## Curriculum Studio + Language / Grammar Lab

**Workbench version:** `0.4.0-wb04`  
**Engine baseline:** Verdant Minds Independent Rebuild through Milestone 19  
**Cognitive engine changes required:** none

## 1. Milestone purpose

WB-04 turns teaching into a laboratory artifact instead of a Python-runner editing task.

The required control flow is now:

```text
SOURCE
  -> PARSE
  -> COMPILE
  -> REVIEW
  -> FREEZE IMMUTABLE .vcurr
  -> QUEUE
  -> VERDANT WORKER
```

The Language / Grammar Lab separately exposes the existing deterministic `verdant_language` path so grammar rules, lexicon state and parse plans can be inspected and taught without pretending that a Workbench language model is part of Verdant cognition.

The architecture rule remains unchanged:

> The Workbench may author, compile, schedule and observe teaching. It does not become a hidden cognitive layer.

## 2. Curriculum compiler

New backend module:

```text
workbench/backend/verdant_workbench/curriculum.py
```

The v1 compiler is deliberately narrow. It supports two source formats.

### 2.1 `primitive_lines`

A small explicit authoring language:

```text
PRESENCE lesson-1 kren tar vel
EDGE lesson-1 kren linked tar | weight=0.8 | directed=false
EDGE lesson-1 tar linked vel | weight=0.8 | directed=false
```

The compiler deterministically produces `ExperienceCommand` records with explicit provenance and content hashes.

### 2.2 `experience_jsonl`

One complete engine `ExperienceCommand` JSON object per nonblank line.

This is the lossless laboratory path for existing corpora and benchmark curricula. Workbench validates every object against the engine model; it does not reinterpret the command.

### 2.3 Intentional boundary

WB-04 does **not** claim to compile arbitrary English prose into correct teaching primitives. That is intentionally deferred to optional provider-assisted authoring later. The current compiler refuses to pretend that prose has been understood when it has not.

## 3. Immutable `.vcurr` package

A frozen curriculum is a deterministic ZIP artifact containing:

```text
manifest.json
source/source.txt
curriculum_ir.json
compiled_commands.jsonl
hashes.json
```

ZIP entry timestamps are fixed and files are written in deterministic order, so identical reviewed input produces identical package bytes in the same implementation.

The package records:

- schema and compiler version;
- original source hash;
- compiled-command hash;
- state-dimension declaration;
- item count;
- exact parsed IR;
- exact engine commands;
- per-file internal SHA-256 values.

Curriculum artifacts are stored through the existing content-addressed artifact store. The SQLite catalog keeps project/title/version metadata but does not become an alternate teaching truth store.

Identical packages deduplicate by content while still allowing immutable catalog versions.

Schema:

```text
workbench/schemas/curriculum/curriculum-v1.json
```

## 4. Persistent curriculum catalog

WB-04 adds a `curricula` metadata table with:

```text
curriculum_id
project_id
title
version
source_format
source_sha256
compiled_sha256
artifact_sha256
artifact_size_bytes
item_count
state_dim
compiler_version
created_at
```

Editing does not rewrite a frozen curriculum. Freezing again creates the next catalog version.

## 5. Curriculum-to-run execution

The run queue now accepts a third executable command class:

```text
TEACH
PROBE
EXPERIENCE
```

`EXPERIENCE` contains an exact validated engine `ExperienceCommand`.

When a `.vcurr` is queued:

1. the Workbench verifies the artifact hash;
2. the package verifies its internal hashes;
3. every compiled command is validated again;
4. the run/project and declared state dimension are checked;
5. each command is appended to the persistent run queue in package order;
6. a `CURRICULUM_QUEUED` Workbench control event records the curriculum ID/hash and queue IDs;
7. execution passes the command through the same isolated `VerdantEngineAdapter.submit_experience()` path used by direct engine integration.

No curriculum is executed by the browser itself.

## 6. M19 reference curriculum proof

WB-04 exposes the exact Milestone 19 alien-world teaching sequence as a Workbench template.

Reference:

```text
30 ExperienceCommand items
state dimension declaration: 16
compiled SHA-256:
38ffb6c25056b7f0134e5f2dd923fe08b9cca05318a66f38e3c7582eb102ce4b
```

The Workbench compiler reproduced the benchmark harness hash exactly.

The reviewed curriculum was frozen as `.vcurr`, queued into an isolated Workbench organism, and all 30 commands completed.

Final Workbench state:

```text
concepts   20
relations  15
fingerprint
d46c43ee0bc6d3b0e1bbe83b62486062b8225ccf74f9d94fccb2435b57d3300f
```

The exact same 30 commands were then supplied directly to a `VerdantKernel` through `VerdantDevelopmentPipeline` with the same seed, field dimension and run label.

Direct fingerprint:

```text
d46c43ee0bc6d3b0e1bbe83b62486062b8225ccf74f9d94fccb2435b57d3300f
```

Therefore the WB-04 curriculum path passed the central equivalence check:

```text
reviewed source
 -> frozen .vcurr
 -> Workbench queue
 -> isolated worker
 -> Verdant

produced the same canonical engine result as

the same commands
 -> direct Verdant developmental pipeline
```

This does not claim the Workbench reproduces every M19 benchmark arm configuration; it establishes lossless execution of the reference curriculum command stream through the Workbench boundary.

A deterministic reference package is included at:

```text
workbench/artifacts/m19_reference_curriculum.vcurr
```

## 7. Grammar Lab

WB-04 adds engine-worker actions for:

```text
grammar status
grammar parse/semantic-plan preview
teach grammar rule
teach lexeme
teach reviewed sentence
```

These use the existing:

```text
verdant_language.ControlledGrammarAnalyzer
verdant_language.VerdantLanguagePipeline
```

rather than a new Workbench parser.

### 7.1 Rule browser

The UI displays the engine's declared rule specifications and whether evidence-backed rule concepts currently exist in that organism.

### 7.2 Lexicon browser/editor

The UI displays recognized surface form -> lemma -> category mappings from the organism's canonical lexeme concepts and can teach new lexeme entries through the existing engine language curriculum path.

### 7.3 Pure semantic-plan preview

Before returning a preview, the adapter records the organism fingerprint and state revision, executes the analyzer/plan operation, then verifies both values are unchanged.

The reference proof taught:

```text
transitive_svo
noun: dog
verb: chase / chases / chased
noun: child
```

Preview:

```text
dog chases child.
```

produced:

```text
frame_type  transitive
subject     dog
predicate   chase
object      child
parsed      true
```

and left both fingerprint and state revision unchanged.

The reviewed sentence was then committed through the actual `VerdantLanguagePipeline`, producing an evidence-backed language event and claim.

### 7.4 Current grammar-artifact boundary

The Grammar Lab's state-dependent rule/lexeme/sentence operations are engine-backed and auditable, but WB-04 does not yet package arbitrary multi-step grammar teaching sessions as a separate freezeable grammar-specific curriculum dialect. `.vcurr` v1 freezes exact `ExperienceCommand` streams. This keeps the first artifact contract simple and prevents state-dependent parsing from being falsely represented as state-independent compilation.

## 8. API additions

Curriculum:

```text
GET  /api/v1/curricula/templates/m19-alien
POST /api/v1/curricula/compile
POST /api/v1/curricula/freeze
GET  /api/v1/curricula
GET  /api/v1/curricula/{curriculum_id}
POST /api/v1/runs/{run_id}/curricula/{curriculum_id}/queue
```

Grammar:

```text
GET  /api/v1/runs/{run_id}/grammar
POST /api/v1/runs/{run_id}/grammar/preview
POST /api/v1/runs/{run_id}/grammar/rules/teach
POST /api/v1/runs/{run_id}/grammar/lexemes/teach
POST /api/v1/runs/{run_id}/grammar/sentences/teach
```

## 9. UI additions

The verified dependency-free browser UI now has four operational surfaces:

```text
Organism
Cultivate
Curriculum
Grammar
```

### Curriculum Studio

Provides:

- title / source format / state-dimension controls;
- explicit source editor;
- M19 reference-loader;
- Parsed inspector;
- Compiled exact-command inspector;
- Diff against a frozen baseline;
- Freeze reviewed `.vcurr`;
- immutable curriculum list/version selection;
- load frozen source;
- queue frozen curriculum into the selected run.

### Grammar Lab

Provides:

- rule state and teach controls;
- lexicon state and lexeme teaching;
- sentence editor;
- pure parse/semantic-plan preview;
- reviewed sentence teaching;
- enabled-rule/revision display.

Explorer, Structures, Evidence, Experiments, Timeline, Connections and Engineering remain intentionally reserved rather than faked.

## 10. Verification state

All pre-Workbench engine tests remain unchanged.

Verified engine partitions:

```text
124  kernel / chunk / language / claims / ECWF / governance /
     shards / objects / workspace / sensory / media / perception
 32  M12-M15 development / plasticity / structures / compilation
 16  M16-M17 interaction / hierarchy
  9  M18 refolding
  8  M19 benchmark tests (verified in fresh individual processes where needed)
---
189 engine tests
```

Workbench suite:

```text
19 passed
```

The six WB-04-specific tests cover:

1. exact M19 template/compile/freeze hash identity;
2. Workbench curriculum execution vs direct engine fingerprint equivalence;
3. primitive-line compilation and frozen-baseline diff;
4. pure Grammar Lab preview plus engine-backed language teaching;
5. curriculum/grammar REST routes;
6. served Curriculum Studio / Grammar Lab surfaces.

Combined verified total:

```text
189 engine + 19 Workbench = 208 passing tests
```

The known long-single-pytest-process slowdown still exists in this environment. M19 benchmark cases were therefore reverified in fresh processes instead of interpreting wall-time timeout as a test failure.

## 11. Frontend build note

The dependency-free `workbench/frontend/dist/` application is syntax-checked with Node and exercised through FastAPI tests.

The repository retains React/TypeScript source as the target UI codebase. `tsc` is present in this container, but the React / React DOM modules and type packages are not available in the environment, so a complete React compile cannot be truthfully claimed here. The operational checked-in browser build does not depend on those packages.

## 12. Milestone exit criteria

WB-04 exit target:

> A user can author, review, freeze and run the M19 alien curriculum entirely through Workbench, while Grammar Lab exposes the existing deterministic language path for rule/lexicon/parse inspection.

Status:

```text
M19 template available in Workbench                    PASS
source remains inspectable                             PASS
compiled commands remain inspectable                   PASS
compiled hash equals M19 reference                     PASS
review hash locked before freeze                       PASS
immutable deterministic .vcurr produced                PASS
frozen version cataloged                               PASS
curriculum queues without Python editing               PASS
all 30 commands execute through isolated worker        PASS
final state matches direct engine command stream       PASS
grammar rules inspectable                              PASS
lexicon inspectable / teachable                        PASS
parse / semantic plan preview is non-mutating          PASS
reviewed language statement can be committed           PASS
```

**WB-04 COMPLETE.**

## 13. Next target

### WB-05 — Structures + Forensic Explorer

The next stage should expose the internal organization already produced by M14-M18:

```text
P/Q candidate lists
promotion gates
frozen topology
constituent evidence
uses
interaction reports
ablation/restoration
challenge/refold lineage
replay formation
raw event references
```

The first WB-05 proof should select a real P object from a cultivated run, trace it back to the exact events/evidence that formed it, execute a causal ablation/restoration from the Workbench, and replay the recorded formation window without rerunning or altering the organism.
