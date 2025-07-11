import json
import logging
from unittest.mock import patch

from corrupt_o11y.logging import LoggingCollector, LoggingConfig, ProcessorChain


class TestProcessorChain:
    """Tests for ProcessorChain class."""

    def test_empty_chain(self):
        """Test empty processor chain."""
        chain = ProcessorChain()

        assert len(chain) == 0
        assert chain.to_list() == []

    def test_append_processor(self):
        """Test appending processors to chain."""
        chain = ProcessorChain()

        def processor1(logger, method_name, event_dict):
            return event_dict

        def processor2(logger, method_name, event_dict):
            return event_dict

        chain.append(processor1)
        chain.append(processor2)

        assert len(chain) == 2
        processors = chain.to_list()
        assert processors[0] is processor1
        assert processors[1] is processor2

    def test_replace_processors(self):
        """Test replacing all processors at once."""
        chain = ProcessorChain()

        def processor1(logger, method_name, event_dict):
            return event_dict

        def processor2(logger, method_name, event_dict):
            return event_dict

        processors = [processor1, processor2]
        chain.replace(processors)

        assert len(chain) == 2
        assert chain.to_list() == processors

    def test_clear_chain(self):
        """Test clearing processor chain."""
        chain = ProcessorChain()

        def processor(logger, method_name, event_dict):
            return event_dict

        chain.append(processor)
        assert len(chain) == 1

        chain.clear()
        assert len(chain) == 0
        assert chain.to_list() == []

    def test_iteration(self):
        """Test iterating over processor chain."""
        chain = ProcessorChain()

        def processor1(logger, method_name, event_dict):
            return event_dict

        def processor2(logger, method_name, event_dict):
            return event_dict

        chain.append(processor1)
        chain.append(processor2)

        processors = list(chain)
        assert processors[0] is processor1
        assert processors[1] is processor2

    def test_initialization_with_processors(self):
        """Test ProcessorChain initialization with processors."""

        def processor1(logger, method_name, event_dict):
            return event_dict

        def processor2(logger, method_name, event_dict):
            return event_dict

        processors = [processor1, processor2]
        chain = ProcessorChain(processors)

        assert len(chain) == 2
        assert chain.to_list() == processors


class TestLoggingCollector:
    """Tests for LoggingCollector class."""

    def test_default_initialization(self):
        """Test LoggingCollector with default config."""
        config = LoggingConfig(level=logging.INFO, as_json=False, integrate_tracing=False)
        collector = LoggingCollector(config)

        assert collector._config is config
        assert collector._safe_processors is True

    def test_custom_initialization(self):
        """Test LoggingCollector with custom parameters."""
        config = LoggingConfig(level=logging.DEBUG, as_json=True, integrate_tracing=True)
        collector = LoggingCollector(config, safe_processors=False)

        assert collector._config is config
        assert collector._safe_processors is False

    def test_processor_chains_exist(self):
        """Test that all processor chains are created."""
        config = LoggingConfig(level=logging.INFO, as_json=False, integrate_tracing=False)
        collector = LoggingCollector(config)

        # Test that all chains exist
        assert hasattr(collector, "_early_processing")
        assert hasattr(collector, "_preprocessing")
        assert hasattr(collector, "_processing")
        assert hasattr(collector, "_postprocessing")

        # Test chain accessor methods
        early_chain = collector.early_processing()
        pre_chain = collector.preprocessing()
        core_chain = collector.processing()
        post_chain = collector.postprocessing()

        assert isinstance(early_chain, ProcessorChain)
        assert isinstance(pre_chain, ProcessorChain)
        assert isinstance(core_chain, ProcessorChain)
        assert isinstance(post_chain, ProcessorChain)

    def test_early_processing_has_processors(self):
        """Test that early processing chain has built-in processors."""
        config = LoggingConfig(level=logging.INFO, as_json=False, integrate_tracing=False)
        collector = LoggingCollector(config)

        early_chain = collector.early_processing()
        # Should have several built-in processors
        assert len(early_chain) > 0

    def test_tracing_integration_adds_processor(self):
        """Test that tracing integration adds processor to core chain."""
        config_without_tracing = LoggingConfig(
            level=logging.INFO, as_json=False, integrate_tracing=False
        )
        collector_without = LoggingCollector(config_without_tracing)

        config_with_tracing = LoggingConfig(
            level=logging.INFO, as_json=False, integrate_tracing=True
        )
        collector_with = LoggingCollector(config_with_tracing)

        # Collector with tracing should have more processors in core chain
        without_count = len(collector_without.processing())
        with_count = len(collector_with.processing())
        assert with_count > without_count

    def test_json_config_adds_exception_processor(self):
        """Test that JSON config adds exception processor."""
        config_text = LoggingConfig(level=logging.INFO, as_json=False, integrate_tracing=False)
        collector_text = LoggingCollector(config_text)

        config_json = LoggingConfig(level=logging.INFO, as_json=True, integrate_tracing=False)
        collector_json = LoggingCollector(config_json)

        # JSON collector should have more processors (exception processor)
        text_count = len(collector_text.processing())
        json_count = len(collector_json.processing())
        assert json_count > text_count

    def test_build_processor_list(self):
        """Test building complete processor list."""
        config = LoggingConfig(level=logging.INFO, as_json=False, integrate_tracing=False)
        collector = LoggingCollector(config)

        # Add some processors to user chains
        def test_processor(logger, method_name, event_dict):
            return event_dict

        collector.preprocessing().append(test_processor)
        collector.postprocessing().append(test_processor)

        processors = collector.build_processor_list()

        # Should include processors from all chains
        assert len(processors) > 0
        # Should include more processors now (at least 2 test processors added)
        initial_count = len(LoggingCollector(config).build_processor_list())
        assert len(processors) > initial_count

    @patch("corrupt_o11y.logging.collector.structlog.configure")
    def test_configure_calls_structlog(self, mock_structlog_configure):
        """Test that configure() calls structlog.configure."""
        config = LoggingConfig(level=logging.INFO, as_json=False, integrate_tracing=False)
        collector = LoggingCollector(config)

        collector.configure()

        # Should have called structlog.configure
        mock_structlog_configure.assert_called_once()

    @patch("corrupt_o11y.logging.collector.structlog.configure")
    def test_configure_structlog_parameters(self, mock_structlog_configure):
        """Test configure passes correct parameters to structlog."""
        config = LoggingConfig(level=logging.INFO, as_json=False, integrate_tracing=False)
        collector = LoggingCollector(config)

        collector.configure()

        # Should have called structlog.configure
        mock_structlog_configure.assert_called_once()
        call_kwargs = mock_structlog_configure.call_args[1]
        assert "wrapper_class" in call_kwargs
        assert "logger_factory" in call_kwargs
        assert "processors" in call_kwargs
        assert "cache_logger_on_first_use" in call_kwargs
        # Verify processors list is not empty
        assert len(call_kwargs["processors"]) > 0

    def test_json_serializer(self):
        """Test JSON serializer method."""
        config = LoggingConfig(level=logging.INFO, as_json=True, integrate_tracing=False)
        collector = LoggingCollector(config)

        test_data = {"key": "value", "number": 42}
        result = collector._json_serializer(test_data, None)

        assert isinstance(result, str)
        # Should be valid JSON containing our data
        parsed = json.loads(result)
        assert parsed["key"] == "value"
        assert parsed["number"] == 42
