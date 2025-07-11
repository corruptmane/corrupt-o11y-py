import re
from typing import Any

from structlog.typing import EventDict, WrappedLogger


class PIIRedactionProcessor:
    """Redact personally identifiable information from log events.

    This processor scans string values in log events and replaces
    patterns that look like PII with redacted placeholders.
    """

    def __init__(
        self,
        patterns: dict[str, str] | None = None,
        redact_keys: set[str] | None = None,
        case_sensitive: bool = False,
    ) -> None:
        """Initialize the PII redaction processor.

        Args:
            patterns: Custom regex patterns for PII detection {name: pattern}.
            redact_keys: Set of keys to always redact regardless of content.
            case_sensitive: Whether pattern matching should be case sensitive.
        """
        self.patterns = patterns or {
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "ssn": r"\b\d{3}-?\d{2}-?\d{4}\b",
            "phone": r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b",
            "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
            "ip_address": r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
        }

        self.redact_keys = redact_keys or {
            "password",
            "passwd",
            "secret",
            "token",
            "key",
            "auth",
            "authorization",
            "credential",
            "credentials",
            "api_key",
            "access_token",
            "refresh_token",
            "private_key",
            "cert",
            "certificate",
            "signature",
            "hash",
        }

        self.case_sensitive = case_sensitive

        # Compile regex patterns
        flags = 0 if case_sensitive else re.IGNORECASE
        self.compiled_patterns = {
            name: re.compile(pattern, flags) for name, pattern in self.patterns.items()
        }

    def _should_redact_key(self, key: str) -> bool:
        """Check if a key should be redacted based on its name."""
        if self.case_sensitive:
            return key in self.redact_keys
        return key.lower() in {k.lower() for k in self.redact_keys}

    def _redact_string(self, text: str) -> str:
        """Apply PII redaction patterns to a string."""
        for pii_type, pattern in self.compiled_patterns.items():
            text = pattern.sub(f"<{pii_type.upper()}>", text)
        return text

    def _redact_value(self, key: str, value: Any) -> Any:  # type: ignore[explicit-any]  # noqa: ANN401
        """Redact a single value, handling different types."""
        # Always redact sensitive keys
        if self._should_redact_key(key):
            return "<REDACTED>"

        # Process strings for PII patterns
        if isinstance(value, str):
            return self._redact_string(value)

        # Recursively process dictionaries
        if isinstance(value, dict):
            return {k: self._redact_value(k, v) for k, v in value.items()}

        # Process lists and tuples
        if isinstance(value, list | tuple):
            redacted_items = [self._redact_value("", item) for item in value]
            return type(value)(redacted_items)

        # Return other types unchanged
        return value

    def __call__(
        self,
        logger: WrappedLogger,  # noqa: ARG002
        method_name: str,  # noqa: ARG002
        event_dict: EventDict,
    ) -> EventDict:
        """Process PII redaction for the event dictionary."""
        redacted_dict = {}

        for key, value in event_dict.items():
            redacted_dict[key] = self._redact_value(key, value)

        return redacted_dict
