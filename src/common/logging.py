import logging
import sys
import uuid
from contextvars import ContextVar
import structlog
from src.common.config import get_settings

# Context variable for request tracing
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

def get_request_id() -> str:
    """Retrieve the current thread request identifier for logs tracing."""
    return request_id_var.get()

def set_request_id(request_id: str) -> None:
    """Set the current thread request identifier."""
    request_id_var.set(request_id)

def add_request_id_processor(logger: structlog.types.WrappedLogger, method_name: str, event_dict: dict) -> dict:
    """Processor to dynamically append the request_id context variable to every logged record."""
    req_id = get_request_id()
    if req_id:
        event_dict["request_id"] = req_id
    return event_dict

def configure_logging() -> None:
    """Configure structured console logging depending on environment."""
    settings = get_settings()
    is_production = settings.ENV == "production"

    shared_processors = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        add_request_id_processor,
    ]

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = (
        structlog.processors.JSONRenderer()
        if is_production
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    stdlib_formatter = structlog.stdlib.ProcessorFormatter(
        processors=shared_processors + [formatter],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(stdlib_formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO if is_production else logging.DEBUG)

    # Silence chatty frameworks
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
