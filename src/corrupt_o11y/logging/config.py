import logging
import os
from dataclasses import dataclass
from typing import Self

from corrupt_o11y._internal import env_bool


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
        integrate_tracing: Whether to include OpenTelemetry tracing information in logs.
        colors: Whether to enable colors in console output (ignored for JSON output).
        exception_max_frames: Maximum number of frames to include in structured traceback.
        exception_preserve_traceback: Whether to preserve original traceback string.
        exception_extract_location: Whether to extract specific error location info.
        exception_skip_library_frames: Whether to skip library/framework
        frames in root cause detection.
    """

    level: int
    as_json: bool
    integrate_tracing: bool
    colors: bool = True
    exception_max_frames: int = 20
    exception_preserve_traceback: bool = True
    exception_extract_location: bool = True
    exception_skip_library_frames: bool = True

    @classmethod
    def from_env(cls) -> Self:
        """Create configuration from environment variables.

        Environment variables:
            LOG_LEVEL: Log level (default: INFO).
            LOG_AS_JSON: Output logs as JSON (default: false).
            LOG_TRACING: Include tracing information (default: false).
            LOG_COLORS: Enable colors in console output (default: true).
            LOG_EXCEPTION_MAX_FRAMES: Maximum frames in traceback (default: 20).
            LOG_EXCEPTION_PRESERVE_TRACEBACK: Preserve original traceback (default: true).
            LOG_EXCEPTION_EXTRACT_LOCATION: Extract error location info (default: true).
            LOG_EXCEPTION_SKIP_LIBRARY_FRAMES: Skip library frames in root cause (default: true).

        Returns:
            LoggingConfig instance.

        Raises:
            ValueError: If any environment variable has an invalid value.
        """
        try:
            level = _str_level_to_int(os.environ.get("LOG_LEVEL", "INFO"))
        except ValueError as exc:
            msg = f"Invalid LOG_LEVEL: {exc}"
            raise ValueError(msg) from exc

        max_frames_str = os.environ.get("LOG_EXCEPTION_MAX_FRAMES", "20")
        try:
            max_frames = int(max_frames_str)
        except ValueError as exc:
            msg = f"Invalid LOG_EXCEPTION_MAX_FRAMES '{max_frames_str}': {exc}"
            raise ValueError(msg) from exc
        else:
            if max_frames < 1:
                msg = "exception_max_frames must be at least 1"
                raise ValueError(msg)

        return cls(
            level=level,
            as_json=env_bool("LOG_AS_JSON", "false"),
            integrate_tracing=env_bool("LOG_TRACING", "false"),
            colors=env_bool("LOG_COLORS", "true"),
            exception_max_frames=max_frames,
            exception_preserve_traceback=env_bool("LOG_EXCEPTION_PRESERVE_TRACEBACK", "true"),
            exception_extract_location=env_bool("LOG_EXCEPTION_EXTRACT_LOCATION", "true"),
            exception_skip_library_frames=env_bool("LOG_EXCEPTION_SKIP_LIBRARY_FRAMES", "true"),
        )
