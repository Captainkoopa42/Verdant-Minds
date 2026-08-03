# Verdant Workbench 1.0.1 — Release Audit & Polish

This pass was intentionally non-cognitive. It checked the completed WB-00 through WB-09 laboratory for release inconsistencies and tightened the parts that affect outside verification.

## Findings resolved

1. **Stale development labels** — Workbench package/version labels and entry documentation were updated to 1.0.1 / V5. Historical milestone strings remain only where retained for regression compatibility or historical reports.
2. **Build identity** — experiments now record exact engine, Workbench, and dependency-lock SHA-256 identities. A declared mismatch blocks experiment execution/reproduction rather than silently comparing unlike builds.
3. **Dependency reproducibility** — the tested Python direct-dependency set is frozen in `requirements-lock.txt`. Frontend source dependencies are explicitly version-pinned; the checked-in dependency-free `dist/` remains the release runtime because this hosted npm registry cannot produce a trustworthy transitive lockfile.
4. **Evidence surface** — canonical evidence, concepts, relations, claims, contradictions, structural challenges, and P/Q records are searchable through a read-only full-debug snapshot surface.
5. **Timeline surface** — run ancestry, checkpoints, and committed event markers are directly navigable rather than only indirectly visible through other screens.
6. **Verification ergonomics** — `verify_release.py` encodes the safe engine partitions and fresh-process Workbench test method, including node-level handling for the benchmark/visualization tests that can trigger the hosted environment's cumulative slowdown.
7. **Entry documentation** — top-level README and operations docs now describe V5 installation, launch, verification, and scientific/security boundaries.

## Explicit remaining non-blockers

- Workbench is local-first, not a production authenticated hosted service.
- Plugin subprocess isolation is not an OS security sandbox; do not run untrusted plugins.
- React/TypeScript source rebuild needs a transitive npm lock generated on a normal registry before replacing the checked-in dependency-free UI build.
- Scaling to very large organisms remains a post-1.0 empirical/engineering problem.

None of these are unfinished WB-00 through WB-09 architecture boxes.
