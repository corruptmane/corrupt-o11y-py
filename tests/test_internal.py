import pytest

from corrupt_o11y._internal import env_bool


class TestEnvBool:
    """Tests for env_bool function."""

    def test_true_values(self, monkeypatch):
        """Test parsing true values."""
        true_values = ["true", "t", "1", "yes", "y", "on", "TRUE", "True", "Y", "YES"]

        for value in true_values:
            monkeypatch.setenv("TEST_BOOL", value)
            assert env_bool("TEST_BOOL") is True

    def test_false_values(self, monkeypatch):
        """Test parsing false values."""
        false_values = ["false", "f", "0", "no", "n", "off", "FALSE", "False", "N", "NO"]

        for value in false_values:
            monkeypatch.setenv("TEST_BOOL", value)
            assert env_bool("TEST_BOOL") is False

    def test_default_true(self, monkeypatch):
        """Test default value when env var not set."""
        monkeypatch.delenv("TEST_BOOL", raising=False)
        assert env_bool("TEST_BOOL", "true") is True

    def test_default_false(self, monkeypatch):
        """Test default value when env var not set."""
        monkeypatch.delenv("TEST_BOOL", raising=False)
        assert env_bool("TEST_BOOL", "false") is False

    def test_invalid_value(self, monkeypatch):
        """Test invalid boolean value raises ValueError."""
        monkeypatch.setenv("TEST_BOOL", "invalid")

        with pytest.raises(ValueError, match="Invalid boolean value for TEST_BOOL"):
            env_bool("TEST_BOOL")

    def test_invalid_default(self):
        """Test invalid default value raises ValueError."""
        with pytest.raises(ValueError, match="Invalid boolean value for TEST_BOOL"):
            env_bool("TEST_BOOL", "invalid_default")

    def test_case_insensitive(self, monkeypatch):
        """Test that parsing is case insensitive."""
        monkeypatch.setenv("TEST_BOOL", "TrUe")
        assert env_bool("TEST_BOOL") is True

        monkeypatch.setenv("TEST_BOOL", "FaLsE")
        assert env_bool("TEST_BOOL") is False
