import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Self

from corrupt_o11y._internal import env_bool


class ExportType(str, Enum):
    """Supported OpenTelemetry exporter types."""

    STDOUT = "stdout"
    HTTP = "http"
    GRPC = "grpc"


@dataclass
class TracingConfig:
    """Configuration for OpenTelemetry tracing.

    Attributes:
        export_type: Type of exporter.
        endpoint: Endpoint URL for remote exporters.
        insecure: Whether to use insecure connections (default: False for production safety).
        timeout: Timeout in seconds for exporter requests.
        headers: Additional headers for HTTP/GRPC exporters.
    """

    export_type: ExportType
    endpoint: str
    insecure: bool = False
    timeout: int = 30
    headers: Mapping[str, str] | None = None

    @classmethod
    def from_env(cls, headers: Mapping[str, str] | None = None) -> Self:
        """Create configuration from environment variables.

        Args:
            headers: Additional headers for HTTP/GRPC exporters.

        Environment variables:
            TRACING_EXPORTER_TYPE: Type of exporter (default: stdout).
            TRACING_EXPORTER_ENDPOINT: Endpoint URL for remote exporters.
            TRACING_INSECURE: Whether to use insecure connections (default: false).
            TRACING_TIMEOUT: Timeout in seconds for exporter requests (default: 30).

        Returns:
            TracingConfig instance.

        Raises:
            ValueError: If any environment variable has an invalid value.
        """
        export_type_str = os.environ.get("TRACING_EXPORTER_TYPE", "stdout")
        try:
            export_type = ExportType(export_type_str)
        except ValueError as e:
            msg = f"Invalid TRACING_EXPORTER_TYPE '{export_type_str}': {e}"
            raise ValueError(msg) from e

        timeout_str = os.environ.get("TRACING_TIMEOUT", "30")
        try:
            timeout = int(timeout_str)
        except ValueError as e:
            msg = f"Invalid TRACING_TIMEOUT '{timeout_str}': {e}"
            raise ValueError(msg) from e
        else:
            if timeout < 1:
                msg = "timeout must be at least 1 second"
                raise ValueError(msg)

        return cls(
            export_type=export_type,
            endpoint=os.environ.get("TRACING_EXPORTER_ENDPOINT", ""),
            insecure=env_bool("TRACING_INSECURE", "false"),
            timeout=timeout,
            headers=headers,
        )
