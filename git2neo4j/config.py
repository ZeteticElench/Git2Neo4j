"""Configuration management for Git2Neo4j."""

from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Neo4jConfig(BaseSettings):
    """Neo4j database configuration."""

    model_config = SettingsConfigDict(
        env_prefix="NEO4J_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j connection URI",
    )
    user: str = Field(
        default="neo4j",
        description="Neo4j username",
    )
    password: str = Field(
        default="password",
        description="Neo4j password",
    )
    database: str = Field(
        default="neo4j",
        description="Neo4j database name",
    )
    max_connection_lifetime: int = Field(
        default=3600,
        description="Max connection lifetime in seconds",
    )
    max_connection_pool_size: int = Field(
        default=50,
        description="Max connection pool size",
    )
    connection_acquisition_timeout: int = Field(
        default=60,
        description="Connection acquisition timeout in seconds",
    )


class GitConfig(BaseSettings):
    """Git repository configuration."""

    model_config = SettingsConfigDict(
        env_prefix="GIT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    repo_path: str = Field(
        default=".",
        description="Path to Git repository",
    )

    @field_validator("repo_path")
    @classmethod
    def validate_repo_path(cls, v: str) -> str:
        """Validate repository path exists."""
        path = Path(v).resolve()
        if not path.exists():
            raise ValueError(f"Repository path does not exist: {path}")
        return str(path)


class SyncConfig(BaseSettings):
    """Synchronization configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SYNC_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    batch_size: int = Field(
        default=100,
        ge=1,
        description="Batch size for bulk operations",
    )
    max_workers: int = Field(
        default=4,
        ge=1,
        description="Max workers for parallel processing",
    )
    sync_blobs: bool = Field(
        default=False,
        description="Whether to sync blob metadata (can be large)",
    )
    sync_trees: bool = Field(
        default=True,
        description="Whether to sync tree objects",
    )
    create_indexes: bool = Field(
        default=True,
        description="Whether to create indexes and constraints",
    )


class Config(BaseSettings):
    """Main application configuration."""

    neo4j: Neo4jConfig = Field(default_factory=Neo4jConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    sync: SyncConfig = Field(default_factory=SyncConfig)

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            neo4j=Neo4jConfig(),
            git=GitConfig(),
            sync=SyncConfig(),
        )
