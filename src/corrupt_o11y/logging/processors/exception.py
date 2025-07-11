import sys
import traceback
from collections.abc import Mapping
from pathlib import Path
from types import TracebackType
from typing import Any

from structlog.typing import EventDict, WrappedLogger


class EnhancedExceptionProcessor:
    """Enhanced exception processor that extracts detailed error information."""

    def __init__(
        self,
        preserve_original_traceback: bool = True,
        max_frames: int = 20,
        extract_error_location: bool = True,
        skip_library_frames: bool = True,
    ) -> None:
        """Initialize the exception processor.

        Args:
            preserve_original_traceback: Keep original traceback in separate key
            max_frames: Maximum number of frames to include
            extract_error_location: Extract specific error location info
            skip_library_frames: Skip library/framework frames in root cause detection
        """
        self.preserve_original_traceback = preserve_original_traceback
        self.max_frames = max_frames
        self.extract_error_location = extract_error_location
        self.skip_library_frames = skip_library_frames

    def _is_library_frame(self, filename: str) -> bool:
        """Detect if frame is from a library/framework.

        Args:
            filename: Path to the source file.

        Returns:
            True if frame appears to be from a library/framework.
        """
        library_indicators = [
            "/site-packages/",
            "/dist-packages/",  # pip
            "/.venv/",
            "/venv/",
            "/env/",  # virtualenv
            "/conda/",
            "/miniconda/",
            "/anaconda/",  # conda
            "/.cache/pypoetry/",  # poetry
            "/usr/lib/",
            "/usr/local/lib/",  # system
            "<frozen",  # builtin
        ]
        return any(indicator in filename for indicator in library_indicators)

    def _extract_error_location(  # type: ignore[explicit-any]
        self,
        exc_info: tuple[type[BaseException] | None, BaseException | None, TracebackType | None],
    ) -> Mapping[str, Any]:
        """Extract specific error location information."""
        _, __, exc_traceback = exc_info

        location_info: dict[str, Any] = {}  # type: ignore[explicit-any]

        if exc_traceback:
            # Get the last frame (where error occurred)
            tb = exc_traceback
            while tb.tb_next:
                tb = tb.tb_next

            frame = tb.tb_frame
            location_info.update(
                {
                    "error_file": Path(frame.f_code.co_filename).name,
                    "error_function": frame.f_code.co_name,
                    "error_line": tb.tb_lineno,
                    "error_module": frame.f_globals.get("__name__", "unknown"),
                }
            )

            # Find root cause (first frame in your code, not libraries)
            stack_summary = traceback.extract_tb(exc_traceback)
            location_info["stack_depth"] = len(stack_summary)

            for frame_summary in stack_summary:
                filename = frame_summary.filename
                # Skip library/framework frames if enabled
                if self.skip_library_frames and self._is_library_frame(filename):
                    continue

                location_info.update(
                    {
                        "root_cause_file": Path(filename).name,
                        "root_cause_function": frame_summary.name,
                        "root_cause_line": frame_summary.lineno,
                    }
                )
                break

        return location_info

    def __call__(
        self,
        logger: WrappedLogger,  # noqa: ARG002
        method_name: str,  # noqa: ARG002
        event_dict: EventDict,
    ) -> EventDict:
        """Process exception information in the event dictionary."""
        if "exc_info" not in event_dict or not event_dict["exc_info"]:
            return event_dict

        exc_info = event_dict["exc_info"]
        if exc_info is True:
            exc_info = sys.exc_info()

        if not exc_info or not exc_info[0]:
            return event_dict

        exc_type, exc_value, exc_traceback = exc_info
        assert exc_type is not None
        assert exc_value is not None

        # Basic exception information
        event_dict["exception_type"] = exc_type.__name__
        event_dict["exception_message"] = str(exc_value)
        event_dict["exception_module"] = exc_type.__module__

        # Extract error location if enabled
        if self.extract_error_location:
            location_info = self._extract_error_location(exc_info)
            event_dict.update(location_info)

        # Remove the original exc_info to avoid duplication
        del event_dict["exc_info"]

        # Format traceback
        if not exc_traceback:
            return event_dict

        if self.preserve_original_traceback:
            # Keep original traceback as string for human reading
            event_dict["original_traceback"] = "".join(
                traceback.format_exception(exc_type, exc_value, exc_traceback)
            )

        # Create structured traceback for machine processing
        stack_summary = traceback.extract_tb(exc_traceback)

        # Limit frames if specified
        if self.max_frames and len(stack_summary) > self.max_frames:
            # Keep first few and last few frames
            keep_start = self.max_frames // 2
            keep_end = self.max_frames - keep_start

            frames: list[str | traceback.FrameSummary] = list(stack_summary[:keep_start])
            if len(stack_summary) > self.max_frames:
                frames.append(f"... {len(stack_summary) - self.max_frames} frames omitted ...")
            frames.extend(list(stack_summary[-keep_end:]))
        else:
            frames = list(stack_summary)

        # Convert to structured format
        structured_frames: list[dict[str, str | int | None]] = []
        for frame in frames:
            if isinstance(frame, str):  # Our omitted message
                structured_frames.append({"info": frame})
            else:
                frame_info = {
                    "filename": Path(frame.filename).name,
                    "full_filename": frame.filename,
                    "function": frame.name,
                    "line": frame.lineno,
                    "code": frame.line,
                }

                structured_frames.append(frame_info)

        event_dict["structured_traceback"] = structured_frames

        return event_dict
