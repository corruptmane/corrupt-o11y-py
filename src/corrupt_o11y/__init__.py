"""corrupt o11y - A comprehensive observability library for Python applications."""

from . import logging, metrics, operational, tracing
from .__meta__ import version as __version__
from .metadata import ServiceInfo

__all__ = [
    "ServiceInfo",
    "__version__",
    "logging",
    "metrics",
    "operational",
    "tracing",
]
