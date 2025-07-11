import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Self


@dataclass
class ServiceInfo:
    """Service metadata information.

    Attributes:
        name: Name of the service.
        version: Version of the service.
        instance_id: Unique identifier for the service instance.
        commit_sha: Git commit SHA.
        build_time: Build timestamp.
    """

    name: str
    version: str
    instance_id: str
    commit_sha: str
    build_time: str

    @classmethod
    def from_env(cls) -> Self:
        """Create service info from environment variables.

        Environment variables:
            SERVICE_NAME: Name of the service (default: unknown-dev).
            SERVICE_VERSION: Version of the service (default: dev).
            INSTANCE_ID: Instance identifier (default: unknown-dev).
            COMMIT_SHA: Git commit SHA (default: unknown-dev).
            BUILD_TIME: Build timestamp (default: unknown-dev).

        Returns:
            ServiceInfo instance.
        """
        return cls(
            name=os.environ.get("SERVICE_NAME", "unknown-dev"),
            version=os.environ.get("SERVICE_VERSION", "unknown-dev"),
            instance_id=os.environ.get("INSTANCE_ID", "unknown-dev"),
            commit_sha=os.environ.get("COMMIT_SHA", "unknown-dev"),
            build_time=os.environ.get("BUILD_TIME", "unknown-dev"),
        )

    def asdict(self) -> Mapping[str, str]:
        """Convert service info to mapping.

        Returns:
            Mapping representation of service info.
        """
        return {
            "service_name": self.name,
            "version": self.version,
            "instance_id": self.instance_id,
            "commit_sha": self.commit_sha,
            "build_time": self.build_time,
        }
