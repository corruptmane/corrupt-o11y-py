from collections.abc import MutableMapping
from typing import Any

from structlog.typing import EventDict, WrappedLogger


class FieldFilterProcessor:
    """Filter log event fields using allowlist or blocklist approach.

    This processor gives you fine-grained control over which fields
    appear in your log events, useful for reducing log verbosity or
    ensuring sensitive fields don't leak.
    """

    def __init__(
        self,
        allowed_fields: set[str] | None = None,
        blocked_fields: set[str] | None = None,
        preserve_essential: bool = True,
    ) -> None:
        """Initialize the field filter processor.

        Args:
            allowed_fields: Set of fields to keep (allowlist mode).
                          If provided, only these fields will be kept.
            blocked_fields: Set of fields to remove (blocklist mode).
                          Ignored if allowed_fields is provided.
            preserve_essential: Whether to always preserve essential fields
                              (event, level, timestamp) even in allowlist mode.
        """
        if allowed_fields is not None and blocked_fields is not None:
            msg = "Cannot specify both allowed_fields and blocked_fields"
            raise ValueError(msg)

        self.allowed_fields = allowed_fields
        self.blocked_fields = blocked_fields or set()
        self.preserve_essential = preserve_essential

        # Essential fields that should typically be preserved
        self.essential_fields = {"event", "level", "timestamp", "logger"}

    def _should_keep_field(self, field_name: str) -> bool:
        """Determine if a field should be kept based on filtering rules."""
        # Always preserve essential fields if configured
        if self.preserve_essential and field_name in self.essential_fields:
            return True

        # Allowlist mode - keep only specified fields
        if self.allowed_fields is not None:
            return field_name in self.allowed_fields

        # Blocklist mode - remove blocked fields
        return field_name not in self.blocked_fields

    def __call__(
        self,
        logger: WrappedLogger,  # noqa: ARG002
        method_name: str,  # noqa: ARG002
        event_dict: EventDict,
    ) -> EventDict:
        """Process field filtering for the event dictionary."""
        return {k: v for k, v in event_dict.items() if self._should_keep_field(k)}


class NestedFieldFilterProcessor:
    """Advanced field filter that can filter nested dictionary fields.

    This processor allows filtering fields using dot notation paths,
    enabling filtering of nested structures in complex log events.
    """

    def __init__(
        self,
        allowed_paths: set[str] | None = None,
        blocked_paths: set[str] | None = None,
        preserve_essential: bool = True,
    ) -> None:
        """Initialize the nested field filter processor.

        Args:
            allowed_paths: Set of dot-notation paths to keep (e.g., {"user.id", "request.method"}).
            blocked_paths: Set of dot-notation paths to remove.
            preserve_essential: Whether to preserve essential top-level fields.
        """
        if allowed_paths is not None and blocked_paths is not None:
            msg = "Cannot specify both allowed_paths and blocked_paths"
            raise ValueError(msg)

        self.allowed_paths = allowed_paths
        self.blocked_paths = blocked_paths or set()
        self.preserve_essential = preserve_essential
        self.essential_fields = {"event", "level", "timestamp", "logger"}

    def _get_nested_value(  # type: ignore[explicit-any]
        self,
        data: MutableMapping[str, Any],
        path: str,
    ) -> Any:  # noqa: ANN401
        """Get a value from nested dictionary using dot notation."""
        keys = path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current

    def _set_nested_value(  # type: ignore[explicit-any]
        self,
        data: MutableMapping[str, Any],
        path: str,
        value: Any,  # noqa: ANN401
    ) -> None:
        """Set a value in nested dictionary using dot notation."""
        keys = path.split(".")
        current = data

        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set the final value
        current[keys[-1]] = value

    def _should_keep_path(self, path: str) -> bool:
        """Determine if a path should be kept based on filtering rules."""
        # Preserve essential top-level fields
        if self.preserve_essential and "." not in path and path in self.essential_fields:
            return True

        # Allowlist mode
        if self.allowed_paths is not None:
            return path in self.allowed_paths

        # Blocklist mode
        return path not in self.blocked_paths

    def _get_all_paths(  # type: ignore[explicit-any]
        self,
        data: MutableMapping[str, Any],
        prefix: str = "",
    ) -> set[str]:
        """Get all possible dot-notation paths from a nested dictionary."""
        paths = set()

        for key, value in data.items():
            current_path = f"{prefix}.{key}" if prefix else key
            paths.add(current_path)

            if isinstance(value, dict):
                paths.update(self._get_all_paths(value, current_path))

        return paths

    def __call__(
        self,
        logger: WrappedLogger,  # noqa: ARG002
        method_name: str,  # noqa: ARG002
        event_dict: EventDict,
    ) -> EventDict:
        """Process nested field filtering for the event dictionary."""
        all_paths = self._get_all_paths(event_dict)
        filtered_dict: MutableMapping[str, Any] = {}  # type: ignore[explicit-any]

        for path in all_paths:
            if self._should_keep_path(path):
                value = self._get_nested_value(event_dict, path)
                if value is not None:
                    self._set_nested_value(filtered_dict, path, value)

        return filtered_dict
