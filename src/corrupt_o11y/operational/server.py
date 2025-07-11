from collections.abc import Mapping
from typing import Any

import orjson
from aiohttp import web
from prometheus_client import generate_latest

from corrupt_o11y.metrics import MetricsCollector

from .config import OperationalServerConfig
from .status import Status


class OperationalServer:
    """HTTP server providing operational endpoints.

    Provides endpoints for:
    - /health: Liveness check
    - /ready: Readiness check
    - /metrics: Prometheus metrics
    - /info: Service information
    """

    def __init__(  # type: ignore[explicit-any]
        self,
        config: OperationalServerConfig,
        service_info: Mapping[str, Any],
        status: Status,
        metrics: MetricsCollector,
    ) -> None:
        """Initialize operational server.

        Args:
            config: Server configuration.
            service_info: Service information mapping.
            status: Service status tracker.
            metrics: Metrics collector.
        """
        self._config = config
        self._status = status
        self._metrics = metrics
        self._service_info = service_info

        self._app = web.Application()
        self._runner: web.AppRunner | None = None
        self._server_url = ""

    @property
    def server_url(self) -> str:
        """Get the server URL."""
        return self._server_url

    async def _handle_health_check(self, _: web.Request) -> web.Response:
        """Handle health check requests.

        Returns:
            HTTP 200 if alive, 503 if not.
        """
        return web.Response(status=200 if self._status.is_alive else 503)

    async def _handle_readiness_check(self, _: web.Request) -> web.Response:
        """Handle readiness check requests.

        Returns:
            HTTP 200 if ready, 503 if not.
        """
        return web.Response(status=200 if self._status.is_ready else 503)

    async def _handle_metrics(self, _: web.Request) -> web.Response:
        """Handle Prometheus metrics requests.

        Returns:
            Prometheus metrics in text format.
        """
        return web.Response(
            body=generate_latest(self._metrics.registry),
            status=200,
            content_type="text/plain",
            charset="utf-8",
        )

    async def _handle_info(self, _: web.Request) -> web.Response:
        """Handle service info requests.

        Returns:
            Service information as JSON.
        """
        return web.json_response(
            data=self._service_info,
            dumps=lambda x: orjson.dumps(x).decode(),
        )

    def _setup_http_routes(self) -> None:
        """Set up HTTP routes."""
        self._app.router.add_get("/health", self._handle_health_check)
        self._app.router.add_get("/ready", self._handle_readiness_check)
        self._app.router.add_get("/info", self._handle_info)
        self._app.router.add_get("/metrics", self._handle_metrics)

    async def start(self) -> None:
        """Start the operational server."""
        self._setup_http_routes()
        self._runner = web.AppRunner(self._app, access_log=None)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self._config.host, self._config.port)
        await site.start()

        # Set server URL using actual assigned port
        host = self._config.host if self._config.host != "0.0.0.0" else ""

        # Get the actual port from the server if available
        actual_port = self._config.port
        if (
            actual_port == 0
            and site._server  # noqa: SLF001
            and hasattr(site._server, "sockets")  # noqa: SLF001
            and site._server.sockets  # noqa: SLF001
        ):
            actual_port = site._server.sockets[0].getsockname()[1]  # noqa: SLF001

        self._server_url = f"http://{host}:{actual_port}"

    async def close(self) -> None:
        """Close the operational server."""
        if self._runner is not None:
            await self._runner.cleanup()
