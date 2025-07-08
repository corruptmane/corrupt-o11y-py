from collections.abc import AsyncGenerator

import aiohttp
import pytest
import pytest_asyncio
from prometheus_client import Counter

from corrupt_o11y.metadata import ServiceInfo
from corrupt_o11y.metrics import MetricsCollector
from corrupt_o11y.operational import OperationalServer, OperationalServerConfig, Status


@pytest.fixture
def service_info() -> ServiceInfo:
    return ServiceInfo(
        name="test-service",
        version="1.0.0",
        instance_id="test-instance",
        commit_sha="abc123",
        build_time="2024-01-01T00:00:00Z",
    )


@pytest.fixture
def metrics_collector() -> MetricsCollector:
    # Each test gets its own collector with its own registry
    return MetricsCollector()


@pytest.fixture
def status() -> Status:
    return Status()


@pytest.fixture
def server_config() -> OperationalServerConfig:
    return OperationalServerConfig(host="127.0.0.1", port=0)  # Port 0 = random available port


@pytest_asyncio.fixture
async def operational_server(
    service_info: ServiceInfo,
    metrics_collector: MetricsCollector,
    status: Status,
    server_config: OperationalServerConfig,
) -> AsyncGenerator[OperationalServer, None]:
    metrics_collector.create_service_info_metric_from_service_info(service_info)
    # Metric is already registered with collector's registry

    server = OperationalServer(server_config, service_info.asdict(), status, metrics_collector)
    await server.start()
    yield server
    await server.close()


@pytest_asyncio.fixture
async def client_session() -> AsyncGenerator[aiohttp.ClientSession, None]:
    timeout = aiohttp.ClientTimeout(total=30, connect=5)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        yield session


@pytest.fixture
def server_url(operational_server: OperationalServer) -> str:
    return operational_server.server_url


class TestOperationalServerEndpoints:
    """Test HTTP endpoints of the operational server."""

    @pytest.mark.asyncio()
    async def test_health_endpoint_alive(
        self,
        server_url: str,
        operational_server: OperationalServer,
        client_session: aiohttp.ClientSession,
    ) -> None:
        """Test health endpoint returns 200 when alive."""
        operational_server._status.is_alive = True

        async with client_session.get(f"{server_url}/health") as response:
            assert response.status == 200

    @pytest.mark.asyncio()
    async def test_health_endpoint_not_alive(
        self,
        server_url: str,
        operational_server: OperationalServer,
        client_session: aiohttp.ClientSession,
    ) -> None:
        """Test health endpoint returns 503 when not alive."""
        operational_server._status.is_alive = False

        async with client_session.get(f"{server_url}/health") as response:
            assert response.status == 503

    @pytest.mark.asyncio()
    async def test_ready_endpoint_ready(
        self,
        server_url: str,
        operational_server: OperationalServer,
        client_session: aiohttp.ClientSession,
    ) -> None:
        """Test ready endpoint returns 200 when ready."""
        operational_server._status.is_ready = True

        async with client_session.get(f"{server_url}/ready") as response:
            assert response.status == 200

    @pytest.mark.asyncio()
    async def test_ready_endpoint_not_ready(
        self,
        server_url: str,
        operational_server: OperationalServer,
        client_session: aiohttp.ClientSession,
    ) -> None:
        """Test ready endpoint returns 503 when not ready."""
        operational_server._status.is_ready = False

        async with client_session.get(f"{server_url}/ready") as response:
            assert response.status == 503

    @pytest.mark.asyncio()
    async def test_metrics_endpoint(
        self, server_url: str, client_session: aiohttp.ClientSession
    ) -> None:
        """Test metrics endpoint returns Prometheus metrics."""
        async with client_session.get(f"{server_url}/metrics") as response:
            assert response.status == 200
            assert response.headers["Content-Type"] == "text/plain; charset=utf-8"

            content = await response.text()
            assert "service_info" in content
            assert "test-service" in content
            assert "1.0.0" in content

    @pytest.mark.asyncio()
    async def test_info_endpoint(
        self, server_url: str, service_info: ServiceInfo, client_session: aiohttp.ClientSession
    ) -> None:
        """Test info endpoint returns service information as JSON."""
        async with client_session.get(f"{server_url}/info") as response:
            assert response.status == 200
            assert "application/json" in response.headers["Content-Type"]

            data = await response.json()
            assert data["service_name"] == service_info.name
            assert data["version"] == service_info.version
            assert data["instance_id"] == service_info.instance_id
            assert data["commit_sha"] == service_info.commit_sha
            assert data["build_time"] == service_info.build_time


class TestOperationalServerLifecycle:
    """Test operational server startup and shutdown."""

    @pytest.mark.asyncio()
    async def test_server_startup_and_shutdown(
        self,
        service_info: ServiceInfo,
        metrics_collector: MetricsCollector,
        status: Status,
        server_config: OperationalServerConfig,
        client_session: aiohttp.ClientSession,
    ) -> None:
        """Test server can start and stop cleanly."""
        server = OperationalServer(server_config, service_info.asdict(), status, metrics_collector)

        # Start server
        await server.start()
        assert server._runner is not None

        # Verify server is accessible
        url = f"{server.server_url}/health"
        async with client_session.get(url) as response:
            assert response.status == 200

        # Stop server
        await server.close()

    @pytest.mark.asyncio()
    async def test_multiple_servers_different_ports(
        self,
        service_info: ServiceInfo,
        metrics_collector: MetricsCollector,
        status: Status,
        client_session: aiohttp.ClientSession,
    ) -> None:
        """Test multiple servers can run on different ports."""
        config1 = OperationalServerConfig(host="127.0.0.1", port=0)
        config2 = OperationalServerConfig(host="127.0.0.1", port=0)

        server1 = OperationalServer(config1, service_info.asdict(), status, metrics_collector)
        server2 = OperationalServer(config2, service_info.asdict(), status, metrics_collector)

        try:
            await server1.start()
            await server2.start()

            # Verify both servers are accessible
            assert server1.server_url != server2.server_url  # Different URLs

            async with client_session.get(f"{server1.server_url}/health") as response:
                assert response.status == 200
            async with client_session.get(f"{server2.server_url}/health") as response:
                assert response.status == 200
        finally:
            await server1.close()
            await server2.close()


class TestEndToEndObservability:
    """Test end-to-end observability integration."""

    @pytest.mark.asyncio()
    async def test_metrics_collection_and_export(
        self,
        service_info: ServiceInfo,
        metrics_collector: MetricsCollector,
        status: Status,
        server_config: OperationalServerConfig,
        client_session: aiohttp.ClientSession,
    ) -> None:
        """Test metrics are collected and exported correctly."""
        # Create service info metric
        metrics_collector.create_service_info_metric_from_service_info(service_info)
        # Metric is already registered with collector's registry

        # Create custom metric
        test_counter = Counter("test_requests_total", "Test counter", registry=None)
        test_counter.inc(5)
        metrics_collector.register("test_counter", test_counter)

        # Start server
        server = OperationalServer(server_config, service_info.asdict(), status, metrics_collector)
        await server.start()

        try:
            # Fetch metrics
            async with client_session.get(f"{server.server_url}/metrics") as response:
                assert response.status == 200
                content = await response.text()

                # Verify service info metric
                assert "service_info" in content
                assert f'service="{service_info.name}"' in content
                assert f'version="{service_info.version}"' in content
                assert f'instance="{service_info.instance_id}"' in content
                assert f'commit="{service_info.commit_sha}"' in content

                # Verify custom metric
                assert "test_requests_total" in content
                assert "5.0" in content
        finally:
            await server.close()

    @pytest.mark.asyncio()
    async def test_service_info_consistency(
        self,
        service_info: ServiceInfo,
        metrics_collector: MetricsCollector,
        status: Status,
        server_config: OperationalServerConfig,
        client_session: aiohttp.ClientSession,
    ) -> None:
        """Test service info is consistent across endpoints."""
        metrics_collector.create_service_info_metric_from_service_info(service_info)
        # Metric is already registered with collector's registry

        server = OperationalServer(server_config, service_info.asdict(), status, metrics_collector)
        await server.start()

        try:
            # Get service info from /info endpoint
            async with client_session.get(f"{server.server_url}/info") as response:
                info_data = await response.json()

            # Get service info from /metrics endpoint
            async with client_session.get(f"{server.server_url}/metrics") as response:
                metrics_content = await response.text()

            # Verify consistency
            assert f'service="{info_data["service_name"]}"' in metrics_content
            assert f'version="{info_data["version"]}"' in metrics_content
            assert f'instance="{info_data["instance_id"]}"' in metrics_content
            assert f'commit="{info_data["commit_sha"]}"' in metrics_content
        finally:
            await server.close()
