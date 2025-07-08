import logging
import os
from dataclasses import dataclass
from typing import Self


def _str_level_to_int(level: str) -> int:
    """Convert string log level to integer.

    Args:
        level: Log level as string (debug, info, warning, error, critical).

    Returns:
        Integer log level.

    Raises:
        ValueError: If the log level is unknown.
    """
    match level.lower():
        case "debug":
            return logging.DEBUG
        case "info":
            return logging.INFO
        case "warning":
            return logging.WARNING
        case "error":
            return logging.ERROR
        case "critical":
            return logging.CRITICAL
        case _:
            msg = f"Unknown log level: {level}"
            raise ValueError(msg)


@dataclass
class LoggingConfig:
    """Configuration for structured logging.

    Attributes:
        level: Logging level as integer.
        as_json: Whether to output logs in JSON format.
        tracing: Whether to include OpenTelemetry tracing information in logs.
    """

    level: int
    as_json: bool
    tracing: bool

    @classmethod
    def from_env(cls) -> Self:
        """Create configuration from environment variables.

        Environment variables:
            LOG_LEVEL: Log level (default: INFO).
            LOG_AS_JSON: Output logs as JSON (default: false).
            LOG_TRACING: Include tracing information (default: false).

        Returns:
            LoggingConfig instance.
        """
        return cls(
            level=_str_level_to_int(os.environ.get("LOG_LEVEL", "INFO")),
            as_json=os.environ.get("LOG_AS_JSON", "false").lower().startswith("t"),
            tracing=os.environ.get("LOG_TRACING", "false").lower().startswith("t"),
        )
