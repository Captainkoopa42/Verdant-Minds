#!/usr/bin/env python3
"""Monolithic integration test runner for the Verdant‑Minds system.

This script validates core module imports, executes multiple
system cycles, and logs per‑cycle diagnostics including processing
status, confidence scores, memory information, ethical assessment,
and per‑module execution times.  Failures in individual blocks are
captured and reported without terminating the overall test run.
"""

import argparse
import os
import sys
import time
import traceback
from typing import Dict, Any, Tuple

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_PACKAGE_ROOT = os.path.join(REPO_ROOT, "Verdant Source Codes")

# Ensure repository paths are available for imports
if SRC_PACKAGE_ROOT not in sys.path:
    sys.path.append(SRC_PACKAGE_ROOT)

# ---------------------------------------------------------------------------
# Import validation
# ---------------------------------------------------------------------------
REQUIRED_MODULES = {
    "MemoryWeb": "src.memory.memory_web",
    "EthicsKing": "src.kings.ethics_king",
    "ReasoningPlanningBlock": "src.blocks.reasoning_planning_block",
    "UnifiedSystem": "src.core.system",
}

missing_modules: Dict[str, str] = {}
for name, module_path in REQUIRED_MODULES.items():
    try:
        __import__(module_path)
        print(f"[IMPORT] {name} loaded successfully from {module_path}")
    except Exception as exc:  # pragma: no cover - diagnostic output
        missing_modules[name] = str(exc)
        print(f"[IMPORT-FAIL] {name} ({module_path}): {exc}")

if missing_modules:
    print("[WARN] Missing modules detected; functionality may be limited:")
    for name, err in missing_modules.items():
        print(f"       - {name}: {err}")

# ---------------------------------------------------------------------------
# System initialization
# ---------------------------------------------------------------------------
try:
    from src.core.system import UnifiedSystem  # type: ignore
except Exception as exc:
    print("[❌] Failed to import UnifiedSystem:", exc)
    traceback.print_exc()
    sys.exit(1)

print("[🌿] Bootstrapping Verdant‑Minds Unified System...")
try:
    SYSTEM = UnifiedSystem()
except Exception as exc:
    print("[❌] UnifiedSystem initialization failed:", exc)
    traceback.print_exc()
    sys.exit(1)
print("[✅] System initialization complete.\n")

# ---------------------------------------------------------------------------
# Helper for executing a single processing cycle with block-level protection
# ---------------------------------------------------------------------------
def run_cycle(input_text: str) -> Tuple[Any, Dict[str, Any], Dict[str, str]]:
    """Execute a processing cycle with block-level error capture.

    Returns
    -------
    chunk: CognitiveChunk or ``None`` if creation failed
    timings: mapping of block name to execution time (seconds or 'error')
    errors: mapping of block name to error strings
    """

    errors: Dict[str, str] = {}
    timings: Dict[str, Any] = {}

    chunk = None
    try:
        chunk = SYSTEM.blocks["SensoryInput"].create_chunk_from_input(input_text)
    except Exception as exc:
        errors["SensoryInput"] = str(exc)

    for block_name in SYSTEM.processing_order:
        start = time.time()
        try:
            if chunk is not None:
                chunk = SYSTEM.blocks[block_name].process_chunk(chunk)

                if block_name == "InternalCommunication":
                    try:
                        chunk = SYSTEM.three_kings_layer.data_king.oversee_processing(chunk)
                    except Exception as exc:  # pragma: no cover - diagnostic
                        errors["DataKing"] = str(exc)

                elif block_name == "EthicsValues":
                    try:
                        chunk = SYSTEM.three_kings_layer.ethics_king.oversee_processing(chunk)
                    except Exception as exc:  # pragma: no cover - diagnostic
                        errors["EthicsKing"] = str(exc)

                elif block_name == "ActionSelection":
                    try:
                        chunk = SYSTEM.three_kings_layer.forefront_king.oversee_processing(chunk)
                    except Exception as exc:  # pragma: no cover - diagnostic
                        errors["ForefrontKing"] = str(exc)
                    try:
                        chunk = SYSTEM.three_kings_layer.oversee_processing(chunk)
                    except Exception as exc:  # pragma: no cover - diagnostic
                        errors["ThreeKingsCoordination"] = str(exc)
        except Exception as exc:
            errors[block_name] = str(exc)
            chunk = chunk  # keep previous chunk if available
        finally:
            timings[block_name] = round(time.time() - start, 3) if block_name not in errors else "error"

    if chunk is not None:
        # Mirror UnifiedSystem.process_input metrics for comparison
        chunk.update_section(
            "processing_metrics_section",
            {
                "processing_times": timings,
                "total_processing_time": sum(
                    t for t in timings.values() if isinstance(t, (int, float))
                ),
            },
        )

    return chunk, timings, errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Monolithic integration test runner for the Verdant-Minds system."
    )
    parser.add_argument(
        "--user-input",
        type=str,
        help="Process a single user input instead of running automated test cycles.",
    )
    args = parser.parse_args()

    if args.user_input:
        print("\n[🧠] Processing interactive input...")
        cycle_start = time.time()
        chunk, timings, errors = run_cycle(args.user_input)
        cycle_time = round(time.time() - cycle_start, 3)

        if chunk is not None and not errors:
            memory_data = chunk.get_section_content("memory_section") or {}
            reasoning_data = chunk.get_section_content("reasoning_section") or {}
            ethics_data = chunk.get_section_content("ethics_king_section") or {}

            confidence = reasoning_data.get("confidence_score", "N/A")
            ethics_assessment = ethics_data.get("evaluation", {}).get("status", "N/A")
            memory_changes = {
                "retrieved": len(memory_data.get("retrieved_concepts", [])),
                "stored": len(SYSTEM.memory_web.memory_store),
            }

            print(f"[✅] Cycle completed in {cycle_time}s")
            print(f"     ↪ Confidence Score: {confidence}")
            print(f"     ↪ Ethical Assessment: {ethics_assessment}")
            print(f"     ↪ Memory Changes: {memory_changes}")
            print(f"     ↪ Module Times: {timings}")
        else:
            print("[⚠️] Cycle encountered errors")
            for blk, err in errors.items():
                print(f"     ↪ {blk}: {err}")
            print(f"     ↪ Partial Module Times: {timings}")
    else:
        # ---------------------------------------------------------------------------
        # Test loop
        # ---------------------------------------------------------------------------
        TEST_CYCLES = 10
        successful_cycles = 0

        for cycle in range(1, TEST_CYCLES + 1):
            print(f"\n[🧠] Starting Cycle {cycle}...")
            cycle_start = time.time()

            chunk, timings, errors = run_cycle(f"Cycle input test #{cycle}")
            cycle_time = round(time.time() - cycle_start, 3)

            if chunk is not None and not errors:
                # Extract diagnostics
                memory_data = chunk.get_section_content("memory_section") or {}
                reasoning_data = chunk.get_section_content("reasoning_section") or {}
                ethics_data = chunk.get_section_content("ethics_king_section") or {}

                confidence = reasoning_data.get("confidence_score", "N/A")
                ethics_assessment = ethics_data.get("evaluation", {}).get("status", "N/A")
                memory_changes = {
                    "retrieved": len(memory_data.get("retrieved_concepts", [])),
                    "stored": len(SYSTEM.memory_web.memory_store),
                }

                print(f"[✅] Cycle {cycle} completed in {cycle_time}s")
                print(f"     ↪ Confidence Score: {confidence}")
                print(f"     ↪ Ethical Assessment: {ethics_assessment}")
                print(f"     ↪ Memory Changes: {memory_changes}")
                print(f"     ↪ Module Times: {timings}")
                successful_cycles += 1
            else:
                print(f"[⚠️] Cycle {cycle} encountered errors")
                for blk, err in errors.items():
                    print(f"     ↪ {blk}: {err}")
                print(f"     ↪ Partial Module Times: {timings}")

        # ---------------------------------------------------------------------------
        # Final summary
        # ---------------------------------------------------------------------------
        print("\n[📊] Verdant‑Minds Monolithic Test Run Complete")
        print(f"     Total Cycles Attempted: {TEST_CYCLES}")
        print(f"     Successful Cycles     : {successful_cycles}")
        print(
            f"     Failure Rate          : {round((1 - successful_cycles / TEST_CYCLES) * 100, 2)}%"
        )

