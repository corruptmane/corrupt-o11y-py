from dataclasses import dataclass


@dataclass
class Status:
    """Service status tracking.

    Attributes:
        is_ready: Whether the service is ready to accept requests.
        is_alive: Whether the service is alive (for health checks).
    """

    is_ready: bool = False
    is_alive: bool = True
