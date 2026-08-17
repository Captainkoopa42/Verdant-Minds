# V1 source tree

This directory contains the runnable Python source and one non-runnable TypeScript sketch. The repository is not packaged, so this directory must be on Python's import path for direct API use.

## Canonical implementation

`src/core/system.py` defines the runnable `UnifiedSystem`. Root scripts configure the path automatically; direct imports require:

```bash
PYTHONPATH="Verdant Source Codes" python -c "from src.core.system import UnifiedSystem; UnifiedSystem()"
```

## Directory map

| Directory | Present contents |
| --- | --- |
| `src/core/` | Python orchestrator, `CognitiveChunk`, system learning, and an incomplete TypeScript sketch |
| `src/blocks/` | Nine processing-block implementations plus lowercase import wrappers |
| `src/memory/` | NetworkX memory, NumPy ECWF, bridge, and lowercase wrappers |
| `src/kings/` | Three governance components, coordinator, and lowercase wrappers |
| `src/integration/` | Interaction manager, integration framework/tests, wiring helper, and visualizer |
| `src/utils/` | Logger setup and JSON-lines metrics logger |
| `src/auth/` | Standalone in-memory RBAC/JWT prototype |
| `src/config/` | No implementation in V1 |
| `src/services/` | No implementation in V1 |
| `docs/` | No separate source-local document set; use repository-root `docs/` |
| `examples/` | No example programs; use the two root runners |

## Uppercase and lowercase Python files

Uppercase files such as `PatternRecognitionBlock.py` contain implementations. Lowercase files such as `pattern_recognition_block.py` are compatibility wrappers used by `system.py`. Both are intentional parts of the current import layout.

## TypeScript boundary

`src/core/UnifiedSystem.ts` imports TypeScript components and types that do not exist on this branch. No `package.json` or TypeScript configuration is present. Treat it as a design artifact, not a buildable second implementation.

## Detailed reference

Use the repository-root [architecture](../docs/architecture.md), [walkthrough](../docs/walkthrough.md), and [API guide](../docs/api.md). Those documents replace the prior inventory text files that named absent modules and documents.
