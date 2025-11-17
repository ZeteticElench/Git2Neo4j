"""Neo4j node and relationship schema definitions for Git objects."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Neo4jNode(BaseModel):
    """Base class for Neo4j nodes."""

    @property
    def label(self) -> str:
        """Get the Neo4j node label."""
        return self.__class__.__name__.replace("Node", "")

    def to_neo4j_properties(self) -> dict[str, Any]:
        """Convert to Neo4j properties dictionary."""
        return self.model_dump(exclude_none=True, exclude={"label"})

    class Config:
        """Pydantic config."""

        frozen = True


class CommitNode(Neo4jNode):
    """Neo4j node representing a Git commit."""

    sha: str = Field(..., description="Commit SHA-1 hash")
    tree_sha: str = Field(..., description="Root tree SHA")
    message: str = Field(..., description="Commit message")
    author_name: str = Field(..., description="Author name")
    author_email: str = Field(..., description="Author email")
    author_timestamp: datetime = Field(..., description="Author timestamp")
    author_timezone: str = Field(..., description="Author timezone")
    committer_name: str = Field(..., description="Committer name")
    committer_email: str = Field(..., description="Committer email")
    committer_timestamp: datetime = Field(..., description="Committer timestamp")
    committer_timezone: str = Field(..., description="Committer timezone")
    encoding: str = Field(default="utf-8", description="Message encoding")
    gpg_signature: str | None = Field(default=None, description="GPG signature")
    parent_count: int = Field(..., ge=0, description="Number of parents")

    @property
    def is_merge(self) -> bool:
        """Check if this is a merge commit."""
        return self.parent_count > 1

    @property
    def is_initial(self) -> bool:
        """Check if this is an initial commit."""
        return self.parent_count == 0


class TreeNode(Neo4jNode):
    """Neo4j node representing a Git tree."""

    sha: str = Field(..., description="Tree SHA-1 hash")
    size: int = Field(..., ge=0, description="Tree size in bytes")
    entry_count: int = Field(..., ge=0, description="Number of entries")
    file_count: int = Field(default=0, ge=0, description="Number of files")
    dir_count: int = Field(default=0, ge=0, description="Number of subdirectories")


class BlobNode(Neo4jNode):
    """Neo4j node representing a Git blob."""

    sha: str = Field(..., description="Blob SHA-1 hash")
    size: int = Field(..., ge=0, description="Blob size in bytes")
    path: str | None = Field(default=None, description="File path")
    is_binary: bool = Field(default=False, description="Whether blob is binary")
    # Note: We don't store actual content in Neo4j, just metadata
    # Content can be retrieved from Git when needed


class TagNode(Neo4jNode):
    """Neo4j node representing a Git tag."""

    sha: str = Field(..., description="Tag SHA-1 hash")
    name: str = Field(..., description="Tag name")
    target_sha: str = Field(..., description="Target object SHA")
    target_type: str = Field(..., description="Target object type")
    message: str = Field(default="", description="Tag message")
    tagger_name: str | None = Field(default=None, description="Tagger name")
    tagger_email: str | None = Field(default=None, description="Tagger email")
    tagger_timestamp: datetime | None = Field(default=None, description="Tag timestamp")
    tagger_timezone: str | None = Field(default=None, description="Tagger timezone")
    gpg_signature: str | None = Field(default=None, description="GPG signature")


class BranchNode(Neo4jNode):
    """Neo4j node representing a Git branch."""

    name: str = Field(..., description="Branch name")
    full_name: str = Field(..., description="Full branch name with remote")
    commit_sha: str = Field(..., description="Commit SHA branch points to")
    is_remote: bool = Field(default=False, description="Whether this is a remote branch")
    remote_name: str | None = Field(default=None, description="Remote name")
    is_head: bool = Field(default=False, description="Whether this is current HEAD")


class AuthorNode(Neo4jNode):
    """Neo4j node representing a Git author/committer."""

    name: str = Field(..., description="Author name")
    email: str = Field(..., description="Author email")
    commit_count: int = Field(default=0, ge=0, description="Number of commits")

    @property
    def unique_id(self) -> str:
        """Get unique identifier for author."""
        return f"{self.name} <{self.email}>"


class RepositoryNode(Neo4jNode):
    """Neo4j node representing a Git repository."""

    path: str = Field(..., description="Repository path")
    name: str = Field(..., description="Repository name")
    head_sha: str | None = Field(default=None, description="HEAD commit SHA")
    current_branch: str | None = Field(default=None, description="Current branch")
    is_bare: bool = Field(default=False, description="Whether repository is bare")
    last_synced: datetime | None = Field(default=None, description="Last sync timestamp")
    commit_count: int = Field(default=0, ge=0, description="Total commits")
    branch_count: int = Field(default=0, ge=0, description="Total branches")
    tag_count: int = Field(default=0, ge=0, description="Total tags")


class Neo4jRelationship(BaseModel):
    """Base class for Neo4j relationships."""

    @property
    def type(self) -> str:
        """Get the Neo4j relationship type."""
        return self.__class__.__name__.replace("Relationship", "").upper()

    def to_neo4j_properties(self) -> dict[str, Any]:
        """Convert to Neo4j properties dictionary."""
        return self.model_dump(exclude_none=True, exclude={"type"})

    class Config:
        """Pydantic config."""

        frozen = True


class ParentRelationship(Neo4jRelationship):
    """Relationship from commit to parent commit."""

    parent_index: int = Field(..., ge=0, description="Index of parent (0 for first parent)")


class TreeRelationship(Neo4jRelationship):
    """Relationship from commit to root tree."""

    pass


class HasEntryRelationship(Neo4jRelationship):
    """Relationship from tree to entry (blob or subtree)."""

    path: str = Field(..., description="Entry path")
    mode: str = Field(..., description="Entry file mode")
    entry_type: str = Field(..., description="Entry type (tree or blob)")


class PointsToRelationship(Neo4jRelationship):
    """Relationship from branch/tag to commit."""

    ref_type: str = Field(..., description="Reference type (branch or tag)")


class AuthoredByRelationship(Neo4jRelationship):
    """Relationship from commit to author."""

    role: str = Field(..., description="Role (author or committer)")


class TracksRelationship(Neo4jRelationship):
    """Relationship from repository to branch."""

    pass


# Index and constraint definitions for Neo4j
NEO4J_CONSTRAINTS = [
    "CREATE CONSTRAINT commit_sha IF NOT EXISTS FOR (c:Commit) REQUIRE c.sha IS UNIQUE",
    "CREATE CONSTRAINT tree_sha IF NOT EXISTS FOR (t:Tree) REQUIRE t.sha IS UNIQUE",
    "CREATE CONSTRAINT blob_sha IF NOT EXISTS FOR (b:Blob) REQUIRE b.sha IS UNIQUE",
    "CREATE CONSTRAINT tag_sha IF NOT EXISTS FOR (t:Tag) REQUIRE t.sha IS UNIQUE",
    "CREATE CONSTRAINT branch_full_name IF NOT EXISTS FOR (b:Branch) REQUIRE b.full_name IS UNIQUE",
    "CREATE CONSTRAINT author_email IF NOT EXISTS FOR (a:Author) REQUIRE a.email IS UNIQUE",
    "CREATE CONSTRAINT repo_path IF NOT EXISTS FOR (r:Repository) REQUIRE r.path IS UNIQUE",
]

NEO4J_INDEXES = [
    "CREATE INDEX commit_timestamp IF NOT EXISTS FOR (c:Commit) ON (c.author_timestamp)",
    "CREATE INDEX commit_author_email IF NOT EXISTS FOR (c:Commit) ON (c.author_email)",
    "CREATE INDEX commit_message IF NOT EXISTS FOR (c:Commit) ON (c.message)",
    "CREATE INDEX branch_name IF NOT EXISTS FOR (b:Branch) ON (b.name)",
    "CREATE INDEX blob_path IF NOT EXISTS FOR (b:Blob) ON (b.path)",
    "CREATE INDEX author_name IF NOT EXISTS FOR (a:Author) ON (a.name)",
]
