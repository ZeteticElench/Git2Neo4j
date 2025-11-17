"""Strongly-typed Pydantic models for Git objects."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class GitObjectType(str, Enum):
    """Git object types."""

    COMMIT = "commit"
    TREE = "tree"
    BLOB = "blob"
    TAG = "tag"


class GitObject(BaseModel):
    """Base class for all Git objects."""

    sha: str = Field(..., description="SHA-1 hash of the object")
    type: GitObjectType = Field(..., description="Type of Git object")
    size: int = Field(..., ge=0, description="Size of the object in bytes")

    @field_validator("sha")
    @classmethod
    def validate_sha(cls, v: str) -> str:
        """Validate SHA-1 hash format."""
        if not v or len(v) != 40:
            raise ValueError(f"Invalid SHA-1 hash: {v}")
        if not all(c in "0123456789abcdef" for c in v.lower()):
            raise ValueError(f"SHA-1 hash contains invalid characters: {v}")
        return v.lower()

    class Config:
        """Pydantic config."""

        frozen = True


class AuthorInfo(BaseModel):
    """Git author/committer information."""

    name: str = Field(..., min_length=1, description="Author name")
    email: str = Field(..., description="Author email")
    timestamp: datetime = Field(..., description="Author timestamp")
    timezone: str = Field(default="+0000", description="Timezone offset")

    class Config:
        """Pydantic config."""

        frozen = True


class CommitObject(GitObject):
    """Git commit object with full metadata."""

    type: GitObjectType = Field(default=GitObjectType.COMMIT, description="Object type")
    tree_sha: str = Field(..., description="SHA of the root tree")
    parent_shas: list[str] = Field(default_factory=list, description="SHAs of parent commits")
    author: AuthorInfo = Field(..., description="Commit author")
    committer: AuthorInfo = Field(..., description="Commit committer")
    message: str = Field(..., description="Commit message")
    encoding: str = Field(default="utf-8", description="Commit message encoding")
    gpg_signature: str | None = Field(default=None, description="GPG signature if present")

    @field_validator("tree_sha")
    @classmethod
    def validate_tree_sha(cls, v: str) -> str:
        """Validate tree SHA format."""
        if not v or len(v) != 40:
            raise ValueError(f"Invalid tree SHA: {v}")
        return v.lower()

    @field_validator("parent_shas")
    @classmethod
    def validate_parent_shas(cls, v: list[str]) -> list[str]:
        """Validate parent SHA formats."""
        return [sha.lower() for sha in v if len(sha) == 40]

    @property
    def is_merge_commit(self) -> bool:
        """Check if this is a merge commit."""
        return len(self.parent_shas) > 1

    @property
    def is_initial_commit(self) -> bool:
        """Check if this is an initial commit (no parents)."""
        return len(self.parent_shas) == 0


class TreeEntryMode(str, Enum):
    """Git tree entry file modes."""

    DIR = "040000"  # Directory (tree)
    FILE = "100644"  # Regular file
    EXECUTABLE = "100755"  # Executable file
    SYMLINK = "120000"  # Symbolic link
    GITLINK = "160000"  # Git submodule


class TreeEntry(BaseModel):
    """Entry in a Git tree (file or subdirectory)."""

    mode: TreeEntryMode = Field(..., description="File mode")
    type: GitObjectType = Field(..., description="Entry type (tree or blob)")
    sha: str = Field(..., description="SHA of the object")
    path: str = Field(..., min_length=1, description="File/directory path")

    @field_validator("sha")
    @classmethod
    def validate_sha(cls, v: str) -> str:
        """Validate SHA format."""
        if not v or len(v) != 40:
            raise ValueError(f"Invalid SHA: {v}")
        return v.lower()

    @property
    def is_directory(self) -> bool:
        """Check if entry is a directory."""
        return self.mode == TreeEntryMode.DIR

    @property
    def is_executable(self) -> bool:
        """Check if entry is executable."""
        return self.mode == TreeEntryMode.EXECUTABLE

    @property
    def is_symlink(self) -> bool:
        """Check if entry is a symlink."""
        return self.mode == TreeEntryMode.SYMLINK

    @property
    def is_submodule(self) -> bool:
        """Check if entry is a submodule."""
        return self.mode == TreeEntryMode.GITLINK

    class Config:
        """Pydantic config."""

        frozen = True


class TreeObject(GitObject):
    """Git tree object (directory snapshot)."""

    type: GitObjectType = Field(default=GitObjectType.TREE, description="Object type")
    entries: list[TreeEntry] = Field(default_factory=list, description="Tree entries")

    @property
    def file_count(self) -> int:
        """Count of files in this tree."""
        return sum(1 for e in self.entries if e.type == GitObjectType.BLOB)

    @property
    def dir_count(self) -> int:
        """Count of subdirectories in this tree."""
        return sum(1 for e in self.entries if e.type == GitObjectType.TREE)


class BlobObject(GitObject):
    """Git blob object (file content)."""

    type: GitObjectType = Field(default=GitObjectType.BLOB, description="Object type")
    content: bytes = Field(..., description="Blob content")
    path: str | None = Field(default=None, description="File path (if known)")

    @property
    def is_binary(self) -> bool:
        """Check if blob contains binary data."""
        # Simple heuristic: check for null bytes
        return b"\x00" in self.content[:8192]

    @property
    def text_content(self) -> str | None:
        """Get text content if blob is text."""
        if self.is_binary:
            return None
        try:
            return self.content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                return self.content.decode("latin-1")
            except UnicodeDecodeError:
                return None

    class Config:
        """Pydantic config."""

        frozen = False  # Allow path to be set later


class TagObject(GitObject):
    """Git tag object (annotated tag)."""

    type: GitObjectType = Field(default=GitObjectType.TAG, description="Object type")
    name: str = Field(..., min_length=1, description="Tag name")
    target_sha: str = Field(..., description="SHA of tagged object")
    target_type: GitObjectType = Field(..., description="Type of tagged object")
    tagger: AuthorInfo | None = Field(default=None, description="Tag creator")
    message: str = Field(default="", description="Tag message")
    gpg_signature: str | None = Field(default=None, description="GPG signature if present")

    @field_validator("target_sha")
    @classmethod
    def validate_target_sha(cls, v: str) -> str:
        """Validate target SHA format."""
        if not v or len(v) != 40:
            raise ValueError(f"Invalid target SHA: {v}")
        return v.lower()


class BranchInfo(BaseModel):
    """Git branch reference information."""

    name: str = Field(..., min_length=1, description="Branch name")
    commit_sha: str = Field(..., description="SHA of commit branch points to")
    is_remote: bool = Field(default=False, description="Whether this is a remote branch")
    remote_name: str | None = Field(default=None, description="Remote name if remote branch")
    is_head: bool = Field(default=False, description="Whether this is the current HEAD")

    @field_validator("commit_sha")
    @classmethod
    def validate_commit_sha(cls, v: str) -> str:
        """Validate commit SHA format."""
        if not v or len(v) != 40:
            raise ValueError(f"Invalid commit SHA: {v}")
        return v.lower()

    @property
    def full_name(self) -> str:
        """Get full branch name including remote."""
        if self.is_remote and self.remote_name:
            return f"{self.remote_name}/{self.name}"
        return self.name

    class Config:
        """Pydantic config."""

        frozen = True


class RepositoryInfo(BaseModel):
    """Git repository metadata."""

    path: str = Field(..., description="Path to repository")
    head_sha: str | None = Field(default=None, description="SHA of HEAD commit")
    current_branch: str | None = Field(default=None, description="Current branch name")
    branches: list[BranchInfo] = Field(default_factory=list, description="Repository branches")
    remotes: dict[str, str] = Field(
        default_factory=dict, description="Remote names and URLs"
    )
    is_bare: bool = Field(default=False, description="Whether repository is bare")

    class Config:
        """Pydantic config."""

        frozen = False  # Allow updates
