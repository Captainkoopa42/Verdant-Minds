import os
import sys
import time
import traceback
from typing import Any, Dict, Tuple

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_PACKAGE_ROOT = os.path.join(SCRIPT_DIR, "Verdant Source Codes")
if SRC_PACKAGE_ROOT not in sys.path:
    sys.path.append(SRC_PACKAGE_ROOT)

# ---------------------------------------------------------------------------
# Core imports
# ---------------------------------------------------------------------------
from src.core.system import UnifiedSystem
from src.utils.VerdantMetricsLogger import VerdantMetricsLogger


class VerdantLoopController:
    """Interactive loop controller with timing and error diagnostics."""

    def __init__(self, log_block_errors: bool = True) -> None:
        self.system = UnifiedSystem()
        self.logger = VerdantMetricsLogger()
        self.log_block_errors = log_block_errors

    def run(self) -> None:
        """Run the interactive Verdant loop."""
        print("[🌿] Verdant system initialized. Enter 'exit' to stop.\n")
        while True:
            user_input = input("User Input: ")
            if user_input.lower() == "exit":
                print("[🛑] Exiting Verdant loop.")
                break

            chunk, timings, errors = self.run_cycle(user_input)

            self.logger.log_metrics({
                "timestamp": time.time(),
                "user_input": user_input,
                "timings": timings,
                "errors": errors,
                "result_chunk": repr(chunk),
            })

            print("\n[📊] Result Summary:")
            try:
                reasoning = chunk.get_section_content("reasoning_section") or {}
                ethics = chunk.get_section_content("ethics_king_section") or {}
                memory = chunk.get_section_content("memory_section") or {}

                print(f"     ↪ Confidence Score: {reasoning.get('confidence_score', 'N/A')}")
                print(f"     ↪ Ethical Status  : {ethics.get('evaluation', {}).get('status', 'N/A')}")
                print(
                    "     ↪ Memory Changes  : stored={len(memory.get('stored_concepts', []))}, "
                    f"retrieved={len(memory.get('retrieved_concepts', []))}"
                )
                print(
                    "     ↪ Processing Time : "
                    f"{sum(t for t in timings.values() if isinstance(t, float)):.3f}s"
                )
            except Exception as exc:  # pragma: no cover - diagnostic output
                print(f"     ↪ Summary Error   : {exc}")

            if self.log_block_errors and errors:
                print("[⚠️] Block-level errors:")
                for block, err in errors.items():
                    print(f"     ↪ {block}: {err}")

            print("[🌱] Cycle complete.\n")

        self.system.visualizer.generate_visual_report("verdant_test_output")

    def run_cycle(self, input_text: str) -> Tuple[Any, Dict[str, Any], Dict[str, str]]:
        """Process one full cycle with timing and error capture."""
        errors: Dict[str, str] = {}
        timings: Dict[str, Any] = {}
        chunk = None

        try:
            chunk = self.system.blocks["SensoryInput"].create_chunk_from_input(input_text)
        except Exception as exc:  # pragma: no cover - safety
            errors["SensoryInput"] = str(exc)

        for block_name in self.system.processing_order:
            start = time.time()
            try:
                if chunk is not None:
                    chunk = self.system.blocks[block_name].process_chunk(chunk)

                    if block_name == "InternalCommunication":
                        try:
                            chunk = self.system.three_kings_layer.data_king.oversee_processing(chunk)
                        except Exception as exc:
                            errors["DataKing"] = str(exc)
                    elif block_name == "EthicsValues":
                        try:
                            chunk = self.system.three_kings_layer.ethics_king.oversee_processing(chunk)
                        except Exception as exc:
                            errors["EthicsKing"] = str(exc)
                    elif block_name == "ActionSelection":
                        try:
                            chunk = self.system.three_kings_layer.forefront_king.oversee_processing(chunk)
                        except Exception as exc:
                            errors["ForefrontKing"] = str(exc)
                        try:
                            chunk = self.system.three_kings_layer.oversee_processing(chunk)
                        except Exception as exc:
                            errors["ThreeKingsCoordination"] = str(exc)
            except Exception as exc:  # pragma: no cover - safety
                errors[block_name] = str(exc)
            finally:
                elapsed = round(time.time() - start, 3)
                timings[block_name] = "error" if block_name in errors else elapsed

        if chunk:
            chunk.update_section(
                "processing_metrics_section",
                {
                    "processing_times": timings,
                    "total_processing_time": sum(
                        t for t in timings.values() if isinstance(t, (int, float))
                    ),
                },
            )

            reasoning = chunk.get_section_content("reasoning_section") or {}
            ethics = chunk.get_section_content("ethics_king_section") or {}
            memory = chunk.get_section_content("memory_section") or {}
            cycle_index = len(self.system.visualizer.cycles) + 1
            self.system.visualizer.log_cycle_data(
                {
                    "cycle": cycle_index,
                    "confidence": reasoning.get("confidence_score"),
                    "ethics": ethics.get("evaluation", {}).get("status"),
                    "memory_delta": len(memory.get("retrieved_concepts", [])),
                    "active_blocks": timings,
                    "chunk": chunk.chunk_id,
                }
            )

        return chunk, timings, errors


if __name__ == "__main__":
    controller = VerdantLoopController()
    controller.run()
