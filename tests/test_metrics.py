from prometheus_client import Counter, Gauge

from corrupt_o11y.metadata import ServiceInfo
from corrupt_o11y.metrics import (
    MetricsCollector,
    MetricsConfig,
    create_service_info_metric,
    create_service_info_metric_from_service_info,
)


class TestMetricsConfig:
    """Tests for MetricsConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = MetricsConfig()

        assert config.enable_gc_collector is True
        assert config.enable_platform_collector is True
        assert config.enable_process_collector is True
        assert config.metric_prefix == ""

    def test_custom_config(self):
        """Test custom configuration values."""
        config = MetricsConfig(
            enable_gc_collector=False,
            enable_platform_collector=False,
            enable_process_collector=False,
            metric_prefix="myapp_",
        )

        assert config.enable_gc_collector is False
        assert config.enable_platform_collector is False
        assert config.enable_process_collector is False
        assert config.metric_prefix == "myapp_"

    def test_from_env_defaults(self, monkeypatch):
        """Test MetricsConfig.from_env with default values."""
        # Clear all relevant env vars
        for var in [
            "METRICS_ENABLE_GC",
            "METRICS_ENABLE_PLATFORM",
            "METRICS_ENABLE_PROCESS",
            "METRICS_PREFIX",
        ]:
            monkeypatch.delenv(var, raising=False)

        config = MetricsConfig.from_env()

        assert config.enable_gc_collector is True
        assert config.enable_platform_collector is True
        assert config.enable_process_collector is True
        assert config.metric_prefix == ""

    def test_from_env_custom(self, monkeypatch):
        """Test MetricsConfig.from_env with custom values."""
        monkeypatch.setenv("METRICS_ENABLE_GC", "false")
        monkeypatch.setenv("METRICS_ENABLE_PLATFORM", "no")
        monkeypatch.setenv("METRICS_ENABLE_PROCESS", "0")
        monkeypatch.setenv("METRICS_PREFIX", "test_")

        config = MetricsConfig.from_env()

        assert config.enable_gc_collector is False
        assert config.enable_platform_collector is False
        assert config.enable_process_collector is False
        assert config.metric_prefix == "test_"


class TestMetricsCollector:
    """Tests for MetricsCollector class."""

    def test_default_initialization(self):
        """Test MetricsCollector with default config."""
        collector = MetricsCollector()

        # Should have built-in collectors registered
        registry = collector.registry
        assert len(registry._collector_to_names) >= 3  # GC, platform, process

    def test_custom_config_initialization(self):
        """Test MetricsCollector with custom config."""
        config = MetricsConfig(
            enable_gc_collector=False,
            enable_platform_collector=False,
            enable_process_collector=False,
        )
        collector = MetricsCollector(config)

        # Should have no built-in collectors
        registry = collector.registry
        assert len(registry._collector_to_names) == 0

    def test_register_metric(self):
        """Test registering a custom metric."""
        config = MetricsConfig(
            enable_gc_collector=False,
            enable_platform_collector=False,
            enable_process_collector=False,
        )
        collector = MetricsCollector(config)
        counter = Counter("register_test_counter", "Test counter description", registry=None)

        collector.register("test_counter", counter)

        # Verify it's registered
        assert "test_counter" in collector._metrics
        assert collector._metrics["test_counter"] is counter

    def test_unregister_metric(self):
        """Test unregistering a metric."""
        config = MetricsConfig(
            enable_gc_collector=False,
            enable_platform_collector=False,
            enable_process_collector=False,
        )
        collector = MetricsCollector(config)
        counter = Counter("unregister_test_counter", "Test counter description", registry=None)

        collector.register("test_counter", counter)
        assert "test_counter" in collector._metrics

        collector.unregister("test_counter")
        assert "test_counter" not in collector._metrics

    def test_unregister_nonexistent_metric(self):
        """Test unregistering a non-existent metric doesn't raise error."""
        collector = MetricsCollector()

        # Should not raise
        collector.unregister("nonexistent_metric")

    def test_clear_metrics(self):
        """Test clearing all custom metrics."""
        config = MetricsConfig(
            enable_gc_collector=False,
            enable_platform_collector=False,
            enable_process_collector=False,
        )
        collector = MetricsCollector(config)

        # Register some metrics
        counter = Counter("clear_test_counter", "Test counter", registry=None)
        gauge = Gauge("clear_test_gauge", "Test gauge", registry=None)
        collector.register("counter", counter)
        collector.register("gauge", gauge)

        assert len(collector._metrics) == 2

        collector.clear()

        assert len(collector._metrics) == 0

    def test_registry_property(self):
        """Test registry property returns the underlying registry."""
        collector = MetricsCollector()
        registry = collector.registry

        # Should be the same object
        assert registry is collector._registry

    def test_create_service_info_metric(self):
        """Test creating service info metric through collector."""
        collector = MetricsCollector()

        metric = collector.create_service_info_metric(
            service_name="test-service",
            service_version="1.0.0",
            instance_id="test-instance",
            commit_sha="abc123",
            build_time="2023-01-01T00:00:00Z",
        )

        assert isinstance(metric, Gauge)
        assert "service_info" in collector._metrics
        assert collector._metrics["service_info"] is metric

    def test_create_service_info_metric_from_service_info(self):
        """Test creating service info metric from ServiceInfo object."""
        collector = MetricsCollector()
        service_info = ServiceInfo(
            name="test-service",
            version="1.0.0",
            instance_id="test-instance",
            commit_sha="abc123",
            build_time="2023-01-01T00:00:00Z",
        )

        metric = collector.create_service_info_metric_from_service_info(service_info)

        assert isinstance(metric, Gauge)
        assert "service_info" in collector._metrics


class TestServiceInfoMetricFunctions:
    """Tests for standalone service info metric functions."""

    def test_create_service_info_metric_basic(self):
        """Test basic service info metric creation."""
        metric = create_service_info_metric(
            service_name="test-service", service_version="1.0.0", instance_id="test-instance"
        )

        assert isinstance(metric, Gauge)
        assert metric._name == "service_info"
        assert "service" in metric._labelnames
        assert "version" in metric._labelnames
        assert "instance" in metric._labelnames

    def test_create_service_info_metric_with_optional_fields(self):
        """Test service info metric creation with optional fields."""
        metric = create_service_info_metric(
            service_name="test-service",
            service_version="1.0.0",
            instance_id="test-instance",
            commit_sha="abc123",
            build_time="2023-01-01T00:00:00Z",
        )

        assert isinstance(metric, Gauge)
        assert "commit" in metric._labelnames
        assert "build_time" in metric._labelnames

    def test_create_service_info_metric_none_values_filtered(self):
        """Test that None values are filtered out from labels."""
        metric = create_service_info_metric(
            service_name="test-service",
            service_version="1.0.0",
            instance_id="test-instance",
            commit_sha=None,
            build_time=None,
        )

        assert isinstance(metric, Gauge)
        assert "commit" not in metric._labelnames
        assert "build_time" not in metric._labelnames

    def test_create_service_info_metric_from_service_info_basic(self):
        """Test creating service info metric from ServiceInfo object."""
        service_info = ServiceInfo(
            name="test-service",
            version="1.0.0",
            instance_id="test-instance",
            commit_sha="abc123",
            build_time="2023-01-01T00:00:00Z",
        )

        metric = create_service_info_metric_from_service_info(service_info)

        assert isinstance(metric, Gauge)
        assert metric._name == "service_info"

    def test_create_service_info_metric_from_service_info_filters_dev_values(self):
        """Test that unknown-dev values are filtered out."""
        service_info = ServiceInfo(
            name="test-service",
            version="1.0.0",
            instance_id="test-instance",
            commit_sha="unknown-dev",
            build_time="unknown-dev",
        )

        metric = create_service_info_metric_from_service_info(service_info)

        assert isinstance(metric, Gauge)
        # Should not include commit or build_time labels since they're "unknown-dev"
        assert "commit" not in metric._labelnames
        assert "build_time" not in metric._labelnames

    def test_service_info_metric_value_is_one(self):
        """Test that service info metric value is set to 1."""
        metric = create_service_info_metric(
            service_name="test-service", service_version="1.0.0", instance_id="test-instance"
        )

        # Get the metric value
        metric_families = list(metric.collect())
        samples = list(metric_families[0].samples)
        assert len(samples) == 1
        assert samples[0].value == 1.0
