# Script inventory

These scripts are not one coherent V2 command surface.

| Script | Interface | Status on this branch |
| --- | --- | --- |
| `run_once.py` | `usm.UnifiedSyntheticMind` | Legacy; `usm` package absent |
| `kernel_loop.py` | `usm.UnifiedSyntheticMind` | Legacy; `usm` package absent |
| `verdant_repl.py` | `usm.UnifiedSyntheticMind` | Legacy; `usm` package absent |
| `verdant_telemetry.py` | `usm.UnifiedSyntheticMind` | Legacy; `usm` package absent |
| `verdant_llm_cultivator.py` | `usm.UnifiedSyntheticMind` plus Groq helper | Legacy; cannot run against active V2 without an adapter |
| `verdant_groq.py` | Standalone Groq client helper | Requires the Groq SDK and credentials; not the V2 system itself |

The active V2 experiment entry point is `python -m cultivation.cli run`, documented in [../cultivation/README.md](../cultivation/README.md).

The root `pyproject.toml` still declares console commands backed by the absent `usm` package. Those declarations and these legacy scripts are preserved as branch history; they should not be used as V2 installation or API instructions.
