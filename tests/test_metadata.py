from corrupt_o11y.metadata import ServiceInfo


class TestServiceInfo:
    """Tests for ServiceInfo class."""

    def test_basic_creation(self):
        """Test basic ServiceInfo creation."""
        service = ServiceInfo(
            name="test-service",
            version="1.0.0",
            instance_id="test-instance",
            commit_sha="abc123",
            build_time="2023-01-01T00:00:00Z",
        )

        assert service.name == "test-service"
        assert service.version == "1.0.0"
        assert service.instance_id == "test-instance"
        assert service.commit_sha == "abc123"
        assert service.build_time == "2023-01-01T00:00:00Z"

    def test_minimal_creation(self):
        """Test ServiceInfo creation with all required fields."""
        service = ServiceInfo(
            name="test-service",
            version="1.0.0",
            instance_id="test-instance",
            commit_sha="abc123",
            build_time="2023-01-01T00:00:00Z",
        )

        assert service.name == "test-service"
        assert service.version == "1.0.0"
        assert service.instance_id == "test-instance"
        assert service.commit_sha == "abc123"
        assert service.build_time == "2023-01-01T00:00:00Z"

    def test_from_env_with_all_vars(self, monkeypatch):
        """Test ServiceInfo.from_env with all environment variables."""
        monkeypatch.setenv("SERVICE_NAME", "env-service")
        monkeypatch.setenv("SERVICE_VERSION", "2.0.0")
        monkeypatch.setenv("INSTANCE_ID", "env-instance")
        monkeypatch.setenv("COMMIT_SHA", "def456")
        monkeypatch.setenv("BUILD_TIME", "2023-06-01T12:00:00Z")

        service = ServiceInfo.from_env()

        assert service.name == "env-service"
        assert service.version == "2.0.0"
        assert service.instance_id == "env-instance"
        assert service.commit_sha == "def456"
        assert service.build_time == "2023-06-01T12:00:00Z"

    def test_from_env_with_defaults(self, monkeypatch):
        """Test ServiceInfo.from_env with default values."""
        # Clear all relevant env vars
        for var in ["SERVICE_NAME", "SERVICE_VERSION", "INSTANCE_ID", "COMMIT_SHA", "BUILD_TIME"]:
            monkeypatch.delenv(var, raising=False)

        service = ServiceInfo.from_env()

        assert service.name == "unknown-dev"
        assert service.version == "unknown-dev"
        assert service.instance_id == "unknown-dev"
        assert service.commit_sha == "unknown-dev"
        assert service.build_time == "unknown-dev"

    def test_from_env_mixed(self, monkeypatch):
        """Test ServiceInfo.from_env with some env vars set."""
        monkeypatch.setenv("SERVICE_NAME", "partial-service")
        monkeypatch.setenv("SERVICE_VERSION", "1.5.0")
        monkeypatch.delenv("INSTANCE_ID", raising=False)
        monkeypatch.delenv("COMMIT_SHA", raising=False)
        monkeypatch.delenv("BUILD_TIME", raising=False)

        service = ServiceInfo.from_env()

        assert service.name == "partial-service"
        assert service.version == "1.5.0"
        assert service.instance_id == "unknown-dev"
        assert service.commit_sha == "unknown-dev"
        assert service.build_time == "unknown-dev"

    def test_asdict(self):
        """Test ServiceInfo.asdict method."""
        service = ServiceInfo(
            name="dict-service",
            version="1.0.0",
            instance_id="dict-instance",
            commit_sha="abc123",
            build_time="2023-01-01T00:00:00Z",
        )

        result = service.asdict()

        expected = {
            "service_name": "dict-service",
            "version": "1.0.0",
            "instance_id": "dict-instance",
            "commit_sha": "abc123",
            "build_time": "2023-01-01T00:00:00Z",
        }

        assert result == expected

    def test_asdict_complete_fields(self):
        """Test ServiceInfo.asdict with all fields."""
        service = ServiceInfo(
            name="dict-service",
            version="1.0.0",
            instance_id="dict-instance",
            commit_sha="xyz789",
            build_time="2023-02-01T00:00:00Z",
        )

        result = service.asdict()

        expected = {
            "service_name": "dict-service",
            "version": "1.0.0",
            "instance_id": "dict-instance",
            "commit_sha": "xyz789",
            "build_time": "2023-02-01T00:00:00Z",
        }

        assert result == expected

    def test_defaults_consistency(self, monkeypatch):
        """Test that default values are consistent."""
        monkeypatch.delenv("INSTANCE_ID", raising=False)

        service1 = ServiceInfo.from_env()
        service2 = ServiceInfo.from_env()

        # All values should be "unknown-dev" when not set
        assert service1.instance_id == "unknown-dev"
        assert service2.instance_id == "unknown-dev"
        assert service1.instance_id == service2.instance_id
