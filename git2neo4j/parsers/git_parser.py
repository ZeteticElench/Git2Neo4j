"""Git repository parser using GitPython."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import git
from git import Commit, Repo, Tree

from git2neo4j.models.git_objects import (
    AuthorInfo,
    BlobObject,
    BranchInfo,
    CommitObject,
    GitObjectType,
    RepositoryInfo,
    TagObject,
    TreeEntry,
    TreeEntryMode,
    TreeObject,
)


class GitParser:
    """Parser for extracting Git objects from a repository."""

    def __init__(self, repo_path: str | Path) -> None:
        """Initialize Git parser.

        Args:
            repo_path: Path to Git repository

        Raises:
            git.exc.InvalidGitRepositoryError: If path is not a valid Git repository
        """
        self.repo_path = Path(repo_path).resolve()
        self.repo = Repo(str(self.repo_path))

    def get_repository_info(self) -> RepositoryInfo:
        """Get repository metadata.

        Returns:
            Repository information including branches and remotes
        """
        branches = list(self._parse_branches())

        head_sha: str | None = None
        current_branch: str | None = None

        if not self.repo.head.is_detached:
            head_sha = str(self.repo.head.commit.hexsha)
            current_branch = str(self.repo.active_branch.name)
        elif self.repo.head.is_valid():
            head_sha = str(self.repo.head.commit.hexsha)

        remotes = {remote.name: remote.url for remote in self.repo.remotes}

        return RepositoryInfo(
            path=str(self.repo_path),
            head_sha=head_sha,
            current_branch=current_branch,
            branches=branches,
            remotes=remotes,
            is_bare=self.repo.bare,
        )

    def get_all_commits(self) -> Iterator[CommitObject]:
        """Get all commits in the repository.

        Yields:
            Commit objects in topological order
        """
        seen: set[str] = set()

        # Get all refs (branches, tags, etc.)
        for ref in self.repo.refs:
            try:
                for commit in self.repo.iter_commits(ref, topo_order=True):
                    commit_sha = str(commit.hexsha)
                    if commit_sha not in seen:
                        seen.add(commit_sha)
                        yield self._parse_commit(commit)
            except (git.exc.GitCommandError, ValueError):
                # Skip invalid refs
                continue

    def get_commit(self, sha: str) -> CommitObject:
        """Get a specific commit by SHA.

        Args:
            sha: Commit SHA-1 hash

        Returns:
            Commit object

        Raises:
            ValueError: If commit not found
        """
        try:
            commit = self.repo.commit(sha)
            return self._parse_commit(commit)
        except (git.exc.BadName, ValueError) as e:
            raise ValueError(f"Commit not found: {sha}") from e

    def get_tree(self, sha: str) -> TreeObject:
        """Get a specific tree by SHA.

        Args:
            sha: Tree SHA-1 hash

        Returns:
            Tree object

        Raises:
            ValueError: If tree not found
        """
        try:
            tree = self.repo.tree(sha)
            return self._parse_tree(tree, sha)
        except (git.exc.BadName, ValueError) as e:
            raise ValueError(f"Tree not found: {sha}") from e

    def get_blob(self, sha: str, path: str | None = None) -> BlobObject:
        """Get a specific blob by SHA.

        Args:
            sha: Blob SHA-1 hash
            path: Optional file path

        Returns:
            Blob object

        Raises:
            ValueError: If blob not found
        """
        try:
            # Convert hex SHA to binary for ODB
            import binascii
            sha_bin = binascii.unhexlify(sha)

            obj = self.repo.odb.info(sha_bin)
            blob = self.repo.odb.stream(sha_bin)
            content = blob.read()

            return BlobObject(
                sha=sha,
                type=GitObjectType.BLOB,
                size=obj.size,
                content=content,
                path=path,
            )
        except (git.exc.BadName, ValueError, binascii.Error) as e:
            raise ValueError(f"Blob not found: {sha}") from e

    def get_all_trees_for_commit(self, commit_sha: str) -> Iterator[TreeObject]:
        """Get all trees reachable from a commit.

        Args:
            commit_sha: Commit SHA to start from

        Yields:
            Tree objects recursively
        """
        commit = self.repo.commit(commit_sha)
        seen: set[str] = set()

        def traverse_tree(tree: Tree, tree_sha: str) -> Iterator[TreeObject]:
            if tree_sha in seen:
                return
            seen.add(tree_sha)

            yield self._parse_tree(tree, tree_sha)

            for item in tree.traverse():
                if item.type == "tree":
                    item_sha = str(item.hexsha)
                    if item_sha not in seen:
                        yield from traverse_tree(item, item_sha)

        yield from traverse_tree(commit.tree, str(commit.tree.hexsha))

    def get_all_tags(self) -> Iterator[TagObject]:
        """Get all annotated tags in the repository.

        Yields:
            Tag objects
        """
        for tag_ref in self.repo.tags:
            try:
                tag = tag_ref.tag
                if tag is not None:  # Annotated tag
                    yield self._parse_tag(tag)
            except (AttributeError, ValueError):
                # Lightweight tag, skip
                continue

    def _parse_branches(self) -> Iterator[BranchInfo]:
        """Parse all branches in the repository.

        Yields:
            Branch information
        """
        # Local branches
        for branch in self.repo.heads:
            is_head = False
            if not self.repo.head.is_detached:
                is_head = branch.name == self.repo.active_branch.name

            yield BranchInfo(
                name=branch.name,
                commit_sha=str(branch.commit.hexsha),
                is_remote=False,
                remote_name=None,
                is_head=is_head,
            )

        # Remote branches
        for remote in self.repo.remotes:
            for ref in remote.refs:
                # Skip HEAD refs
                if ref.name.endswith("/HEAD"):
                    continue

                branch_name = ref.name.split("/", 1)[1]
                yield BranchInfo(
                    name=branch_name,
                    commit_sha=str(ref.commit.hexsha),
                    is_remote=True,
                    remote_name=remote.name,
                    is_head=False,
                )

    def _parse_commit(self, commit: Commit) -> CommitObject:
        """Parse a Git commit object.

        Args:
            commit: GitPython Commit object

        Returns:
            Parsed commit object
        """
        author = self._parse_author(
            commit.author.name,
            commit.author.email,
            commit.authored_datetime,
        )

        committer = self._parse_author(
            commit.committer.name,
            commit.committer.email,
            commit.committed_datetime,
        )

        parent_shas = [str(p.hexsha) for p in commit.parents]

        # Extract GPG signature if present
        gpg_signature: str | None = None
        if hasattr(commit, "gpgsig") and commit.gpgsig:
            gpg_signature = commit.gpgsig

        return CommitObject(
            sha=str(commit.hexsha),
            type=GitObjectType.COMMIT,
            size=commit.size,
            tree_sha=str(commit.tree.hexsha),
            parent_shas=parent_shas,
            author=author,
            committer=committer,
            message=commit.message,
            encoding=commit.encoding or "utf-8",
            gpg_signature=gpg_signature,
        )

    def _parse_tree(self, tree: Tree, sha: str) -> TreeObject:
        """Parse a Git tree object.

        Args:
            tree: GitPython Tree object
            sha: Tree SHA

        Returns:
            Parsed tree object
        """
        entries: list[TreeEntry] = []

        for item in tree:
            # Map Git mode to TreeEntryMode
            mode_str = f"{item.mode:06o}"
            try:
                mode = TreeEntryMode(mode_str)
            except ValueError:
                # Default to file mode if unknown
                mode = TreeEntryMode.FILE

            # Determine type
            obj_type = (
                GitObjectType.TREE if item.type == "tree" else GitObjectType.BLOB
            )

            entry = TreeEntry(
                mode=mode,
                type=obj_type,
                sha=str(item.hexsha),
                path=item.path,
            )
            entries.append(entry)

        return TreeObject(
            sha=sha,
            type=GitObjectType.TREE,
            size=0,  # Git doesn't expose tree size easily
            entries=entries,
        )

    def _parse_tag(self, tag: git.TagObject) -> TagObject:
        """Parse a Git tag object.

        Args:
            tag: GitPython Tag object

        Returns:
            Parsed tag object
        """
        tagger: AuthorInfo | None = None
        if hasattr(tag, "tagger") and tag.tagger:
            tagger = self._parse_author(
                tag.tagger.name,
                tag.tagger.email,
                tag.tagged_date,
            )

        # Determine target type
        target_type_map = {
            "commit": GitObjectType.COMMIT,
            "tree": GitObjectType.TREE,
            "blob": GitObjectType.BLOB,
            "tag": GitObjectType.TAG,
        }
        target_type = target_type_map.get(tag.object.type, GitObjectType.COMMIT)

        return TagObject(
            sha=str(tag.hexsha),
            type=GitObjectType.TAG,
            size=0,  # Size not easily available
            name=tag.tag,
            target_sha=str(tag.object.hexsha),
            target_type=target_type,
            tagger=tagger,
            message=tag.message or "",
            gpg_signature=None,  # GPG signature handling would go here
        )

    def _parse_author(
        self, name: str, email: str, timestamp: datetime | int
    ) -> AuthorInfo:
        """Parse author information.

        Args:
            name: Author name
            email: Author email
            timestamp: Commit timestamp (datetime or Unix timestamp)

        Returns:
            Author information
        """
        if isinstance(timestamp, int):
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        else:
            dt = timestamp

        # Extract timezone offset
        if dt.tzinfo:
            offset = dt.strftime("%z")
            if not offset:
                offset = "+0000"
        else:
            offset = "+0000"

        return AuthorInfo(
            name=name,
            email=email,
            timestamp=dt,
            timezone=offset,
        )
