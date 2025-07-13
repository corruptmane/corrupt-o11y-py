from typing import assert_never, cast

from corrupt_o11y._internal.dependencies import (
    check_opentelemetry,
    check_opentelemetry_grpc_exporter,
    check_opentelemetry_http_exporter,
)

from .config import ExportType, TracingConfig

# Check for OpenTelemetry availability
check_opentelemetry()
from opentelemetry import trace  # noqa: E402
from opentelemetry.propagate import set_global_textmap  # noqa: E402
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource  # noqa: E402
from opentelemetry.sdk.trace import TracerProvider  # noqa: E402
from opentelemetry.sdk.trace.export import (  # noqa: E402
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SpanExporter,
)
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator  # noqa: E402


class TracingError(ValueError):
    """Exception raised for tracing configuration errors."""


def configure_tracing(
    cfg: TracingConfig,
    service_name: str,
    service_version: str,
) -> TracerProvider:
    """Configure OpenTelemetry tracing.

    Args:
        cfg: Tracing configuration.
        service_name: Name of the service.
        service_version: Version of the service.

    Returns:
        Configured tracer provider.

    Raises:
        TracingError: If configuration is invalid.
    """
    resource = Resource.create(
        attributes={
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
        },
    )

    exporter: SpanExporter
    match cfg.export_type:
        case ExportType.STDOUT:
            exporter = ConsoleSpanExporter()
        case ExportType.HTTP:
            check_opentelemetry_http_exporter()

            if not cfg.endpoint:
                msg = "HTTP exporter requires an endpoint"
                raise TracingError(msg)

            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # noqa: PLC0415
                OTLPSpanExporter as OTLPHttpExporter,
            )

            exporter = OTLPHttpExporter(
                endpoint=cfg.endpoint,
                timeout=cfg.timeout,
                headers=cast("dict[str, str]", cfg.headers),
            )
        case ExportType.GRPC:
            check_opentelemetry_grpc_exporter()

            if not cfg.endpoint:
                msg = "GRPC exporter requires an endpoint"
                raise TracingError(msg)

            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # noqa: PLC0415
                OTLPSpanExporter as OTLPGrpcExporter,
            )

            exporter = OTLPGrpcExporter(
                endpoint=cfg.endpoint,
                insecure=cfg.insecure,
                timeout=cfg.timeout,
                headers=cast("dict[str, str]", cfg.headers),
            )
        case _:
            assert_never(cfg.export_type)

    tracer_provider = TracerProvider(resource=resource)
    span_processor = BatchSpanProcessor(exporter)
    tracer_provider.add_span_processor(span_processor)

    trace.set_tracer_provider(tracer_provider)
    set_global_textmap(TraceContextTextMapPropagator())

    return tracer_provider


def get_tracer(name: str, version: str | None = None) -> trace.Tracer:
    """Get an OpenTelemetry tracer.

    Args:
        name: Name of the tracer (usually module name).
        version: Version of the tracer.

    Returns:
        OpenTelemetry tracer instance.
    """
    return trace.get_tracer(name, version)
