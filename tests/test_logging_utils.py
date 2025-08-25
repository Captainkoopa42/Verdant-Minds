import io
import logging
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Verdant Source Codes', 'src'))
from utils.logging_utils import setup_logger


def test_setup_logger_disables_propagation():
    """Logger messages should not propagate to the root logger."""
    stream = io.StringIO()
    root_handler = logging.StreamHandler(stream)
    root_logger = logging.getLogger()
    root_logger.handlers = [root_handler]
    root_logger.setLevel(logging.INFO)

    logger = setup_logger('test_logger')
    # Redirect logger's own handler to avoid writing to stderr during tests
    if logger.handlers:
        logger.handlers[0].stream = io.StringIO()

    logger.info('hello')
    root_handler.flush()

    assert stream.getvalue() == ''
