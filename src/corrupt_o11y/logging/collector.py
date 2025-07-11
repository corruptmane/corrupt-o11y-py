import logging
from collections.abc import Callable, Iterator
from typing import Any, Self

import orjson
import structlog
from structlog.typing import Processor

from .config import LoggingConfig
from .processors import (
    EnhancedExceptionProcessor,
    add_open_telemetry_spans,
    make_processor_chain_safe,
)


class ProcessorChain:
    """A chain of logging processors that can be modified."""

    def __init__(self, processors: list[Processor] | None = None) -> None:
        """Initialize the processor chain.

        Args:
            processors: Initial list of processors, defaults to empty list.
        """
        self._processors: list[Processor] = processors or []

    def append(self, processor: Processor) -> Self:
        """Add a processor to the end of the chain.

        Args:
            processor: Processor to append.

        Returns:
            Self for method chaining.
        """
        self._processors.append(processor)
        return self

    def insert(self, index: int, processor: Processor) -> Self:
        """Insert a processor at a specific position.

        Args:
            index: Position to insert at.
            processor: Processor to insert.

        Returns:
            Self for method chaining.
        """
        self._processors.insert(index, processor)
        return self

    def clear(self) -> Self:
        """Remove all processors from the chain.

        Returns:
            Self for method chaining.
        """
        self._processors.clear()
        return self

    def replace(self, processors: list[Processor]) -> Self:
        """Replace all processors with a new list.

        Args:
            processors: New list of processors.

        Returns:
            Self for method chaining.
        """
        self._processors = processors.copy()
        return self

    def remove(self, processor: Processor) -> Self:
        """Remove a specific processor from the chain.

        Args:
            processor: Processor to remove.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If processor is not found in the chain.
        """
        self._processors.remove(processor)
        return self

    def to_list(self) -> list[Processor]:
        """Get a copy of the processor list.

        Returns:
            Copy of the internal processor list.
        """
        return self._processors.copy()

    def __len__(self) -> int:
        """Get the number of processors in the chain."""
        return len(self._processors)

    def __iter__(self) -> Iterator[Processor]:
        """Iterate over processors in the chain."""
        return iter(self._processors)

    def __repr__(self) -> str:
        """String representation of the processor chain."""
        return f"ProcessorChain({len(self._processors)} processors)"


class LoggingCollector:
    """Configurable logging system with processor chains."""

    def __init__(self, config: LoggingConfig, safe_processors: bool = True) -> None:
        """Initialize the logging collector with sensible defaults.

        Args:
            config: Configuration for the logging system.
            safe_processors: Whether to wrap processors with error handling.
        """
        self._config = config
        self._safe_processors = safe_processors

        # Early processors (enrichment - run before user pre-processing)
        early_processors: list[Processor] = [
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.ExtraAdder(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.CallsiteParameterAdder(
                [
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                    structlog.processors.CallsiteParameter.MODULE,
                ]
            ),
        ]
        self._early_processing = ProcessorChain(early_processors)

        # Pre-processing chain (user-defined early cleanup, filtering)
        self._preprocessing = ProcessorChain()

        # Core processing chain (opinionated processing logic)
        core_processors: list[Processor] = []

        if config.integrate_tracing:
            core_processors.append(add_open_telemetry_spans)

        if config.as_json:
            core_processors.append(
                EnhancedExceptionProcessor(
                    preserve_original_traceback=config.exception_preserve_traceback,
                    max_frames=config.exception_max_frames,
                    extract_error_location=config.exception_extract_location,
                    skip_library_frames=config.exception_skip_library_frames,
                )
            )

        self._processing = ProcessorChain(core_processors)

        # Post-processing chain (external integrations, final formatting)
        self._postprocessing = ProcessorChain()

    def early_processing(self) -> ProcessorChain:
        """Get the early processing chain (read-only).

        Early processors handle basic enrichment and run before user pre-processing.
        This chain is managed by the library and should not be modified.

        Returns:
            Early processing chain with basic enrichment processors.
        """
        return self._early_processing

    def preprocessing(self) -> ProcessorChain:
        """Get the pre-processing chain for user-defined processors.

        This chain runs after early enrichment but before core processing.
        Ideal for PII redaction, field filtering, and custom enrichment.

        Returns:
            Pre-processing chain for user-defined processors.
        """
        return self._preprocessing

    def processing(self) -> ProcessorChain:
        """Get the core processing chain.

        This chain contains opinionated processing logic like exception
        transformation and OpenTelemetry integration.

        Returns:
            Core processing chain with main logging logic.
        """
        return self._processing

    def postprocessing(self) -> ProcessorChain:
        """Get the post-processing chain for late processors.

        This chain runs after all core processing and is ideal for
        external integrations and final formatting.

        Returns:
            Post-processing chain for external integrations and formatting.
        """
        return self._postprocessing

    def build_processor_list(self) -> list[Processor]:
        """Build the complete processor list from all chains.

        Returns:
            Combined list of all processors from all chains.
        """
        processors: list[Processor] = []
        processors.extend(self._early_processing.to_list())
        processors.extend(self._preprocessing.to_list())
        processors.extend(self._processing.to_list())
        processors.extend(self._postprocessing.to_list())

        # Wrap processors with error handling if enabled
        if self._safe_processors:
            processors = make_processor_chain_safe(processors)

        return processors

    def _json_serializer(  # type: ignore[explicit-any]
        self,
        data: Any,  # noqa: ANN401
        default: Callable[[Any], Any] | None,
    ) -> str:
        """Serialize data to JSON string.

        Args:
            data: Data to serialize.
            default: Additional serializer function.

        Returns:
            JSON string.
        """
        return orjson.dumps(data, default=default).decode()

    def configure(self) -> None:
        """Configure structlog with the current processor chains.

        Args:
            level: Logging level to use.
        """
        # Build the complete processor list
        common_processors = self.build_processor_list()

        final_processor: Processor
        # Determine final processor based on JSON configuration
        if self._config.as_json:
            final_processor = structlog.processors.JSONRenderer(serializer=self._json_serializer)
        else:
            final_processor = structlog.dev.ConsoleRenderer(colors=self._config.colors)

        # Set up structlog processors for internal use
        structlog_processors: list[Processor] = [
            structlog.processors.StackInfoRenderer(),
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ]

        # Set up logging processors for stdlib integration
        logging_processors = (
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            final_processor,
        )

        # Configure stdlib logging
        handler = logging.StreamHandler()
        handler.set_name("default")
        handler.setLevel(self._config.level)
        console_formatter = structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=common_processors,
            processors=logging_processors,
        )
        handler.setFormatter(console_formatter)

        logging.basicConfig(handlers=[handler], level=self._config.level)

        # Configure structlog
        structlog.configure(
            processors=common_processors + structlog_processors,
            logger_factory=structlog.WriteLoggerFactory(),
            wrapper_class=structlog.make_filtering_bound_logger(self._config.level),
            cache_logger_on_first_use=True,
        )
