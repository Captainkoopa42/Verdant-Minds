# Interpreting the V1 branch

## What “V1” means here

`V1` is a complete browsable Verdant generation. A reader can select the branch and inspect its source, research writing, runners, and documentation together. This documentation does not require treating the branch as finished or preventing future work on it.

The branch name is also not proof that every present file originated during the earliest V1 work. A branch records its current complete file state, and support work can be added later.

## Evidence of later-added support work

Some source comments explicitly label methods as fixed, including `CognitiveChunk.get_section_content()`, `MemoryWeb.process_chunk()`, and `MemoryStorageBlock.process_chunk()`. The integration wiring module states that it was added because the original module was missing. The root loop controller, diagnostic runner, logging utility, visualizer, and focused regression tests also read as repair or observability work around the core generation.

Those files belong to the current V1 branch and should be documented. They should not be used to claim that the earliest V1 state already contained every repair.

## Relationship between code and the outline

The files under `Verdant Outline/` preserve a broad proposal, implementation narrative, validation claims, and roadmap. Some architecture names correspond to source files. Other statements exceed what can be verified from the branch, and `IV. IMPLEMENTATION STATUS.txt` contains malformed or incomplete text.

The correct reading order is:

1. use the current branch files to determine what exists;
2. use runnable checks to determine what executes;
3. use tests and experiment artifacts to determine what is supported;
4. read the outline as theory, history, interpretation, and proposed direction.

## Documentation reconciliation

Before this engineering pass, the root README described nonexistent installation and import paths and the small inventory text files listed absent frontend, configuration, documentation, service, and example files. The proposed V1 documentation replaces those competing instructions with one root entry point, one canonical `docs/` set, and directory-scoped guides.

The conceptual papers are intentionally retained. Their directory guide marks the evidence boundary instead of erasing the research record.

## Moving forward

Future experimental work can continue on V1 or another branch according to the author's research plan. When behavior changes, update the status table, walkthrough, tests, and evidence package together so a reader inspecting that branch sees one internally consistent generation.
