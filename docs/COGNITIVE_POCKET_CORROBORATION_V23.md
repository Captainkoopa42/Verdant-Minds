# Cognitive Pocket v2.3 — Corroboration and scaling

Research branch: test/cognitive-pocket-corroboration-v2-3, branched from v2.2 commit 75f923cf2b911b3dc4106b8b75b6b1cfcd84ff73. Earlier experiment branches and the native VDK remain untouched.

## Scope

V2.3 adds two research controls:
1. A conservative declared-provenance assessor. A claim only reaches \`provisionally_corroborated\` when at least two different (source_family, source_record_id) pairs support the same directed claim. Repeated labels, a copied source record, and source family reuse do not count as independence.
2. A synthetic scaling benchmark that increases query-chain size and irrelevant disconnected edges while giving flat BFS and indexed BFS exactly the same graph and query. Deterministic edge inspections are the primary metric; wall-clock time is descriptive only.

Conflicting reverse-directed claims are reported for review, not resolved by majority vote. Nothing is written into canonical P/Q, native relations, obligations or the original VDK.

## Critical limitations

- Provenance independence is based on declared metadata. The system cannot prove that two source families are controlled by different people, instruments, owners, data feeds or upstream documents.
- \`source_authenticity_verified\` is always false. SHA256 checksums and source labels do not authenticate evidence.
- A synthetic chain benchmark is not a real pocket-vs-flat benchmark over the full Verdant graph. Both methods are intentionally given identical graph data; indexed BFS currently uses the same traversal algorithm, so it should not be expected to show a speed advantage. The benchmark tests scaling behavior and result equivalence, not cognitive superiority.
- No autonomous sensing, source authentication, learned rule induction, canonical writeback, or obligation scheduling is implemented.

## Windows use

See [COGNITIVE_POCKET_V23_WINDOWS.md](COGNITIVE_POCKET_V23_WINDOWS.md).

CLI:
\`python -m verdant_pockets.corroboration_cli --out report.json --sizes 32,64,128,256 --irrelevant-per-node 4\`

Optional custom observations must be a JSON list with \`observation_id\`, \`source_ref\`, \`source_family\`, \`source_record_id\`, \`subject\`, \`predicate\`, \`object\`, and \`direction\` on every record. Output paths are exclusive-create and never overwrite.
