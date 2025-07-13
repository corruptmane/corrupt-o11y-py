import importlib
from typing import NoReturn


class MissingDependencyError(ImportError):
    """Raised when a required optional dependency is missing."""


def require_dependency(module_name: str, feature: str, extra: str) -> None:
    """Check if a dependency is available and raise helpful error if not.

    Args:
        module_name: Name of the module to import.
        feature: Human-readable feature name.
        extra: Name of the optional dependency group.

    Raises:
        MissingDependencyError: If the dependency is not available.
    """
    try:
        importlib.import_module(module_name)
    except ImportError as exc:
        _raise_missing_dependency(module_name, feature, extra, exc)


def _raise_missing_dependency(
    module_name: str, feature: str, extra: str, error: Exception
) -> NoReturn:
    """Raise a helpful error message for missing dependencies."""
    msg = (
        f"Missing dependency '{module_name}' required for {feature}. "
        f"Install with: pip install corrupt-o11y[{extra}]"
    )
    raise MissingDependencyError(msg) from error


def check_structlog() -> None:
    """Check if structlog is available for logging features."""
    require_dependency("structlog", "structured logging", "logging")


def check_opentelemetry() -> None:
    """Check if OpenTelemetry is available for tracing features."""
    require_dependency("opentelemetry.sdk", "tracing", "tracing")


def check_opentelemetry_grpc_exporter() -> None:
    """Check if OpenTelemetry gRPC exporter is available."""
    require_dependency("opentelemetry.exporter.otlp.proto.grpc", "tracing", "tracing")


def check_opentelemetry_http_exporter() -> None:
    """Check if OpenTelemetry HTTP exporter is available."""
    require_dependency("opentelemetry.exporter.otlp.proto.http", "tracing", "tracing")


def check_opentelemetry_exporters() -> None:
    """Check if OpenTelemetry exporters are available."""
    try:
        importlib.import_module("opentelemetry.exporter.otlp.proto.grpc")
    except ImportError:
        try:
            importlib.import_module("opentelemetry.exporter.otlp.proto.http")
        except ImportError as exc:
            _raise_missing_dependency("opentelemetry exporters", "OTLP export", "exporters", exc)


def check_aiohttp() -> None:
    """Check if aiohttp is available for operational server."""
    require_dependency("aiohttp", "HTTP server", "server")
