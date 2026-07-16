import uuid
import structlog
from src.common.logging import configure_logging, set_request_id, get_request_id, add_request_id_processor

def test_request_id_tracing():
    test_id = str(uuid.uuid4())
    set_request_id(test_id)
    assert get_request_id() == test_id

def test_logger_setup():
    configure_logging()
    logger = structlog.get_logger("test_channel")
    assert logger is not None
