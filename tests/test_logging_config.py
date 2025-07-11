import logging

import pytest

from corrupt_o11y.logging import LoggingConfig


class TestLoggingConfig:
    """Tests for LoggingConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = LoggingConfig(level=logging.INFO, as_json=False, integrate_tracing=False)

        assert config.level == logging.INFO
        assert config.as_json is False
        assert config.integrate_tracing is False
        assert config.colors is True
        assert config.exception_max_frames == 20
        assert config.exception_preserve_traceback is True
        assert config.exception_extract_location is True
        assert config.exception_skip_library_frames is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = LoggingConfig(
            level=logging.DEBUG,
            as_json=True,
            integrate_tracing=True,
            colors=False,
            exception_max_frames=50,
            exception_preserve_traceback=False,
            exception_extract_location=False,
            exception_skip_library_frames=False,
        )

        assert config.level == logging.DEBUG
        assert config.as_json is True
        assert config.integrate_tracing is True
        assert config.colors is False
        assert config.exception_max_frames == 50
        assert config.exception_preserve_traceback is False
        assert config.exception_extract_location is False
        assert config.exception_skip_library_frames is False

    def test_from_env_defaults(self, monkeypatch):
        """Test LoggingConfig.from_env with default values."""
        # Clear all relevant env vars
        env_vars = [
            "LOG_LEVEL",
            "LOG_AS_JSON",
            "LOG_TRACING",
            "LOG_COLORS",
            "LOG_EXCEPTION_MAX_FRAMES",
            "LOG_EXCEPTION_PRESERVE_TRACEBACK",
            "LOG_EXCEPTION_EXTRACT_LOCATION",
            "LOG_EXCEPTION_SKIP_LIBRARY_FRAMES",
        ]
        for var in env_vars:
            monkeypatch.delenv(var, raising=False)

        config = LoggingConfig.from_env()

        assert config.level == logging.INFO
        assert config.as_json is False
        assert config.integrate_tracing is False
        assert config.colors is True

    def test_from_env_custom(self, monkeypatch):
        """Test LoggingConfig.from_env with custom values."""
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("LOG_AS_JSON", "true")
        monkeypatch.setenv("LOG_TRACING", "yes")
        monkeypatch.setenv("LOG_COLORS", "false")
        monkeypatch.setenv("LOG_EXCEPTION_MAX_FRAMES", "100")

        config = LoggingConfig.from_env()

        assert config.level == logging.DEBUG
        assert config.as_json is True
        assert config.integrate_tracing is True
        assert config.colors is False
        assert config.exception_max_frames == 100

    def test_from_env_invalid_log_level(self, monkeypatch):
        """Test LoggingConfig.from_env with invalid log level."""
        monkeypatch.setenv("LOG_LEVEL", "INVALID")

        with pytest.raises(ValueError, match="Invalid LOG_LEVEL"):
            LoggingConfig.from_env()

    def test_from_env_invalid_max_frames(self, monkeypatch):
        """Test LoggingConfig.from_env with invalid max frames."""
        monkeypatch.setenv("LOG_EXCEPTION_MAX_FRAMES", "not_a_number")

        with pytest.raises(ValueError, match="Invalid LOG_EXCEPTION_MAX_FRAMES"):
            LoggingConfig.from_env()

    def test_from_env_max_frames_too_small(self, monkeypatch):
        """Test LoggingConfig.from_env with max frames too small."""
        monkeypatch.setenv("LOG_EXCEPTION_MAX_FRAMES", "0")

        with pytest.raises(ValueError, match="exception_max_frames must be at least 1"):
            LoggingConfig.from_env()

    def test_log_level_mapping(self, monkeypatch):
        """Test various log level string mappings."""
        test_cases = [
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
            ("ERROR", logging.ERROR),
            ("CRITICAL", logging.CRITICAL),
            ("debug", logging.DEBUG),
            ("info", logging.INFO),
        ]

        for level_str, expected_level in test_cases:
            monkeypatch.setenv("LOG_LEVEL", level_str)
            config = LoggingConfig.from_env()
            assert config.level == expected_level
