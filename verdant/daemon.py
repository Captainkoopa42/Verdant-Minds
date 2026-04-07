from __future__ import annotations

import logging
import signal
import time
from pathlib import Path

from verdant.system import VerdantSystem


class VerdantDaemon:
    def __init__(
        self,
        system: VerdantSystem,
        *,
        interval: float = 0.5,
        checkpoint_dir: str | None = None,
        checkpoint_interval: float = 30.0,
        log_level: str = "INFO",
    ) -> None:
        self.system = system
        self.interval = interval
        self.checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else None
        self.checkpoint_interval = max(0.0, float(checkpoint_interval))
        self.running = True
        logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO))

    def _stop(self, signum, _frame) -> None:  # type: ignore[no-untyped-def]
        logging.info("Received signal %s; shutting down Verdant daemon.", signum)
        self.running = False

    def run(self) -> None:
        signal.signal(signal.SIGINT, self._stop)
        signal.signal(signal.SIGTERM, self._stop)

        if self.checkpoint_dir:
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        last_checkpoint_at = time.monotonic()

        while self.running:
            self.system.run_cycle()
            if self.checkpoint_dir and self.checkpoint_interval > 0:
                now = time.monotonic()
                elapsed = now - last_checkpoint_at
                if elapsed >= self.checkpoint_interval:
                    checkpoint_path = self.checkpoint_dir / f"checkpoint_{int(time.time())}.json"
                    self.system.save_state(str(checkpoint_path))
                    last_checkpoint_at = now
            elif self.checkpoint_dir:
                checkpoint_path = self.checkpoint_dir / f"checkpoint_{int(time.time())}.json"
                self.system.save_state(str(checkpoint_path))
            time.sleep(max(0.0, self.interval))
