import os
from dataclasses import dataclass
from typing import Self


@dataclass
class OperationalServerConfig:
    """Configuration for operational HTTP server.

    Attributes:
        host: Host address to bind to.
        port: Port number to bind to.
    """

    host: str
    port: int

    @classmethod
    def from_env(cls) -> Self:
        """Create configuration from environment variables.

        Environment variables:
            OPERATIONAL_HOST: Host address (default: 0.0.0.0).
            OPERATIONAL_PORT: Port number (default: 42069).

        Returns:
            OperationalServerConfig instance.
        """
        return cls(
            host=os.environ.get("OPERATIONAL_HOST", "0.0.0.0"),
            port=int(os.environ.get("OPERATIONAL_PORT", "42069")),
        )
