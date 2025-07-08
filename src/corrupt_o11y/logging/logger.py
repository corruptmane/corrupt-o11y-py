import logging
from typing import Any
from uuid import UUID

import orjson
import structlog
from opentelemetry import trace

from .config import LoggingConfig


def _mute_loggers() -> None:
    """Mute noisy third-party loggers."""
    # Mute Uvicorn loggers
    logging.getLogger("uvicorn.access").disabled = True
    for _log in ("uvicorn", "uvicorn.errors"):
        logging.getLogger(_log).handlers.clear()
        logging.getLogger(_log).propagate = True


def drop_color_message_key(  # type: ignore[explicit-any]
    _: Any,  # noqa: ANN401
    __: Any,  # noqa: ANN401
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    """Drop color_message key from event dict.

    Uvicorn logs the message a second time in the extra `color_message`, but we don't
    need it. This processor drops the key from the event dict if it exists.

    Args:
        _: Unused logger parameter.
        __: Unused method name parameter.
        event_dict: Event dictionary to process.

    Returns:
        Event dictionary without color_message key.
    """
    event_dict.pop("color_message", None)
    return event_dict


def dict_tracebacks() -> structlog.processors.ExceptionRenderer:
    """Create exception renderer that outputs tracebacks as dictionaries.

    Returns:
        Exception renderer for structured traceback output.
    """
    return structlog.processors.ExceptionRenderer(
        structlog.tracebacks.ExceptionDictTransformer(),
    )


def additionally_serialize(obj: Any) -> Any:  # type: ignore[explicit-any] # noqa: ANN401
    """Serialize additional types for JSON output.

    Args:
        obj: Object to serialize.

    Returns:
        Serialized object.

    Raises:
        TypeError: If object type is not JSON serializable.
    """
    if isinstance(obj, UUID):
        return str(obj)
    msg = f"TypeError: Type is not JSON serializable: {type(obj)}"
    raise TypeError(msg)


def serialize_to_json(data: Any, _: Any) -> bytes:  # type: ignore[explicit-any] # noqa: ANN401
    """Serialize data to JSON bytes.

    Args:
        data: Data to serialize.
        _: Unused parameter.

    Returns:
        JSON bytes.
    """
    return orjson.dumps(data, default=additionally_serialize)


def add_open_telemetry_spans(  # type: ignore[explicit-any]
    _: Any,  # noqa: ANN401
    __: Any,  # noqa: ANN401
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    """Add OpenTelemetry span information to log events.

    Args:
        _: Unused logger parameter.
        __: Unused method name parameter.
        event_dict: Event dictionary to process.

    Returns:
        Event dictionary with span information.
    """
    span = trace.get_current_span()
    if not span.is_recording():
        event_dict["span"] = None
        return event_dict

    ctx = span.get_span_context()
    parent = getattr(span, "parent", None)

    event_dict["span"] = {
        "span_id": hex(ctx.span_id),
        "trace_id": hex(ctx.trace_id),
        "parent_span_id": None if not parent else hex(parent.span_id),
    }

    return event_dict


def configure_logging(log_config: LoggingConfig) -> None:
    """Configure structured logging with the given configuration.

    Args:
        log_config: Logging configuration.
    """
    _mute_loggers()

    common_processors: list[Any] = [  # type: ignore[explicit-any]
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.ExtraAdder(),
        drop_color_message_key,
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.contextvars.merge_contextvars,
        structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
                structlog.processors.CallsiteParameter.MODULE,
            ],
        ),
    ]
    if log_config.tracing:
        common_processors.append(add_open_telemetry_spans)

    processor: structlog.processors.JSONRenderer | structlog.dev.ConsoleRenderer
    if log_config.as_json:
        common_processors.append(dict_tracebacks())
        processor = structlog.processors.JSONRenderer(serializer=serialize_to_json)
    else:
        processor = structlog.dev.ConsoleRenderer(colors=True)

    structlog_processors: list[Any] = [  # type: ignore[explicit-any]
        structlog.processors.StackInfoRenderer(),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]

    logging_processors = (
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        processor,
    )

    handler = logging.StreamHandler()
    handler.set_name("default")
    handler.setLevel(log_config.level)
    console_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=common_processors,
        processors=logging_processors,
    )
    handler.setFormatter(console_formatter)

    logging.basicConfig(handlers=[handler], level=log_config.level)

    structlog.configure(
        processors=common_processors + structlog_processors,
        logger_factory=structlog.BytesLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(log_config.level),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> Any:  # type: ignore[explicit-any] # noqa: ANN401
    """Get a structured logger instance.

    Args:
        name: Logger name. If None, uses the calling module's name.

    Returns:
        Structured logger instance.
    """
    return structlog.get_logger(name)
