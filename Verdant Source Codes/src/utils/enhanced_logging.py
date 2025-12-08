"""
Enhanced Logging System for Verdant-Minds

This module provides comprehensive logging with:
- Proper log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Structured logging (JSON format)
- Performance metrics integration
- Contextual information
- Log rotation
- Colorized console output

Usage:
    >>> from src.utils.enhanced_logging import get_logger
    >>> logger = get_logger(__name__)
    >>> logger.info("Processing chunk", extra={"chunk_id": "123", "block": "PatternRecognition"})
"""

import logging
import logging.handlers
import json
import sys
import time
from typing import Any, Dict, Optional
from pathlib import Path
from datetime import datetime
import traceback

# Color codes for terminal output
class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"


class ColorizedFormatter(logging.Formatter):
    """Formatter that adds colors to log output."""

    LEVEL_COLORS = {
        logging.DEBUG: Colors.GRAY,
        logging.INFO: Colors.BLUE,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.RED + Colors.BOLD,
    }

    def __init__(self, fmt: str, colorize: bool = True):
        super().__init__(fmt)
        self.colorize = colorize

    def format(self, record: logging.LogRecord) -> str:
        if self.colorize and sys.stdout.isatty():
            # Colorize level name
            levelname = record.levelname
            if record.levelno in self.LEVEL_COLORS:
                color = self.LEVEL_COLORS[record.levelno]
                record.levelname = f"{color}{levelname}{Colors.RESET}"

            # Colorize message for errors
            if record.levelno >= logging.ERROR:
                record.msg = f"{Colors.RED}{record.msg}{Colors.RESET}"

        return super().format(record)


class StructuredFormatter(logging.Formatter):
    """Formatter that outputs structured JSON logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }

        return json.dumps(log_data)


class PerformanceLogger:
    """Logger for performance metrics."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.metrics: Dict[str, list] = {}

    def log_timing(self, operation: str, duration_ms: float, **metadata):
        """
        Log timing information.

        Args:
            operation: Name of operation
            duration_ms: Duration in milliseconds
            **metadata: Additional metadata
        """
        if operation not in self.metrics:
            self.metrics[operation] = []

        self.metrics[operation].append(duration_ms)

        self.logger.debug(
            f"Performance: {operation} took {duration_ms:.3f}ms",
            extra={
                "extra_data": {
                    "metric_type": "timing",
                    "operation": operation,
                    "duration_ms": duration_ms,
                    **metadata
                }
            }
        )

    def log_memory(self, operation: str, memory_mb: float, **metadata):
        """
        Log memory usage.

        Args:
            operation: Name of operation
            memory_mb: Memory in megabytes
            **metadata: Additional metadata
        """
        self.logger.debug(
            f"Memory: {operation} used {memory_mb:.2f}MB",
            extra={
                "extra_data": {
                    "metric_type": "memory",
                    "operation": operation,
                    "memory_mb": memory_mb,
                    **metadata
                }
            }
        )

    def log_throughput(self, operation: str, items_per_sec: float, **metadata):
        """
        Log throughput metrics.

        Args:
            operation: Name of operation
            items_per_sec: Items processed per second
            **metadata: Additional metadata
        """
        self.logger.info(
            f"Throughput: {operation} = {items_per_sec:.2f} items/sec",
            extra={
                "extra_data": {
                    "metric_type": "throughput",
                    "operation": operation,
                    "items_per_sec": items_per_sec,
                    **metadata
                }
            }
        )

    def get_stats(self, operation: str) -> Optional[Dict[str, float]]:
        """Get statistics for an operation."""
        if operation not in self.metrics or not self.metrics[operation]:
            return None

        import statistics
        values = self.metrics[operation]

        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0,
            "min": min(values),
            "max": max(values),
        }


class EnhancedLogger(logging.LoggerAdapter):
    """
    Enhanced logger with additional functionality.
    """

    def __init__(self, logger: logging.Logger, extra: Optional[Dict] = None):
        super().__init__(logger, extra or {})
        self.performance = PerformanceLogger(logger)

    def process(self, msg: str, kwargs: Dict) -> tuple:
        """Process log message and kwargs."""
        # Add extra data to record
        if "extra" in kwargs:
            extra_data = kwargs["extra"]
            if "extra_data" not in extra_data:
                extra_data["extra_data"] = {}
            extra_data["extra_data"].update(self.extra)
        else:
            kwargs["extra"] = {"extra_data": self.extra.copy()}

        return msg, kwargs

    def log_chunk_processing(
        self,
        chunk_id: str,
        block_name: str,
        status: str = "start",
        **metadata
    ):
        """
        Log chunk processing event.

        Args:
            chunk_id: Chunk identifier
            block_name: Name of processing block
            status: Processing status (start, complete, error)
            **metadata: Additional metadata
        """
        self.info(
            f"Chunk {chunk_id} {status} in {block_name}",
            extra={
                "extra_data": {
                    "event_type": "chunk_processing",
                    "chunk_id": chunk_id,
                    "block_name": block_name,
                    "status": status,
                    **metadata
                }
            }
        )

    def log_block_output(
        self,
        block_name: str,
        output_summary: Dict[str, Any],
        **metadata
    ):
        """
        Log block processing output.

        Args:
            block_name: Name of block
            output_summary: Summary of output
            **metadata: Additional metadata
        """
        self.debug(
            f"Block output: {block_name}",
            extra={
                "extra_data": {
                    "event_type": "block_output",
                    "block_name": block_name,
                    "output_summary": output_summary,
                    **metadata
                }
            }
        )


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    structured_log_file: Optional[str] = None,
    console_output: bool = True,
    colorize: bool = True,
    max_bytes: int = 100 * 1024 * 1024,  # 100MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up enhanced logging system.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to regular log file (optional)
        structured_log_file: Path to structured JSON log file (optional)
        console_output: Whether to output to console
        colorize: Whether to colorize console output
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep

    Returns:
        Root logger
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    root_logger.handlers = []

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))

        console_format = (
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        )
        console_formatter = ColorizedFormatter(console_format, colorize=colorize)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # File handler (regular logs)
    if log_file:
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(logging.DEBUG)

        file_format = (
            "%(asctime)s | %(levelname)-8s | %(name)-30s | "
            "%(funcName)-20s | %(message)s"
        )
        file_formatter = logging.Formatter(file_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Structured log handler (JSON)
    if structured_log_file:
        # Create log directory if it doesn't exist
        log_path = Path(structured_log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        structured_handler = logging.handlers.RotatingFileHandler(
            structured_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        structured_handler.setLevel(logging.DEBUG)
        structured_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(structured_handler)

    return root_logger


def get_logger(
    name: str,
    context: Optional[Dict[str, Any]] = None
) -> EnhancedLogger:
    """
    Get an enhanced logger instance.

    Args:
        name: Logger name (usually __name__)
        context: Optional context to include in all logs

    Returns:
        EnhancedLogger instance

    Example:
        >>> logger = get_logger(__name__, context={"component": "PatternRecognition"})
        >>> logger.info("Processing started")
    """
    base_logger = logging.getLogger(name)
    return EnhancedLogger(base_logger, extra=context or {})


class TimingContext:
    """Context manager for timing operations."""

    def __init__(self, logger: EnhancedLogger, operation: str, **metadata):
        self.logger = logger
        self.operation = operation
        self.metadata = metadata
        self.start_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        self.logger.debug(f"Starting: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.perf_counter() - self.start_time) * 1000

        if exc_type is not None:
            self.logger.error(
                f"Failed: {self.operation} ({duration_ms:.3f}ms)",
                exc_info=(exc_type, exc_val, exc_tb)
            )
        else:
            self.logger.performance.log_timing(
                self.operation,
                duration_ms,
                **self.metadata
            )


# Example usage
if __name__ == "__main__":
    # Set up logging
    setup_logging(
        level="DEBUG",
        log_file="logs/test.log",
        structured_log_file="logs/test_structured.jsonl",
        colorize=True
    )

    # Get logger
    logger = get_logger(__name__, context={"component": "test"})

    # Test logging
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    # Test performance logging
    logger.performance.log_timing("test_operation", 123.45, chunk_id="test_123")

    # Test timing context
    with TimingContext(logger, "expensive_operation", metadata={"type": "test"}):
        time.sleep(0.1)

    print("\nLogs written to logs/test.log and logs/test_structured.jsonl")
