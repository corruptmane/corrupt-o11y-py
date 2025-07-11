# corrupt o11y

[![CI](https://github.com/corruptmane/corrupt-o11y-py/actions/workflows/ci.yml/badge.svg)](https://github.com/corruptmane/corrupt-o11y-py/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/mykyta/corrupt-o11y-py/branch/main/graph/badge.svg)](https://codecov.io/gh/mykyta/corrupt-o11y-py)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

A comprehensive observability library for Python applications with logging, metrics, and tracing.

## Features

- **Structured Logging** - JSON-formatted logs with OpenTelemetry trace correlation
- **Flexible Processor Chain** - PII redaction, field filtering, exception enhancement, conditional processing
- **Prometheus Metrics** - Built-in collectors for GC, platform, and process metrics with custom metric support
- **OpenTelemetry Tracing** - Multiple exporters (OTLP HTTP/gRPC, console)
- **Operational Endpoints** - Health checks, metrics, and service info HTTP server
- **Service Metadata** - Centralized service information management
- **Type Safe** - Strict type checking with mypy
- **Environment-Based Configuration** - All components configurable via environment variables

## Quick Start

```python
from corrupt_o11y import logging, metrics, tracing
from corrupt_o11y.operational import Status, OperationalServerConfig, OperationalServer
from corrupt_o11y.metadata import ServiceInfo

async def main():
    # Setup service information
    service_info = ServiceInfo.from_env()

    # Configure logging
    log_config = logging.LoggingConfig.from_env()
    logging.configure_logging(log_config)
    logger = logging.get_logger(__name__)

    # Set up metrics
    metrics_collector = metrics.MetricsCollector()
    metrics_collector.create_service_info_metric_from_service_info(service_info)

    # Configure tracing
    trace_config = tracing.TracingConfig.from_env()
    tracing.configure_tracing(trace_config, service_info.name, service_info.version)
    tracer = tracing.get_tracer(__name__)

    # Set up operational server
    status = Status()
    op_config = OperationalServerConfig.from_env()
    server = OperationalServer(op_config, service_info.asdict(), status, metrics_collector)
    await server.start()
    status.is_ready = True

    # Use observability features
    logger.info("Service started", extra={"port": 8080})

    with tracer.start_as_current_span("process_request"):
        # Your business logic here
        logger.info("Processing request")
```

## Configuration

All components are configured via environment variables:

### Logging
- `LOG_LEVEL` - Log level (default: INFO)
- `LOG_AS_JSON` - Output JSON format (default: false)
- `LOG_TRACING` - Include trace information (default: false)

### Tracing
- `TRACING_EXPORTER_TYPE` - Exporter type: stdout, http, grpc (default: stdout)
- `TRACING_EXPORTER_ENDPOINT` - OTLP endpoint URL (required for http/grpc)
- `TRACING_INSECURE` - Use insecure connection (default: false)
- `TRACING_TIMEOUT` - Request timeout in seconds (default: 30)

### Metrics
- `METRICS_ENABLE_GC` - Enable GC metrics collector (default: true)
- `METRICS_ENABLE_PLATFORM` - Enable platform metrics collector (default: true)
- `METRICS_ENABLE_PROCESS` - Enable process metrics collector (default: true)
- `METRICS_PREFIX` - Prefix for custom metrics (default: empty)

### Operational Server
- `OPERATIONAL_HOST` - Bind address (default: 0.0.0.0)
- `OPERATIONAL_PORT` - Port number (default: 42069)

### Service Metadata
- `SERVICE_NAME` - Service name (default: unknown-dev)
- `SERVICE_VERSION` - Service version (default: unknown-dev)
- `INSTANCE_ID` - Instance identifier (default: unknown-dev)
- `COMMIT_SHA` - Git commit SHA (default: unknown-dev)
- `BUILD_TIME` - Build timestamp (default: unknown-dev)

## Endpoints

The operational server provides:

- `GET /health` - Liveness check (200 if alive)
- `GET /ready` - Readiness check (200 if ready)
- `GET /metrics` - Prometheus metrics
- `GET /info` - Service information JSON

## Service Info Metric

Following Prometheus best practices, service metadata is exposed as an info metric:

```prometheus
service_info{service="my-service", version="1.2.3", instance="pod-123", commit="abc123"} 1
```

This provides rich metadata without increasing cardinality of other metrics.

## Advanced Usage

### Logging Processors

The library supports flexible processor chains for log processing:

```python
from corrupt_o11y.logging import LoggingCollector
from corrupt_o11y.logging.processors import (
    PIIRedactionProcessor,
    FieldFilterProcessor,
    EnhancedExceptionProcessor,
    ConditionalProcessor,
    is_level
)

collector = LoggingCollector()
collector.preprocessing().extend([
    PIIRedactionProcessor(),  # Redact PII (emails, phones, etc.)
    FieldFilterProcessor(blocked_fields=["password", "token"]),  # Filter sensitive fields
    ConditionalProcessor(
        condition=is_level("error"),
        processor=EnhancedExceptionProcessor()  # Enhanced exception info for errors
    )
])

logging.configure_logging(config, collector)
```

### Custom Metrics

```python
from prometheus_client import Counter, Histogram

# Create custom metrics
request_counter = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=None
)

# Register with collector
metrics_collector.register("http_requests", request_counter)

# Use metrics
request_counter.labels(method="GET", endpoint="/api/users", status="200").inc()
```

## Installation

```bash
# With uv (recommended)
uv add corrupt-o11y
```

```bash
# With pip
pip install corrupt-o11y
```

## Development

For contributors (using [uv](https://docs.astral.sh/uv/) as recommended package manager):

```bash
# Install with development dependencies
uv sync --dev

# Install pre-commit hooks
uv run pre-commit install

# Run linting and type checking
uv run ruff check
uv run ruff format --check
uv run mypy

# Run tests with coverage
uv run pytest tests/ --cov=src --cov-report=term-missing --cov-branch

# Or just commit - pre-commit will run all checks automatically
```

With pip:
```bash
pip install -e ".[dev]"
pre-commit install
```

## Requirements

- Python 3.11+
- OpenTelemetry
- Prometheus Client
- structlog
- aiohttp

## License

MIT
