from unittest.mock import MagicMock, patch

import pytest

from corrupt_o11y.tracing import ExportType, TracingConfig, TracingError, configure_tracing


class TestExportType:
    """Tests for ExportType enum."""

    def test_export_type_values(self):
        """Test ExportType enum values."""
        assert ExportType.STDOUT.value == "stdout"
        assert ExportType.HTTP.value == "http"
        assert ExportType.GRPC.value == "grpc"


class TestTracingConfig:
    """Tests for TracingConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TracingConfig(export_type=ExportType.STDOUT, endpoint="")

        assert config.export_type == ExportType.STDOUT
        assert config.endpoint == ""
        assert config.insecure is False
        assert config.timeout == 30
        assert config.headers is None

    def test_custom_config(self):
        """Test custom configuration values."""
        headers = {"Authorization": "Bearer token"}
        config = TracingConfig(
            export_type=ExportType.HTTP,
            endpoint="http://localhost:4318/v1/traces",
            insecure=True,
            timeout=60,
            headers=headers,
        )

        assert config.export_type == ExportType.HTTP
        assert config.endpoint == "http://localhost:4318/v1/traces"
        assert config.insecure is True
        assert config.timeout == 60
        assert config.headers == headers

    def test_from_env_defaults(self, monkeypatch):
        """Test TracingConfig.from_env with default values."""
        # Clear all relevant env vars
        for var in [
            "TRACING_EXPORTER_TYPE",
            "TRACING_EXPORTER_ENDPOINT",
            "TRACING_INSECURE",
            "TRACING_TIMEOUT",
        ]:
            monkeypatch.delenv(var, raising=False)

        config = TracingConfig.from_env()

        assert config.export_type == ExportType.STDOUT
        assert config.endpoint == ""
        assert config.insecure is False
        assert config.timeout == 30
        assert config.headers is None

    def test_from_env_custom(self, monkeypatch):
        """Test TracingConfig.from_env with custom values."""
        monkeypatch.setenv("TRACING_EXPORTER_TYPE", "http")
        monkeypatch.setenv("TRACING_EXPORTER_ENDPOINT", "http://jaeger:14268/api/traces")
        monkeypatch.setenv("TRACING_INSECURE", "true")
        monkeypatch.setenv("TRACING_TIMEOUT", "120")

        headers = {"X-Custom": "header"}
        config = TracingConfig.from_env(headers=headers)

        assert config.export_type == ExportType.HTTP
        assert config.endpoint == "http://jaeger:14268/api/traces"
        assert config.insecure is True
        assert config.timeout == 120
        assert config.headers == headers

    def test_from_env_invalid_export_type(self, monkeypatch):
        """Test TracingConfig.from_env with invalid export type."""
        monkeypatch.setenv("TRACING_EXPORTER_TYPE", "invalid")

        with pytest.raises(ValueError, match="Invalid TRACING_EXPORTER_TYPE"):
            TracingConfig.from_env()

    def test_from_env_invalid_timeout(self, monkeypatch):
        """Test TracingConfig.from_env with invalid timeout."""
        monkeypatch.setenv("TRACING_TIMEOUT", "not_a_number")

        with pytest.raises(ValueError, match="Invalid TRACING_TIMEOUT"):
            TracingConfig.from_env()

    def test_from_env_timeout_too_small(self, monkeypatch):
        """Test TracingConfig.from_env with timeout too small."""
        monkeypatch.setenv("TRACING_TIMEOUT", "0")

        with pytest.raises(ValueError, match="timeout must be at least 1 second"):
            TracingConfig.from_env()

    def test_from_env_negative_timeout(self, monkeypatch):
        """Test TracingConfig.from_env with negative timeout."""
        monkeypatch.setenv("TRACING_TIMEOUT", "-5")

        with pytest.raises(ValueError, match="timeout must be at least 1 second"):
            TracingConfig.from_env()


class TestConfigureTracing:
    """Tests for configure_tracing function."""

    @patch("corrupt_o11y.tracing.tracer.trace.set_tracer_provider")
    @patch("corrupt_o11y.tracing.tracer.Resource")
    def test_configure_stdout_tracing(self, mock_resource, mock_set_tracer_provider):
        """Test configuring stdout tracing."""
        config = TracingConfig(export_type=ExportType.STDOUT, endpoint="")

        configure_tracing(config, "test-service", "1.0.0")

        # Verify resource was created with correct attributes
        mock_resource.create.assert_called_once()
        call_kwargs = mock_resource.create.call_args[1]
        assert "attributes" in call_kwargs
        attributes = call_kwargs["attributes"]
        assert "service.name" in attributes
        assert "service.version" in attributes
        assert attributes["service.name"] == "test-service"
        assert attributes["service.version"] == "1.0.0"

        # Verify tracer provider was set
        mock_set_tracer_provider.assert_called_once()

    @patch("corrupt_o11y.tracing.tracer.trace.set_tracer_provider")
    @patch("corrupt_o11y.tracing.tracer.Resource")
    @patch("corrupt_o11y.tracing.tracer.OTLPHttpExporter")
    def test_configure_http_tracing(
        self, mock_http_exporter, mock_resource, mock_set_tracer_provider
    ):
        """Test configuring HTTP tracing."""
        config = TracingConfig(
            export_type=ExportType.HTTP,
            endpoint="http://localhost:4318/v1/traces",
            timeout=60,
            headers={"Authorization": "Bearer token"},
        )

        configure_tracing(config, "test-service", "1.0.0")

        # Verify HTTP exporter was created with correct parameters
        mock_http_exporter.assert_called_once_with(
            endpoint="http://localhost:4318/v1/traces",
            timeout=60,
            headers={"Authorization": "Bearer token"},
        )

        # Verify tracer provider was set
        mock_set_tracer_provider.assert_called_once()

    @patch("corrupt_o11y.tracing.tracer.trace.set_tracer_provider")
    @patch("corrupt_o11y.tracing.tracer.Resource")
    @patch("corrupt_o11y.tracing.tracer.OTLPGrpcExporter")
    def test_configure_grpc_tracing(
        self, mock_grpc_exporter, mock_resource, mock_set_tracer_provider
    ):
        """Test configuring GRPC tracing."""
        config = TracingConfig(
            export_type=ExportType.GRPC,
            endpoint="http://localhost:4317",
            insecure=True,
            timeout=90,
            headers={"X-API-Key": "secret"},
        )

        configure_tracing(config, "test-service", "1.0.0")

        # Verify GRPC exporter was created with correct parameters
        mock_grpc_exporter.assert_called_once_with(
            endpoint="http://localhost:4317",
            insecure=True,
            timeout=90,
            headers={"X-API-Key": "secret"},
        )

        # Verify tracer provider was set
        mock_set_tracer_provider.assert_called_once()

    def test_configure_http_tracing_no_endpoint(self):
        """Test configuring HTTP tracing without endpoint raises error."""
        config = TracingConfig(export_type=ExportType.HTTP, endpoint="")

        with pytest.raises(TracingError, match="HTTP exporter requires an endpoint"):
            configure_tracing(config, "test-service", "1.0.0")

    def test_configure_grpc_tracing_no_endpoint(self):
        """Test configuring GRPC tracing without endpoint raises error."""
        config = TracingConfig(export_type=ExportType.GRPC, endpoint="")

        with pytest.raises(TracingError, match="GRPC exporter requires an endpoint"):
            configure_tracing(config, "test-service", "1.0.0")

    @patch("corrupt_o11y.tracing.tracer.trace.set_tracer_provider")
    @patch("corrupt_o11y.tracing.tracer.Resource")
    def test_resource_attributes(self, mock_resource, mock_set_tracer_provider):
        """Test that resource is created with correct attributes."""
        config = TracingConfig(export_type=ExportType.STDOUT, endpoint="")

        configure_tracing(config, "my-service", "2.1.0")

        # Verify resource was created with expected attributes
        mock_resource.create.assert_called_once()
        call_kwargs = mock_resource.create.call_args[1]
        assert "attributes" in call_kwargs
        attributes = call_kwargs["attributes"]

        expected_attrs = {"service.name": "my-service", "service.version": "2.1.0"}

        for key, value in expected_attrs.items():
            assert attributes[key] == value

    @patch("corrupt_o11y.tracing.tracer.trace.set_tracer_provider")
    @patch("corrupt_o11y.tracing.tracer.Resource")
    @patch("corrupt_o11y.tracing.tracer.TracerProvider")
    @patch("corrupt_o11y.tracing.tracer.BatchSpanProcessor")
    def test_tracer_provider_setup(
        self,
        mock_batch_processor,
        mock_tracer_provider_class,
        mock_resource,
        mock_set_tracer_provider,
    ):
        """Test that tracer provider is set up correctly."""
        config = TracingConfig(export_type=ExportType.STDOUT, endpoint="")

        mock_tracer_provider = MagicMock()
        mock_tracer_provider_class.return_value = mock_tracer_provider
        mock_span_processor = MagicMock()
        mock_batch_processor.return_value = mock_span_processor

        configure_tracing(config, "test-service", "1.0.0")

        # Verify tracer provider was created with resource
        mock_tracer_provider_class.assert_called_once()
        call_kwargs = mock_tracer_provider_class.call_args[1]
        assert "resource" in call_kwargs

        # Verify span processor was added
        mock_tracer_provider.add_span_processor.assert_called_once_with(mock_span_processor)

        # Verify tracer provider was set globally
        mock_set_tracer_provider.assert_called_once_with(mock_tracer_provider)
