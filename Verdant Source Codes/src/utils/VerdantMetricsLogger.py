import json
from pathlib import Path
from typing import Any, Dict


class VerdantMetricsLogger:
    """Simple JSONL metrics logger for Verdant runs.

    Metrics are appended to a log file where each line is a JSON object. This
    keeps the logger lightweight and makes logs easy to parse later.
    """

    def __init__(self, log_file: str = "verdant_metrics.log") -> None:
        """Initialize the logger.

        Args:
            log_file: Path to the log file where metrics will be stored.
        """
        self.log_path = Path(log_file)

    def log_metrics(self, metrics: Dict[str, Any]) -> None:
        """Append a metrics dictionary to the log file as a JSON line."""
        with self.log_path.open("a", encoding="utf-8") as fp:
            json.dump(metrics, fp)
            fp.write("\n")
