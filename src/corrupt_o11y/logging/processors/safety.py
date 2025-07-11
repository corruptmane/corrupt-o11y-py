import functools

from structlog.typing import EventDict, Processor, ProcessorReturnValue, WrappedLogger


def safe_processor(
    processor: Processor,
    name: str | None = None,
    log_errors: bool = True,
) -> Processor:
    """Wrap a processor with error handling to prevent pipeline failures.

    Args:
        processor: The processor to wrap with error handling.
        name: Optional name for the processor (for debugging).
        log_errors: Whether to log processor errors to the event.

    Returns:
        A wrapped processor that handles exceptions gracefully.
    """
    processor_name = name or getattr(processor, "__name__", processor.__class__.__name__)

    @functools.wraps(processor)
    def wrapper(
        logger: WrappedLogger,
        method_name: str,
        event_dict: EventDict,
    ) -> ProcessorReturnValue:
        try:
            return processor(logger, method_name, event_dict)
        except Exception as exc:  # noqa: BLE001
            if log_errors:
                # Add error information to the event without breaking the pipeline
                if "_processor_errors" not in event_dict:
                    event_dict["_processor_errors"] = []

                event_dict["_processor_errors"].append(
                    {
                        "processor": processor_name,
                        "error": str(exc),
                        "error_type": exc.__class__.__name__,
                    }
                )

            # Return the original event_dict to continue processing
            return event_dict

    return wrapper


def make_processor_chain_safe(
    processors: list[Processor],
    log_errors: bool = True,
) -> list[Processor]:
    """Wrap all processors in a chain with error handling.

    Args:
        processors: List of processors to wrap.
        log_errors: Whether to log processor errors to events.

    Returns:
        List of wrapped processors with error handling.
    """
    return [safe_processor(proc, log_errors=log_errors) for proc in processors]
