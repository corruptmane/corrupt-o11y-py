from collections.abc import MutableMapping, Sequence

from prometheus_client import (
    GC_COLLECTOR,
    PLATFORM_COLLECTOR,
    PROCESS_COLLECTOR,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Summary,
)
from prometheus_client.registry import Collector

from corrupt_o11y.metadata import ServiceInfo

from .config import MetricsConfig


class MetricsCollector:
    """Prometheus metrics collector with configurable built-in metrics.

    Provides a centralized registry for Prometheus metrics with optional
    garbage collection, platform, and process metrics.
    """

    def __init__(self, config: MetricsConfig | None = None) -> None:
        """Initialize metrics collector.

        Args:
            config: Configuration for metrics collection. If None, uses defaults.
        """
        self._config = config or MetricsConfig()
        self._registry = CollectorRegistry()
        self._metrics: MutableMapping[str, Collector] = {}

        # Register built-in collectors based on configuration
        if self._config.enable_gc_collector:
            self._registry.register(GC_COLLECTOR)
        if self._config.enable_platform_collector:
            self._registry.register(PLATFORM_COLLECTOR)
        if self._config.enable_process_collector:
            self._registry.register(PROCESS_COLLECTOR)

    def register(self, name: str, collector: Collector) -> None:
        """Register a metric collector.

        Args:
            name: Name to identify the collector.
            collector: Prometheus collector instance.
        """
        self._registry.register(collector)
        self._metrics[name] = collector

    def unregister(self, name: str) -> None:
        """Unregister a metric collector.

        Args:
            name: Name of the collector to unregister.
        """
        if collector := self._metrics.pop(name, None):
            self._registry.unregister(collector)

    @property
    def registry(self) -> CollectorRegistry:
        """Get the underlying Prometheus registry.

        Returns:
            Prometheus collector registry.
        """
        return self._registry

    def clear(self) -> None:
        """Clear all custom registered metrics.

        Built-in metrics (GC, platform, process) are not cleared.
        """
        for name in list(self._metrics.keys()):
            self.unregister(name)
        self._metrics.clear()

    def create_service_info_metric(
        self,
        service_name: str,
        service_version: str,
        instance_id: str,
        commit_sha: str | None = None,
        build_time: str | None = None,
    ) -> Gauge:
        """Create a service info metric using this collector's registry."""
        metric = create_service_info_metric(
            service_name=service_name,
            service_version=service_version,
            instance_id=instance_id,
            commit_sha=commit_sha,
            build_time=build_time,
            registry=None,  # Don't auto-register
        )
        self.register("service_info", metric)
        return metric

    def create_service_info_metric_from_service_info(self, service_info: ServiceInfo) -> Gauge:
        """Create a service info metric from ServiceInfo using this collector's registry."""
        return self.create_service_info_metric(
            service_name=service_info.name,
            service_version=service_info.version,
            instance_id=service_info.instance_id,
            commit_sha=service_info.commit_sha,
            build_time=service_info.build_time,
        )

    def create_counter(
        self,
        name: str,
        documentation: str,
        labelnames: list[str] | None = None,
        unit: str = "",
    ) -> Counter:
        """Create a Counter metric and register it with this collector.

        Args:
            name: Name of the metric.
            documentation: Help text for the metric.
            labelnames: List of label names for the metric.
            unit: Unit of measurement (optional).

        Returns:
            Counter metric instance.
        """
        metric_name = f"{self._config.metric_prefix}{name}"
        if unit:
            metric_name = f"{metric_name}_{unit}"

        counter = Counter(
            metric_name,
            documentation,
            labelnames=labelnames or [],
            registry=None,
        )
        self.register(name, counter)
        return counter

    def create_gauge(
        self,
        name: str,
        documentation: str,
        labelnames: list[str] | None = None,
        unit: str = "",
    ) -> Gauge:
        """Create a Gauge metric and register it with this collector.

        Args:
            name: Name of the metric.
            documentation: Help text for the metric.
            labelnames: List of label names for the metric.
            unit: Unit of measurement (optional).

        Returns:
            Gauge metric instance.
        """
        metric_name = f"{self._config.metric_prefix}{name}"
        if unit:
            metric_name = f"{metric_name}_{unit}"

        gauge = Gauge(
            metric_name,
            documentation,
            labelnames=labelnames or [],
            registry=None,
        )
        self.register(name, gauge)
        return gauge

    def create_histogram(
        self,
        name: str,
        documentation: str,
        labelnames: list[str] | None = None,
        buckets: Sequence[float | str] = Histogram.DEFAULT_BUCKETS,
        unit: str = "",
    ) -> Histogram:
        """Create a Histogram metric and register it with this collector.

        Args:
            name: Name of the metric.
            documentation: Help text for the metric.
            labelnames: List of label names for the metric.
            buckets: Histogram buckets (optional, uses default if None).
            unit: Unit of measurement (optional).

        Returns:
            Histogram metric instance.
        """
        metric_name = f"{self._config.metric_prefix}{name}"
        if unit:
            metric_name = f"{metric_name}_{unit}"

        histogram = Histogram(
            name=metric_name,
            documentation=documentation,
            labelnames=labelnames or [],
            registry=None,
            buckets=buckets,
        )
        self.register(name, histogram)
        return histogram

    def create_summary(
        self,
        name: str,
        documentation: str,
        labelnames: list[str] | None = None,
        unit: str = "",
    ) -> Summary:
        """Create a Summary metric and register it with this collector.

        Args:
            name: Name of the metric.
            documentation: Help text for the metric.
            labelnames: List of label names for the metric.
            unit: Unit of measurement (optional).

        Returns:
            Summary metric instance.
        """
        metric_name = f"{self._config.metric_prefix}{name}"
        if unit:
            metric_name = f"{metric_name}_{unit}"

        summary = Summary(
            metric_name,
            documentation,
            labelnames=labelnames or [],
            registry=None,
        )
        self.register(name, summary)
        return summary


def create_service_info_metric(
    service_name: str,
    service_version: str,
    instance_id: str,
    commit_sha: str | None = None,
    build_time: str | None = None,
    registry: CollectorRegistry | None = None,
) -> Gauge:
    """Create a service info metric following Prometheus best practices.

    Creates a metric with value 1 that carries service metadata as labels.
    This is the standard pattern for exposing build and deployment information.

    Args:
        service_name: Name of the service.
        service_version: Version of the service.
        instance_id: Unique identifier for the service instance.
        commit_sha: Git commit SHA (optional).
        build_time: Build timestamp (optional).
        registry: Prometheus registry to register the metric with (optional).

    Returns:
        Configured Gauge metric with service information.

    Example:
        >>> info_metric = create_service_info_metric(
        ...     service_name="my-service",
        ...     service_version="1.2.3",
        ...     instance_id="pod-123",
        ...     commit_sha="abc123",
        ...     build_time="2023-01-01T10:00:00Z"
        ... )
        >>> # Results in: service_info{service="my-service", version="1.2.3", ...} 1
    """
    # Build label names and values, filtering out None values
    labels = {
        "service": service_name,
        "version": service_version,
        "instance": instance_id,
    }

    if commit_sha is not None:
        labels["commit"] = commit_sha
    if build_time is not None:
        labels["build_time"] = build_time

    info_metric = Gauge(
        "service_info",
        "Service information and build metadata",
        labelnames=list(labels.keys()),
        registry=registry,
    )

    info_metric.labels(**labels).set(1)
    return info_metric


def create_service_info_metric_from_service_info(service_info: ServiceInfo) -> Gauge:
    """Create a service info metric from ServiceInfo instance.

    Convenience function that extracts metadata from ServiceInfo and creates
    the standard service_info metric.

    Args:
        service_info: ServiceInfo instance containing service metadata.

    Returns:
        Configured Gauge metric with service information.

    Example:
        >>> from corrupt_o11y.metadata import ServiceInfo
        >>> service = ServiceInfo.from_env()
        >>> info_metric = create_service_info_metric_from_service_info(service)
    """
    return create_service_info_metric(
        service_name=service_info.name,
        service_version=service_info.version,
        instance_id=service_info.instance_id,
        commit_sha=service_info.commit_sha if service_info.commit_sha != "unknown-dev" else None,
        build_time=service_info.build_time if service_info.build_time != "unknown-dev" else None,
    )
