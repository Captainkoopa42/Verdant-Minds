#!/usr/bin/env python3
import atexit
import signal
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from usm import UnifiedSyntheticMind

STATE_PATH = Path("artifacts/state.json")
SAVE_EVERY = 5


def _extract_response(chunk):
    language = chunk.get_section_content("language_processing_section") or {}
    return language.get("generated_response") or "[no generated_response]"


def main():
    try:
        mind = UnifiedSyntheticMind(config={"initialize_knowledge": False})
    except TypeError:
        mind = UnifiedSyntheticMind()

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

    if STATE_PATH.exists():
        try:
            mind.load_state(str(STATE_PATH))
            print(f"[state] loaded: {STATE_PATH}")
        except Exception as exc:
            print(f"[state] load failed: {exc}")
            print("[state] starting fresh")
    else:
        print("[state] starting fresh")

    def save_now():
        mind.save_state(str(STATE_PATH))
        print(f"[state] saved: {STATE_PATH}")

    atexit.register(save_now)

    def handle_signal(_signum, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    turn = 0
    print("Verdant REPL ready. Type 'exit' or Ctrl+C to quit.")
    while True:
        try:
            text = input("verdant> ").strip()
        except EOFError:
            print()
            break

        if not text:
            continue
        if text.lower() in {"exit", "quit"}:
            break

        chunk = mind.process_input(text)
        print(_extract_response(chunk))

        turn += 1
        if turn % SAVE_EVERY == 0:
            save_now()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
