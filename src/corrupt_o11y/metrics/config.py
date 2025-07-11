import os
from dataclasses import dataclass
from typing import Self

from corrupt_o11y._internal import env_bool


@dataclass
class MetricsConfig:
    """Configuration for Prometheus metrics collection.

    Attributes:
        enable_gc_collector: Whether to enable garbage collection metrics.
        enable_platform_collector: Whether to enable platform metrics.
        enable_process_collector: Whether to enable process metrics.
        metric_prefix: Optional prefix for all metrics.
    """

    enable_gc_collector: bool = True
    enable_platform_collector: bool = True
    enable_process_collector: bool = True
    metric_prefix: str = ""

    @classmethod
    def from_env(cls) -> Self:
        """Create configuration from environment variables.

        Environment variables:
            METRICS_ENABLE_GC: Enable garbage collection metrics (default: true).
            METRICS_ENABLE_PLATFORM: Enable platform metrics (default: true).
            METRICS_ENABLE_PROCESS: Enable process metrics (default: true).
            METRICS_PREFIX: Prefix for all metrics (default: empty).

        Returns:
            MetricsConfig instance.

        Raises:
            ValueError: If any environment variable has an invalid value.
        """
        return cls(
            enable_gc_collector=env_bool("METRICS_ENABLE_GC", "true"),
            enable_platform_collector=env_bool("METRICS_ENABLE_PLATFORM", "true"),
            enable_process_collector=env_bool("METRICS_ENABLE_PROCESS", "true"),
            metric_prefix=os.environ.get("METRICS_PREFIX", ""),
        )
