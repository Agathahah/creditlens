import uuid

import structlog

from src.common.logging import (
    configure_logging,
    get_request_id,
    set_request_id,
)


def test_request_id_tracing() -> None:
    test_id = str(uuid.uuid4())
    set_request_id(test_id)
    assert get_request_id() == test_id


def test_logger_setup() -> None:
    configure_logging()
    logger = structlog.get_logger("test_channel")
    assert logger is not None
