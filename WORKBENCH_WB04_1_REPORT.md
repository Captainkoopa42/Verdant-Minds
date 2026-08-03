# Verdant Workbench WB-04.1
## Editable Teaching Records Patch

**Status:** Complete and verified  
**Baseline:** WB-04 Curriculum Studio + Grammar Lab / M19 engine  
**Purpose:** Replace pressure for increasingly automatic language parsing with a common editable teaching representation.

## Why this patch exists

The practical teaching problem does not require Verdant Workbench to solve unrestricted English before users can work with the engine. A human, researcher, script, or external LLM can instead provide the same explicit teaching structure and review/edit it before anything reaches Verdant.

The governing rule is now:

> **Workbench validates the structure and provenance of a curriculum; it does not decide whether the curriculum is true.**

This makes misinformation, contradictions, fictional worlds, custom terminology and deliberately malformed knowledge experiments first-class laboratory inputs rather than exceptional cases.

## New source format

WB-04.1 adds:

```text
teaching_bundle_json
schema: verdant.teaching.bundle.v1
```

An editable bundle has two independent regions:

```text
language_scaffold
    optional executable parser rules already supported by Verdant
    optional lexicon entries already supported by Verdant

items[]
    source text
    explicit concepts
    explicit relations
    explicit claims
    grammar annotations
    lexicon annotations
    provenance
    context / confidence
```

The source text, grammar annotations and lexicon annotations are not silently interpreted into semantic truth. The compiled concepts, relations and claims are exactly those the author supplied.

## UI change

Curriculum Studio now contains an **Editable Teaching Record Builder** with fields for:

- source sentence;
- item ID and context;
- concepts;
- relations;
- claims / contradictions;
- grammar annotations;
- lexicon annotations;
- provenance;
- optional existing-engine parser scaffold rules;
- optional existing-engine scaffold lexicon.

The builder produces ordinary editable `teaching_bundle_json`. The JSON remains visible and can be changed directly. A separate full editable template can also be loaded from the API.

This means an external LLM can simply be asked to produce the same record format, pasted into Workbench, inspected, edited and frozen. A future provider API will populate the exact same structure rather than creating a second teaching path.

## Executable language scaffold

A frozen `.vcurr` may now carry an optional `language_scaffold.json`.

When queued, Workbench places the operations in deterministic order:

```text
grammar rules
-> lexicon entries
-> explicit world-teaching ExperienceCommands
```

The scaffold only invokes grammar/lexicon mechanisms already present in the Verdant engine. Arbitrary grammar annotations may still be stored in teaching records, but they do not pretend to become executable parser logic unless the engine supports them.

## Deliberate false and contradictory information

The validator performs schema/range/type checks. It does not perform a reality check.

The proof curriculum intentionally supplied both:

```text
kren has_property hot     AFFIRMED
kren has_property hot     NEGATED
```

Both records were accepted, executed and produced one canonical contradiction in Verdant:

```text
claim_count          2
contradiction_count  1
```

This confirms that Workbench does not sanitize contradictory teaching before Verdant's own epistemic machinery receives it.

## No hidden prose inference proof

The proof used source text that intentionally did **not** describe the explicit compiled relation. The source sentence was preserved in evidence provenance, while the compiled world relation remained exactly:

```text
kren --moves_toward--> tar
```

No concept from the unrelated sentence was silently created.

Therefore, in editable-record mode:

```text
source sentence != hidden parser output
explicit teaching plan == engine input
```

## Curriculum package changes

`.vcurr` remains backwards compatible with earlier packages and now may contain:

```text
manifest.json
source/source.txt
curriculum_ir.json
compiled_commands.jsonl
language_scaffold.json
hashes.json
```

The curriculum digest incorporates the scaffold whenever one is present. Earlier curricula with no scaffold retain the existing command-only digest behavior, including the M19 reference hash.

## Verification

### Workbench

```text
23 passed
```

This includes four WB-04.1-specific tests covering:

- explicit teaching records with no prose inference;
- executable grammar/lexicon scaffold queueing;
- deliberate contradictory claims;
- editable-template API and live UI surface.

### Engine regression

All **189** existing engine tests were reverified in fresh partitions:

```text
124 passed  core/kernel/media/language/etc.
32 passed   M12-M15
16 passed   M16-M17
9 passed    M18
8 passed    M19 benchmark (fresh individual processes where required)
--------------------------------
189 passed
```

The known long-single-process benchmark slowdown remains environmental; no engine test failed.

### Combined verified state

```text
189 engine + 23 Workbench = 212 passing tests
```

## Machine proof

`workbench/artifacts/wb041_editable_teaching_proof.json`

All proof gates passed:

- editable bundle compiled;
- source sentence did not act as a hidden semantic parser;
- language scaffold queued before experiences;
- grammar rule installed;
- lexicon installed;
- deliberately contradictory claims accepted;
- frozen package round-tripped its scaffold exactly.

## Architectural consequence

The teaching architecture is now:

```text
Human -----------+
External LLM ----+
Provider API ----+--> Editable Teaching Record --> Validate --> Freeze .vcurr --> Verdant
Import / Script -+
```

An LLM is therefore optional. It can save authoring labor, but it gains no privileged cognitive role.

## Next

Resume the main roadmap at **WB-05 — Structures + Forensic Explorer**.

The teaching-path correction is complete; no new language intelligence is required before opening the engine's learned structures to forensic inspection.
