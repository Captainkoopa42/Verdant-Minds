# WB-11 Curriculum Packs & Batch Cultivation

`verdant.curriculum.pack.v1` is a Workbench authoring/orchestration format for organizing many explicit teaching records into named sections.

It does **not** add a new cognition or semantic-inference pathway. The Workbench validates the pack, selects sections, merges explicit language scaffolds, annotates provenance, and deterministically flattens the selected records into the existing `verdant.teaching.bundle.v1` format. The existing curriculum compiler then produces the same `ExperienceCommand` objects used by manual curricula.

## Intended workflow

1. Build one record precisely in Manual Builder, or author/generate many records in a `.vcpack` file.
2. Import or paste the pack in Curriculum Studio.
3. Select one or more sections.
4. Compile/inspect the exact flattened teaching bundle.
5. Freeze the reviewed result as an immutable `.vcurr`.
6. Queue or run it through the ordinary run queue.
7. Optional section tests are ordinary recorded `PROBE` cues appended after cultivation. They are not automatic pass/fail claims.

## Pack shape

```json
{
  "schema": "verdant.curriculum.pack.v1",
  "title": "Foundations",
  "state_dim": 128,
  "sections": [
    {
      "section_id": "physics",
      "title": "Physical World",
      "enabled": true,
      "items": ["EditableTeachingItem records live here"],
      "tests": [
        {"test_id": "physics-probe-001", "cue_labels": ["gravity", "mass"]}
      ]
    }
  ]
}
```

The canonical JSON Schema is `workbench/schemas/curriculum/curriculum-pack-v1.json`.
