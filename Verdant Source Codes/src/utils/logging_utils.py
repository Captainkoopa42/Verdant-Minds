"""Simple logging utilities for the Verdant project."""
import logging


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Create and configure a ``logging.Logger`` instance.

    Args:
        name: Name of the logger to create.
        level: Logging level, defaulting to ``logging.INFO``.

    Returns:
        Configured ``Logger`` instance.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger
