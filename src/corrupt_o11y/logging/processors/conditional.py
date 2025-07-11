import re
from collections.abc import Callable

from structlog.typing import EventDict, Processor, ProcessorReturnValue, WrappedLogger


class ConditionalProcessor:
    """Apply a processor only when certain conditions are met.

    This meta-processor allows you to conditionally apply other processors
    based on the content of the log event, enabling flexible processing chains.
    """

    def __init__(
        self,
        condition: Callable[[EventDict], bool],
        processor: Processor,
        else_processor: Processor | None = None,
    ) -> None:
        """Initialize the conditional processor.

        Args:
            condition: Function that takes an EventDict and returns bool.
            processor: Processor to apply when condition is True.
            else_processor: Optional processor to apply when condition is False.
        """
        self.condition = condition
        self.processor = processor
        self.else_processor = else_processor

    def __call__(
        self,
        logger: WrappedLogger,
        method_name: str,
        event_dict: EventDict,
    ) -> ProcessorReturnValue:
        """Process the event conditionally."""
        if self.condition(event_dict):
            return self.processor(logger, method_name, event_dict)
        if self.else_processor:
            return self.else_processor(logger, method_name, event_dict)
        return event_dict


# Common condition functions for convenience
def is_level(level: str) -> Callable[[EventDict], bool]:
    """Create a condition that checks for a specific log level."""

    def condition(event_dict: EventDict) -> bool:
        return event_dict.get("level") == level

    return condition


def is_error_or_critical() -> Callable[[EventDict], bool]:
    """Create a condition that checks for error or critical log levels."""

    def condition(event_dict: EventDict) -> bool:
        return event_dict.get("level") in ("error", "critical")

    return condition


def has_field(field_name: str) -> Callable[[EventDict], bool]:
    """Create a condition that checks if a specific field exists."""

    def condition(event_dict: EventDict) -> bool:
        return field_name in event_dict

    return condition


def has_exception() -> Callable[[EventDict], bool]:
    """Create a condition that checks if the event contains exception information."""

    def condition(event_dict: EventDict) -> bool:
        return any(
            key in event_dict for key in ["exception_type", "exc_info", "structured_traceback"]
        )

    return condition


def field_contains(field_name: str, substring: str) -> Callable[[EventDict], bool]:
    """Create a condition that checks if a field contains a substring."""

    def condition(event_dict: EventDict) -> bool:
        value = event_dict.get(field_name)
        if isinstance(value, str):
            return substring in value
        return False

    return condition


def field_matches_pattern(field_name: str, pattern: str) -> Callable[[EventDict], bool]:
    """Create a condition that checks if a field matches a regex pattern."""
    compiled_pattern = re.compile(pattern)

    def condition(event_dict: EventDict) -> bool:
        value = event_dict.get(field_name)
        if isinstance(value, str):
            return bool(compiled_pattern.search(value))
        return False

    return condition
