# Advanced Usage

This guide covers advanced features and patterns for using corrupt-o11y.

## Logging Processors

The logging system supports a flexible processor chain architecture. Processors can transform, filter, or enhance log events.

### Built-in Processors

#### PII Redaction
```python
from corrupt_o11y.logging.processors import PIIRedactionProcessor

processor = PIIRedactionProcessor()
# Automatically redacts emails, phone numbers, SSNs, and credit card numbers
```

#### Field Filtering
```python
from corrupt_o11y.logging.processors import FieldFilterProcessor

# Only allow specific fields
processor = FieldFilterProcessor(allowed_fields=["message", "level", "timestamp"])

# Block sensitive fields
processor = FieldFilterProcessor(blocked_fields=["password", "token"])
```

#### Nested Field Filtering
```python
from corrupt_o11y.logging.processors import NestedFieldFilterProcessor

# Filter nested structures
processor = NestedFieldFilterProcessor(
    allowed_fields=["user.id", "user.name"],
    blocked_fields=["user.password"]
)
```

#### Exception Enhancement
```python
from corrupt_o11y.logging.processors import EnhancedExceptionProcessor

processor = EnhancedExceptionProcessor(
    include_locals=True,
    include_source=True,
    max_frames=10
)
```

#### Conditional Processing
```python
from corrupt_o11y.logging.processors import (
    ConditionalProcessor,
    is_level,
    has_exception,
    field_contains
)

# Only process error logs
processor = ConditionalProcessor(
    condition=is_level("error"),
    processor=EnhancedExceptionProcessor()
)

# Redact PII only in production
processor = ConditionalProcessor(
    condition=field_contains("environment", "prod"),
    processor=PIIRedactionProcessor()
)
```

### Custom Processors

Create custom processors by implementing the processor protocol:

```python
from structlog.types import EventDict, Processor

def my_custom_processor(logger, method_name: str, event_dict: EventDict) -> EventDict:
    # Transform the event_dict
    event_dict["custom_field"] = "custom_value"
    return event_dict

# Use with the collector
collector = logging.LoggingCollector()
collector.preprocessing().append(my_custom_processor)
```

### Processor Chains

Build complex processing pipelines:

```python
from corrupt_o11y.logging import LoggingCollector
from corrupt_o11y.logging.processors import (
    PIIRedactionProcessor,
    FieldFilterProcessor,
    ConditionalProcessor,
    is_level
)

collector = LoggingCollector()

# Add processors in order
collector.preprocessing().extend([
    PIIRedactionProcessor(),
    FieldFilterProcessor(blocked_fields=["internal_id"]),
    ConditionalProcessor(
        condition=is_level("error"),
        processor=EnhancedExceptionProcessor()
    )
])

# Configure logging with the collector
logging.configure_logging(config, collector)
```

## Metrics Collection

### Custom Metrics

```python
from prometheus_client import Counter, Histogram, Gauge
from corrupt_o11y.metrics import MetricsCollector

collector = MetricsCollector()

# Register custom metrics
request_counter = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=None
)
collector.register("http_requests", request_counter)

# Use metrics
request_counter.labels(method="GET", endpoint="/api/users", status="200").inc()
```

### Metric Naming Conventions

```python
# Use consistent naming with prefixes
config = MetricsConfig(metric_prefix="myapp_")
collector = MetricsCollector(config)

# Results in metrics like: myapp_http_requests_total
```

## Tracing Configuration

### Custom Trace Exporters

```python
from corrupt_o11y.tracing import TracingConfig, ExportType

# HTTP exporter
config = TracingConfig(
    export_type=ExportType.HTTP,
    endpoint="http://jaeger:14268/api/traces",
    headers={"Authorization": "Bearer token"}
)

# gRPC exporter
config = TracingConfig(
    export_type=ExportType.GRPC,
    endpoint="http://otel-collector:4317",
    insecure=True
)
```

### Distributed Tracing

```python
from opentelemetry import trace
from corrupt_o11y.tracing import get_tracer

tracer = get_tracer(__name__)

async def handle_request():
    with tracer.start_as_current_span("handle_request") as span:
        span.set_attribute("user_id", "123")
        span.set_attribute("request_size", 1024)

        # Nested spans
        with tracer.start_as_current_span("database_query"):
            # Database operation
            pass

        with tracer.start_as_current_span("external_api_call"):
            # External API call
            pass
```

## Operational Server

### Custom Health Checks

```python
from corrupt_o11y.operational import Status, OperationalServer

status = Status()

async def check_database():
    # Your database health check
    return database.is_healthy()

async def check_external_service():
    # Your external service check
    return external_service.is_available()

# Update status based on checks
if await check_database() and await check_external_service():
    status.is_ready = True
else:
    status.is_ready = False
```

### Custom Endpoints

```python
from aiohttp import web
from corrupt_o11y.operational import OperationalServer

class CustomOperationalServer(OperationalServer):
    def _setup_routes(self):
        super()._setup_routes()
        self.app.router.add_get("/custom", self._custom_endpoint)

    async def _custom_endpoint(self, request: web.Request) -> web.Response:
        return web.json_response({"custom": "data"})
```

## Environment-Based Configuration

### Development vs Production

```python
import os
from corrupt_o11y.logging import LoggingConfig
from corrupt_o11y.logging.processors import PIIRedactionProcessor, ConditionalProcessor

# Different configurations based on environment
env = os.getenv("ENVIRONMENT", "development")

if env == "production":
    # Production: JSON logs with PII redaction
    log_config = LoggingConfig(
        level="INFO",
        as_json=True,
        include_tracing=True
    )

    collector = LoggingCollector()
    collector.preprocessing().append(PIIRedactionProcessor())

else:
    # Development: Human-readable logs
    log_config = LoggingConfig(
        level="DEBUG",
        as_json=False,
        include_tracing=False
    )

    collector = LoggingCollector()
```

### Configuration Validation

```python
from corrupt_o11y.tracing import TracingConfig, ExportType

try:
    config = TracingConfig.from_env()
    if config.export_type != ExportType.STDOUT and not config.endpoint:
        raise ValueError("Endpoint required for non-stdout exporters")
except ValueError as e:
    # Handle configuration errors
    logger.error("Invalid tracing configuration", error=str(e))
```

## Performance Considerations

### Processor Performance

```python
from corrupt_o11y.logging.processors import make_processor_chain_safe

# Wrap processors to handle exceptions gracefully
safe_processors = make_processor_chain_safe([
    PIIRedactionProcessor(),
    custom_processor,
])
```

### Metrics Cardinality

```python
# Be careful with label cardinality
counter = Counter(
    "requests_total",
    "Total requests",
    ["method", "status"],  # Low cardinality
    registry=None
)

# Avoid high cardinality labels
# ["method", "status", "user_id"]  # High cardinality - avoid!
```

### Async Context

```python
import asyncio
from corrupt_o11y.operational import OperationalServer

async def main():
    server = OperationalServer(config, service_info, status, metrics)

    # Start server in background
    await server.start()

    try:
        # Your application logic
        await run_application()
    finally:
        # Clean shutdown
        await server.stop()

if __name__ == "__main__":
    asyncio.run(main())
```
