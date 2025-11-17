"""Sync Neo4j database changes back to Git repository."""

from datetime import datetime
from pathlib import Path
from typing import Any

from git import Actor, Repo
from neo4j import GraphDatabase, Neo4jDriver

from git2neo4j.parsers.git_parser import GitParser


class Neo4jToGitSync:
    """Synchronize Neo4j changes back to Git repository.

    This allows Git operations performed in Neo4j (via Cypher)
    to be mirrored back to the actual Git repository.
    """

    def __init__(
        self,
        repo_path: str | Path,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "password",
        neo4j_database: str = "neo4j",
    ) -> None:
        """Initialize Neo4j to Git sync engine.

        Args:
            repo_path: Path to Git repository
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            neo4j_database: Neo4j database name
        """
        self.repo_path = Path(repo_path).resolve()
        self.repo = Repo(str(self.repo_path))
        self.parser = GitParser(self.repo_path)

        # Initialize Neo4j driver
        self.driver: Neo4jDriver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password),
        )
        self.database = neo4j_database

    def __enter__(self) -> "Neo4jToGitSync":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    def close(self) -> None:
        """Close Neo4j driver connection."""
        if self.driver:
            self.driver.close()

    def create_branch_from_neo4j(
        self,
        branch_name: str,
        from_commit_sha: str | None = None,
    ) -> str:
        """Create a Git branch from a Neo4j branch node.

        Args:
            branch_name: Name of branch to create
            from_commit_sha: SHA of commit to branch from (None = HEAD)

        Returns:
            SHA of commit the branch points to

        Raises:
            ValueError: If commit not found
        """
        # Get commit from Neo4j
        if from_commit_sha is None:
            # Use current HEAD
            from_commit_sha = str(self.repo.head.commit.hexsha)

        # Verify commit exists in both Neo4j and Git
        commit_exists = self._verify_commit_exists(from_commit_sha)
        if not commit_exists:
            raise ValueError(f"Commit not found: {from_commit_sha}")

        # Create branch in Git
        try:
            commit = self.repo.commit(from_commit_sha)
            new_branch = self.repo.create_head(branch_name, commit)

            # Update Neo4j to reflect the new branch
            self._create_branch_node_in_neo4j(branch_name, from_commit_sha)

            return from_commit_sha

        except Exception as e:
            raise ValueError(f"Failed to create branch: {e}") from e

    def delete_branch_from_neo4j(self, branch_name: str) -> bool:
        """Delete a Git branch that was removed from Neo4j.

        Args:
            branch_name: Name of branch to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if branch exists in Git
            if branch_name in self.repo.heads:
                self.repo.delete_head(branch_name, force=False)

            # Remove from Neo4j
            self._delete_branch_node_from_neo4j(branch_name)

            return True

        except Exception:
            return False

    def tag_commit_from_neo4j(
        self,
        tag_name: str,
        commit_sha: str,
        message: str = "",
        tagger_name: str | None = None,
        tagger_email: str | None = None,
    ) -> str:
        """Create a Git tag from a Neo4j tag node.

        Args:
            tag_name: Tag name
            commit_sha: Commit SHA to tag
            message: Tag message
            tagger_name: Tagger name
            tagger_email: Tagger email

        Returns:
            Tag object SHA

        Raises:
            ValueError: If commit not found
        """
        # Verify commit exists
        commit_exists = self._verify_commit_exists(commit_sha)
        if not commit_exists:
            raise ValueError(f"Commit not found: {commit_sha}")

        try:
            commit = self.repo.commit(commit_sha)

            # Create tagger actor
            if tagger_name and tagger_email:
                tagger = Actor(tagger_name, tagger_email)
            else:
                tagger = None

            # Create annotated tag
            if message:
                tag = self.repo.create_tag(
                    tag_name,
                    ref=commit,
                    message=message,
                    # Note: GitPython doesn't directly support tagger
                )
            else:
                # Lightweight tag
                tag = self.repo.create_tag(tag_name, ref=commit)

            return str(tag.commit.hexsha)

        except Exception as e:
            raise ValueError(f"Failed to create tag: {e}") from e

    # Helper methods

    def _verify_commit_exists(self, commit_sha: str) -> bool:
        """Verify commit exists in both Neo4j and Git.

        Args:
            commit_sha: Commit SHA to verify

        Returns:
            True if exists in both, False otherwise
        """
        # Check Git
        try:
            self.repo.commit(commit_sha)
        except Exception:
            return False

        # Check Neo4j
        query = "MATCH (c:Commit {sha: $sha}) RETURN count(c) > 0 as exists"
        with self.driver.session(database=self.database) as session:
            result = session.run(query, sha=commit_sha)
            record = result.single()
            return record["exists"] if record else False

    def _create_branch_node_in_neo4j(
        self, branch_name: str, commit_sha: str
    ) -> None:
        """Create branch node in Neo4j.

        Args:
            branch_name: Branch name
            commit_sha: Commit SHA branch points to
        """
        query = """
        MATCH (c:Commit {sha: $commit_sha})
        MERGE (b:Branch {full_name: $branch_name})
        SET b.name = $branch_name,
            b.commit_sha = $commit_sha,
            b.is_remote = false,
            b.is_head = false
        MERGE (b)-[:POINTS_TO {ref_type: 'branch'}]->(c)
        """

        with self.driver.session(database=self.database) as session:
            session.run(
                query,
                branch_name=branch_name,
                commit_sha=commit_sha,
            )

    def _delete_branch_node_from_neo4j(self, branch_name: str) -> None:
        """Delete branch node from Neo4j.

        Args:
            branch_name: Branch name to delete
        """
        query = """
        MATCH (b:Branch {name: $branch_name})
        DETACH DELETE b
        """

        with self.driver.session(database=self.database) as session:
            session.run(query, branch_name=branch_name)

    def sync_branches_from_neo4j(self) -> dict[str, int]:
        """Sync all branches from Neo4j to Git.

        This creates Git branches for any branches that exist in Neo4j
        but not in Git.

        Returns:
            Statistics about branches synced
        """
        stats = {"created": 0, "updated": 0, "errors": 0}

        # Get all branches from Neo4j
        query = """
        MATCH (b:Branch)
        WHERE b.is_remote = false
        RETURN b.name as name, b.commit_sha as commit_sha
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query)

            for record in result:
                branch_name = record["name"]
                commit_sha = record["commit_sha"]

                try:
                    # Check if branch exists in Git
                    if branch_name not in self.repo.heads:
                        # Create branch
                        commit = self.repo.commit(commit_sha)
                        self.repo.create_head(branch_name, commit)
                        stats["created"] += 1
                    else:
                        # Update branch pointer if different
                        branch = self.repo.heads[branch_name]
                        if str(branch.commit.hexsha) != commit_sha:
                            commit = self.repo.commit(commit_sha)
                            branch.commit = commit
                            stats["updated"] += 1

                except Exception:
                    stats["errors"] += 1

        return stats
