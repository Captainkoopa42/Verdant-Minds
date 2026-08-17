# Interpreting the V2 branch

## V2 as a research generation

The `V2` branch is the browsable collection for this stage of Verdant research. It can continue to receive corrections and documentation. It does not imply that every file was authored together or that all artifacts use the same interface and experiment protocol.

## Layers visible in the current branch

1. **Older compatibility layer** — root packaging, `INSTALL.md`, old API/architecture docs, and most `scripts/` targeted a V1-style `usm.UnifiedSyntheticMind` interface.
2. **Active V2 core** — `ethomorphic/`, `verdant/`, and `tests_v2/` implement the redesigned Pydantic/JSON architecture.
3. **Cultivation layer** — deterministic local and optional hosted providers drive repeated sessions and state capture.
4. **Basin/intervention layer** — community telemetry, local micro-pipelines, routing, ablation, scrambling, and comparisons were added around the core.
5. **Analysis/results layer** — scripts and derived outputs study temporal edge ordering, basins, nulls, and timescales.
6. **Manuscript layers** — `paper/` is an earlier modular draft; the long standalone paper directory is a later archived package.
7. **Colab layer** — notebooks and cell fragments try to reproduce the later experiments but retain incorrect package paths and one absent analysis command.

## Why the previous docs conflicted

The root README had been updated to foreground the later scaffolding story, while `INSTALL.md`, `docs/api.md`, and `docs/architecture.md` still described the older `usm` package. As a result, the branch looked current from the front page but sent a reader into nonexistent packages and methods.

This documentation pass replaces those competing instructions with the actual V2 interface and labels historical layers in place.

## Results are from multiple scales

The branch contains at least three distinct result contexts:

- manuscript short replication claims (5–14 emergents);
- current-code 20-cycle audit reproduction (18–29 emergents);
- tracked seed artifacts (52–95 emergents) and a 62-emergent representative directory.

These should never be aggregated without naming the generating protocol and source state.

## Moving forward

The highest-value next engineering generation would first repair package identity, then make lineage a first-class directed event separate from undirected associations. After that, the existing cultivation and intervention framework can be reused to test whether selective temporal lineage actually emerges.
