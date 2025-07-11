from typing import assert_never, cast

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as OTLPGrpcExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as OTLPHttpExporter,
)
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from .config import ExportType, TracingConfig


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

    exporter: ConsoleSpanExporter | OTLPHttpExporter | OTLPGrpcExporter
    match cfg.export_type:
        case ExportType.STDOUT:
            exporter = ConsoleSpanExporter()
        case ExportType.HTTP:
            if not cfg.endpoint:
                msg = "HTTP exporter requires an endpoint"
                raise TracingError(msg)

            exporter = OTLPHttpExporter(
                endpoint=cfg.endpoint,
                timeout=cfg.timeout,
                headers=cast("dict[str, str]", cfg.headers),
            )
        case ExportType.GRPC:
            if not cfg.endpoint:
                msg = "GRPC exporter requires an endpoint"
                raise TracingError(msg)

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
