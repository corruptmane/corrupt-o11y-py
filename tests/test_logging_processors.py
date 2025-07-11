import sys
from unittest.mock import MagicMock, patch

import pytest

from corrupt_o11y.logging.processors import (
    ConditionalProcessor,
    EnhancedExceptionProcessor,
    FieldFilterProcessor,
    PIIRedactionProcessor,
    add_open_telemetry_spans,
    make_processor_chain_safe,
    safe_processor,
)


class TestSafeProcessor:
    """Tests for safe_processor decorator."""

    def test_safe_processor_success(self):
        """Test safe_processor when processor succeeds."""

        @safe_processor
        def test_processor(logger, method_name, event_dict):
            event_dict["processed"] = True
            return event_dict

        logger = MagicMock()
        event_dict = {"message": "test"}

        result = test_processor(logger, "info", event_dict)

        assert result["processed"] is True
        assert result["message"] == "test"

    def test_safe_processor_exception(self):
        """Test safe_processor when processor raises exception."""

        def failing_processor(logger, method_name, event_dict):
            raise ValueError("Test error")

        wrapped_processor = safe_processor(failing_processor)

        logger = MagicMock()
        event_dict = {"message": "test"}

        # Should not raise, but return event_dict with error info
        result = wrapped_processor(logger, "info", event_dict)

        assert result["message"] == "test"
        assert "_processor_errors" in result
        assert len(result["_processor_errors"]) == 1
        assert result["_processor_errors"][0]["error"] == "Test error"
        assert result["_processor_errors"][0]["error_type"] == "ValueError"

    def test_make_processor_chain_safe(self):
        """Test making a chain of processors safe."""

        def processor1(logger, method_name, event_dict):
            event_dict["step1"] = True
            return event_dict

        def failing_processor(logger, method_name, event_dict):
            raise ValueError("Test error")

        def processor2(logger, method_name, event_dict):
            event_dict["step2"] = True
            return event_dict

        processors = [processor1, failing_processor, processor2]
        safe_processors = make_processor_chain_safe(processors)

        logger = MagicMock()
        event_dict = {"message": "test"}

        # Process through all safe processors
        result = event_dict
        for processor in safe_processors:
            result = processor(logger, "info", result)

        # Should have step1 and step2, but no exception
        assert result["step1"] is True
        assert result["step2"] is True
        assert result["message"] == "test"


class TestPIIRedactionProcessor:
    """Tests for PIIRedactionProcessor."""

    def test_default_patterns(self):
        """Test PII redaction with default patterns."""
        processor = PIIRedactionProcessor()

        event_dict = {
            "email": "user@example.com",
            "phone": "555-123-4567",
            "ssn": "123-45-6789",
            "credit_card": "4111-1111-1111-1111",
            "safe_data": "this is safe",
        }

        result = processor(MagicMock(), "info", event_dict)

        assert result["email"] == "<EMAIL>"
        assert result["phone"] == "<PHONE>"
        assert result["ssn"] == "<SSN>"
        assert result["credit_card"] == "<CREDIT_CARD>"
        assert result["safe_data"] == "this is safe"

    def test_custom_patterns(self):
        """Test PII redaction with custom patterns."""
        custom_patterns = {"secret": r"secret_\w+", "token": r"tok_\w+"}
        processor = PIIRedactionProcessor(patterns=custom_patterns)

        event_dict = {
            "api_key": "secret_abc123",
            "access_token": "tok_xyz789",
            "normal_text": "this is normal",
        }

        result = processor(MagicMock(), "info", event_dict)

        assert result["api_key"] == "<REDACTED>"
        assert result["access_token"] == "<REDACTED>"
        assert result["normal_text"] == "this is normal"

    def test_redact_keys(self):
        """Test PII redaction with keys to always redact."""
        processor = PIIRedactionProcessor(redact_keys={"password", "secret_key"})

        event_dict = {
            "password": "any_value_here",
            "secret_key": "also_any_value",
            "normal_field": "safe data",
        }

        result = processor(MagicMock(), "info", event_dict)

        assert result["password"] == "<REDACTED>"
        assert result["secret_key"] == "<REDACTED>"
        assert result["normal_field"] == "safe data"

    def test_nested_data_redaction(self):
        """Test PII redaction in nested structures."""
        processor = PIIRedactionProcessor()

        event_dict = {
            "user": {"email": "user@example.com", "profile": {"phone": "555-123-4567"}},
            "safe": "data",
        }

        result = processor(MagicMock(), "info", event_dict)

        assert result["user"]["email"] == "<EMAIL>"
        assert result["user"]["profile"]["phone"] == "<PHONE>"
        assert result["safe"] == "data"


class TestFieldFilterProcessor:
    """Tests for FieldFilterProcessor."""

    def test_allowlist_filter(self):
        """Test field filtering with allowlist and preserve_essential=False."""
        processor = FieldFilterProcessor(
            allowed_fields={"message", "level"}, preserve_essential=False
        )

        event_dict = {
            "message": "test message",
            "level": "INFO",
            "timestamp": "2023-01-01",
            "extra_data": "should be removed",
        }

        result = processor(MagicMock(), "info", event_dict)

        assert "message" in result
        assert "level" in result
        assert "timestamp" not in result
        assert "extra_data" not in result

    def test_blocklist_filter(self):
        """Test field filtering with blocklist."""
        processor = FieldFilterProcessor(blocked_fields={"password", "secret"})

        event_dict = {
            "message": "test message",
            "password": "secret123",
            "secret": "top_secret",
            "level": "INFO",
        }

        result = processor(MagicMock(), "info", event_dict)

        assert "message" in result
        assert "level" in result
        assert "password" not in result
        assert "secret" not in result

    def test_preserve_essential_fields(self):
        """Test that essential fields are preserved even in allowlist mode."""
        processor = FieldFilterProcessor(allowed_fields={"custom_field"}, preserve_essential=True)

        event_dict = {
            "event": "test message",
            "level": "INFO",
            "timestamp": "2023-01-01",
            "custom_field": "keep this",
            "extra_data": "should be removed",
        }

        result = processor(MagicMock(), "info", event_dict)

        # Should keep essential fields even though not in allowlist
        assert "event" in result
        assert "level" in result
        assert "timestamp" in result  # timestamp is essential
        assert "custom_field" in result
        assert "extra_data" not in result

    def test_invalid_configuration(self):
        """Test FieldFilterProcessor with invalid configuration."""
        with pytest.raises(
            ValueError, match="Cannot specify both allowed_fields and blocked_fields"
        ):
            FieldFilterProcessor(allowed_fields={"test"}, blocked_fields={"test2"})


class TestConditionalProcessor:
    """Tests for ConditionalProcessor."""

    def test_condition_true(self):
        """Test conditional processor when condition is true."""

        def always_true_condition(event_dict):
            return True

        def add_marker_processor(logger, method_name, event_dict):
            event_dict["marker"] = "added"
            return event_dict

        processor = ConditionalProcessor(always_true_condition, add_marker_processor)

        event_dict = {"message": "test"}
        result = processor(MagicMock(), "info", event_dict)

        assert result["marker"] == "added"

    def test_condition_false(self):
        """Test conditional processor when condition is false."""

        def always_false_condition(event_dict):
            return False

        def add_marker_processor(logger, method_name, event_dict):
            event_dict["marker"] = "added"
            return event_dict

        processor = ConditionalProcessor(always_false_condition, add_marker_processor)

        event_dict = {"message": "test"}
        result = processor(MagicMock(), "info", event_dict)

        assert "marker" not in result
        assert result["message"] == "test"

    def test_with_else_processor(self):
        """Test conditional processor with else processor."""

        def level_is_error(event_dict):
            return event_dict.get("level") == "ERROR"

        def error_processor(logger, method_name, event_dict):
            event_dict["error_marker"] = True
            return event_dict

        def normal_processor(logger, method_name, event_dict):
            event_dict["normal_marker"] = True
            return event_dict

        processor = ConditionalProcessor(level_is_error, error_processor, normal_processor)

        # Test error case
        error_dict = {"message": "error", "level": "ERROR"}
        result = processor(MagicMock(), "error", error_dict)
        assert result["error_marker"] is True
        assert "normal_marker" not in result

        # Test normal case
        info_dict = {"message": "info", "level": "INFO"}
        result = processor(MagicMock(), "info", info_dict)
        assert result["normal_marker"] is True
        assert "error_marker" not in result


class TestEnhancedExceptionProcessor:
    """Tests for EnhancedExceptionProcessor."""

    def test_no_exception(self):
        """Test processor when no exception is present."""
        processor = EnhancedExceptionProcessor()

        event_dict = {"message": "normal log", "level": "INFO"}
        result = processor(MagicMock(), "info", event_dict)

        # Should return unchanged when no exception
        assert result == event_dict

    def test_exception_processing(self):
        """Test exception processing with actual exception."""
        processor = EnhancedExceptionProcessor()

        try:
            raise ValueError("Test error")
        except Exception:
            exc_info = sys.exc_info()
            event_dict = {"message": "error occurred", "exc_info": exc_info}
            result = processor(MagicMock(), "error", event_dict)

            # Should add exception details (actual format from output)
            assert "exception_type" in result
            assert result["exception_type"] == "ValueError"
            assert result["exception_message"] == "Test error"
            assert "structured_traceback" in result

    def test_preserve_original_traceback(self):
        """Test preserving original traceback."""
        processor = EnhancedExceptionProcessor(preserve_original_traceback=True)

        try:
            raise ValueError("Test error")
        except Exception:
            exc_info = sys.exc_info()
            event_dict = {"message": "error occurred", "exc_info": exc_info}
            result = processor(MagicMock(), "error", event_dict)

            assert "original_traceback" in result
            assert isinstance(result["original_traceback"], str)

    def test_max_frames_limit(self):
        """Test max frames limitation."""
        processor = EnhancedExceptionProcessor(max_frames=2)

        def nested_error():
            def level2():
                def level3():
                    raise ValueError("Deep error")

                level3()

            level2()

        try:
            nested_error()
        except Exception:
            exc_info = sys.exc_info()
            event_dict = {"message": "error occurred", "exc_info": exc_info}
            result = processor(MagicMock(), "error", event_dict)

            frames = result["structured_traceback"]
            # The processor includes an omitted frames marker, so we get max_frames + 1
            # when frames are omitted: first frame, "... N frames omitted ...", last frame
            assert len(frames) <= 3  # max_frames=2 plus omitted marker


class TestAddOpenTelemetrySpans:
    """Tests for add_open_telemetry_spans processor."""

    @patch("corrupt_o11y.logging.processors.opentelemetry.trace")
    def test_no_active_span(self, mock_trace):
        """Test when no active span exists."""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = False
        mock_trace.get_current_span.return_value = mock_span

        event_dict = {"message": "test"}
        result = add_open_telemetry_spans(MagicMock(), "info", event_dict)

        # Should return unchanged when no span
        assert result == event_dict

    @patch("corrupt_o11y.logging.processors.opentelemetry.trace")
    def test_with_active_span(self, mock_trace):
        """Test when active span exists."""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mock_span_context = MagicMock()
        mock_span_context.is_valid = True
        mock_span_context.trace_id = 123456789
        mock_span_context.span_id = 987654321
        mock_span.get_span_context.return_value = mock_span_context
        mock_trace.get_current_span.return_value = mock_span

        event_dict = {"message": "test"}
        result = add_open_telemetry_spans(MagicMock(), "info", event_dict)

        # Should add tracing information in span object
        assert "span" in result
        assert result["span"]["trace_id"] == "000000000000000000000000075bcd15"
        assert result["span"]["span_id"] == "000000003ade68b1"

    @patch("corrupt_o11y.logging.processors.opentelemetry.trace")
    def test_with_non_recording_span(self, mock_trace):
        """Test when span is not recording."""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = False
        mock_trace.get_current_span.return_value = mock_span

        event_dict = {"message": "test"}
        result = add_open_telemetry_spans(MagicMock(), "info", event_dict)

        # Should return unchanged when span not recording
        assert result == event_dict
        # Should not call get_span_context
        mock_span.get_span_context.assert_not_called()

    @patch("corrupt_o11y.logging.processors.opentelemetry.trace")
    def test_with_invalid_span_context(self, mock_trace):
        """Test when span context is invalid."""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mock_span_context = MagicMock()
        mock_span_context.is_valid = False
        mock_span.get_span_context.return_value = mock_span_context
        mock_trace.get_current_span.return_value = mock_span

        event_dict = {"message": "test"}
        result = add_open_telemetry_spans(MagicMock(), "info", event_dict)

        # Should return unchanged when span context is invalid
        assert result == event_dict
        assert "span" not in result
