import os
from dataclasses import dataclass
from enum import Enum
from typing import Self


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
    """

    export_type: ExportType
    endpoint: str

    @classmethod
    def from_env(cls) -> Self:
        """Create configuration from environment variables.

        Environment variables:
            TRACING_EXPORTER_TYPE: Type of exporter (default: stdout).
            TRACING_EXPORTER_ENDPOINT: Endpoint URL for remote exporters.

        Returns:
            TracingConfig instance.
        """
        export_type_str = os.environ.get("TRACING_EXPORTER_TYPE", "stdout")
        try:
            export_type = ExportType(export_type_str)
        except ValueError:
            msg = f"Invalid export type: {export_type_str}"
            raise ValueError(msg) from None

        return cls(
            export_type=export_type,
            endpoint=os.environ.get("TRACING_EXPORTER_ENDPOINT", ""),
        )
