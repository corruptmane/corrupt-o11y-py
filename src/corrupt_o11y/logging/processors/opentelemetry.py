import structlog
from opentelemetry import trace
from structlog.typing import WrappedLogger


def add_open_telemetry_spans(
    logger: WrappedLogger,  # noqa: ARG001
    method_name: str,  # noqa: ARG001
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    """Add OpenTelemetry span information to log events.

    Args:
        logger: Unused logger parameter.
        method_name: Unused method name parameter.
        event_dict: Event dictionary to process.

    Returns:
        Event dictionary with span information.
    """
    span = trace.get_current_span()
    if not span.is_recording():
        return event_dict

    ctx = span.get_span_context()

    # Only add span information if we have a valid span context
    if ctx.is_valid:
        event_dict["span"] = {
            "span_id": f"{ctx.span_id:016x}",  # 16-char hex (64-bit)
            "trace_id": f"{ctx.trace_id:032x}",  # 32-char hex (128-bit)
        }

    return event_dict
