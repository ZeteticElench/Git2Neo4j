"""Sync Git repositories to Neo4j database."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase, ManagedTransaction, Neo4jDriver
from neo4j.exceptions import ServiceUnavailable

from git2neo4j.models.git_objects import (
    BranchInfo,
    CommitObject,
    RepositoryInfo,
    TagObject,
    TreeObject,
)
from git2neo4j.models.neo4j_schema import (
    AuthorNode,
    BlobNode,
    BranchNode,
    CommitNode,
    NEO4J_CONSTRAINTS,
    NEO4J_INDEXES,
    RepositoryNode,
    TagNode,
    TreeNode,
)
from git2neo4j.parsers.git_parser import GitParser


class GitToNeo4jSync:
    """Synchronize Git repository to Neo4j database."""

    def __init__(
        self,
        repo_path: str | Path,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "password",
        neo4j_database: str = "neo4j",
        batch_size: int = 100,
        sync_trees: bool = True,
        sync_blobs: bool = False,
    ) -> None:
        """Initialize Git to Neo4j sync engine.

        Args:
            repo_path: Path to Git repository
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            neo4j_database: Neo4j database name
            batch_size: Batch size for bulk operations
            sync_trees: Whether to sync tree objects
            sync_blobs: Whether to sync blob metadata
        """
        self.repo_path = Path(repo_path).resolve()
        self.parser = GitParser(self.repo_path)
        self.batch_size = batch_size
        self.sync_trees = sync_trees
        self.sync_blobs = sync_blobs

        # Initialize Neo4j driver
        self.driver: Neo4jDriver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password),
        )
        self.database = neo4j_database

    def __enter__(self) -> "GitToNeo4jSync":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    def close(self) -> None:
        """Close Neo4j driver connection."""
        if self.driver:
            self.driver.close()

    def verify_connection(self) -> bool:
        """Verify Neo4j connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.driver.verify_connectivity()
            return True
        except ServiceUnavailable:
            return False

    def setup_schema(self) -> None:
        """Create Neo4j constraints and indexes."""
        with self.driver.session(database=self.database) as session:
            # Create constraints
            for constraint in NEO4J_CONSTRAINTS:
                try:
                    session.run(constraint)
                except Exception:
                    # Constraint might already exist
                    pass

            # Create indexes
            for index in NEO4J_INDEXES:
                try:
                    session.run(index)
                except Exception:
                    # Index might already exist
                    pass

    def sync_repository(self, create_schema: bool = True) -> dict[str, int]:
        """Sync entire repository to Neo4j.

        Args:
            create_schema: Whether to create schema (constraints/indexes)

        Returns:
            Dictionary with sync statistics
        """
        if create_schema:
            self.setup_schema()

        stats = {
            "commits": 0,
            "trees": 0,
            "blobs": 0,
            "tags": 0,
            "branches": 0,
            "authors": 0,
        }

        # Sync repository metadata
        repo_info = self.parser.get_repository_info()
        self._sync_repository_node(repo_info)

        # Sync commits (most important)
        commits = list(self.parser.get_all_commits())
        stats["commits"] = len(commits)
        self._sync_commits_batch(commits)

        # Sync branches
        stats["branches"] = len(repo_info.branches)
        self._sync_branches_batch(repo_info.branches)

        # Sync tags
        tags = list(self.parser.get_all_tags())
        stats["tags"] = len(tags)
        self._sync_tags_batch(tags)

        # Optionally sync trees
        if self.sync_trees and commits:
            tree_count = self._sync_all_trees(commits)
            stats["trees"] = tree_count

        # Update repository stats
        self._update_repository_stats(repo_info, stats)

        return stats

    def sync_incremental(self, since_commit: str | None = None) -> dict[str, int]:
        """Incrementally sync new commits since last sync.

        Args:
            since_commit: SHA of last synced commit (None = sync all)

        Returns:
            Dictionary with sync statistics
        """
        # TODO: Implement incremental sync logic
        # For now, just do full sync
        return self.sync_repository(create_schema=False)

    def _sync_repository_node(self, repo_info: RepositoryInfo) -> None:
        """Sync repository metadata node.

        Args:
            repo_info: Repository information
        """
        repo_node = RepositoryNode(
            path=repo_info.path,
            name=Path(repo_info.path).name,
            head_sha=repo_info.head_sha,
            current_branch=repo_info.current_branch,
            is_bare=repo_info.is_bare,
            last_synced=datetime.now(timezone.utc),
        )

        with self.driver.session(database=self.database) as session:
            session.execute_write(
                self._create_repository_tx,
                repo_node.to_neo4j_properties(),
            )

    def _sync_commits_batch(self, commits: list[CommitObject]) -> None:
        """Sync commits in batches.

        Args:
            commits: List of commit objects
        """
        for i in range(0, len(commits), self.batch_size):
            batch = commits[i : i + self.batch_size]

            with self.driver.session(database=self.database) as session:
                session.execute_write(self._create_commits_tx, batch)

    def _sync_branches_batch(self, branches: list[BranchInfo]) -> None:
        """Sync branches in batches.

        Args:
            branches: List of branch information
        """
        for i in range(0, len(branches), self.batch_size):
            batch = branches[i : i + self.batch_size]

            with self.driver.session(database=self.database) as session:
                session.execute_write(self._create_branches_tx, batch)

    def _sync_tags_batch(self, tags: list[TagObject]) -> None:
        """Sync tags in batches.

        Args:
            tags: List of tag objects
        """
        for i in range(0, len(tags), self.batch_size):
            batch = tags[i : i + self.batch_size]

            with self.driver.session(database=self.database) as session:
                session.execute_write(self._create_tags_tx, batch)

    def _sync_all_trees(self, commits: list[CommitObject]) -> int:
        """Sync all trees for commits.

        Args:
            commits: List of commits

        Returns:
            Number of trees synced
        """
        tree_count = 0
        seen_trees: set[str] = set()

        for commit in commits:
            # Only sync trees we haven't seen
            if commit.tree_sha not in seen_trees:
                try:
                    trees = list(
                        self.parser.get_all_trees_for_commit(commit.sha)
                    )
                    for tree in trees:
                        if tree.sha not in seen_trees:
                            seen_trees.add(tree.sha)
                            tree_count += 1

                    # Sync in batches
                    if trees:
                        self._sync_trees_batch(trees)
                except Exception:
                    # Skip problematic trees
                    continue

        return tree_count

    def _sync_trees_batch(self, trees: list[TreeObject]) -> None:
        """Sync trees in batches.

        Args:
            trees: List of tree objects
        """
        for i in range(0, len(trees), self.batch_size):
            batch = trees[i : i + self.batch_size]

            with self.driver.session(database=self.database) as session:
                session.execute_write(self._create_trees_tx, batch)

    def _update_repository_stats(
        self, repo_info: RepositoryInfo, stats: dict[str, int]
    ) -> None:
        """Update repository node with statistics.

        Args:
            repo_info: Repository information
            stats: Sync statistics
        """
        with self.driver.session(database=self.database) as session:
            session.execute_write(
                self._update_repository_stats_tx,
                repo_info.path,
                stats,
            )

    # Transaction functions

    @staticmethod
    def _create_repository_tx(tx: ManagedTransaction, props: dict[str, Any]) -> None:
        """Create or update repository node.

        Args:
            tx: Neo4j transaction
            props: Repository properties
        """
        query = """
        MERGE (r:Repository {path: $path})
        SET r += $props
        """
        tx.run(query, path=props["path"], props=props)

    @staticmethod
    def _create_commits_tx(tx: ManagedTransaction, commits: list[CommitObject]) -> None:
        """Create commit nodes and relationships.

        Args:
            tx: Neo4j transaction
            commits: List of commits
        """
        # Create commit nodes
        for commit in commits:
            commit_node = CommitNode(
                sha=commit.sha,
                tree_sha=commit.tree_sha,
                message=commit.message,
                author_name=commit.author.name,
                author_email=commit.author.email,
                author_timestamp=commit.author.timestamp,
                author_timezone=commit.author.timezone,
                committer_name=commit.committer.name,
                committer_email=commit.committer.email,
                committer_timestamp=commit.committer.timestamp,
                committer_timezone=commit.committer.timezone,
                encoding=commit.encoding,
                gpg_signature=commit.gpg_signature,
                parent_count=len(commit.parent_shas),
            )

            # Create commit node
            tx.run(
                """
                MERGE (c:Commit {sha: $sha})
                SET c += $props
                """,
                sha=commit.sha,
                props=commit_node.to_neo4j_properties(),
            )

            # Create author node and relationship
            author_node = AuthorNode(
                name=commit.author.name,
                email=commit.author.email,
            )

            tx.run(
                """
                MERGE (a:Author {email: $email})
                SET a.name = $name
                WITH a
                MATCH (c:Commit {sha: $commit_sha})
                MERGE (c)-[:AUTHORED_BY {role: 'author'}]->(a)
                """,
                email=author_node.email,
                name=author_node.name,
                commit_sha=commit.sha,
            )

            # Create parent relationships
            for idx, parent_sha in enumerate(commit.parent_shas):
                tx.run(
                    """
                    MATCH (c:Commit {sha: $sha})
                    MERGE (p:Commit {sha: $parent_sha})
                    MERGE (c)-[:PARENT {parent_index: $idx}]->(p)
                    """,
                    sha=commit.sha,
                    parent_sha=parent_sha,
                    idx=idx,
                )

            # Create tree relationship
            tx.run(
                """
                MATCH (c:Commit {sha: $sha})
                MERGE (t:Tree {sha: $tree_sha})
                MERGE (c)-[:TREE]->(t)
                """,
                sha=commit.sha,
                tree_sha=commit.tree_sha,
            )

    @staticmethod
    def _create_branches_tx(
        tx: ManagedTransaction, branches: list[BranchInfo]
    ) -> None:
        """Create branch nodes and relationships.

        Args:
            tx: Neo4j transaction
            branches: List of branches
        """
        for branch in branches:
            branch_node = BranchNode(
                name=branch.name,
                full_name=branch.full_name,
                commit_sha=branch.commit_sha,
                is_remote=branch.is_remote,
                remote_name=branch.remote_name,
                is_head=branch.is_head,
            )

            tx.run(
                """
                MERGE (b:Branch {full_name: $full_name})
                SET b += $props
                WITH b
                MATCH (c:Commit {sha: $commit_sha})
                MERGE (b)-[:POINTS_TO {ref_type: 'branch'}]->(c)
                """,
                full_name=branch.full_name,
                props=branch_node.to_neo4j_properties(),
                commit_sha=branch.commit_sha,
            )

    @staticmethod
    def _create_tags_tx(tx: ManagedTransaction, tags: list[TagObject]) -> None:
        """Create tag nodes and relationships.

        Args:
            tx: Neo4j transaction
            tags: List of tags
        """
        for tag in tags:
            tag_props = {
                "sha": tag.sha,
                "name": tag.name,
                "target_sha": tag.target_sha,
                "target_type": tag.target_type.value,
                "message": tag.message,
            }

            if tag.tagger:
                tag_props.update(
                    {
                        "tagger_name": tag.tagger.name,
                        "tagger_email": tag.tagger.email,
                        "tagger_timestamp": tag.tagger.timestamp,
                        "tagger_timezone": tag.tagger.timezone,
                    }
                )

            tx.run(
                """
                MERGE (t:Tag {sha: $sha})
                SET t += $props
                WITH t
                MATCH (c:Commit {sha: $target_sha})
                MERGE (t)-[:POINTS_TO {ref_type: 'tag'}]->(c)
                """,
                sha=tag.sha,
                props=tag_props,
                target_sha=tag.target_sha,
            )

    @staticmethod
    def _create_trees_tx(tx: ManagedTransaction, trees: list[TreeObject]) -> None:
        """Create tree nodes and relationships.

        Args:
            tx: Neo4j transaction
            trees: List of trees
        """
        for tree in trees:
            tree_node = TreeNode(
                sha=tree.sha,
                size=tree.size,
                entry_count=len(tree.entries),
                file_count=tree.file_count,
                dir_count=tree.dir_count,
            )

            tx.run(
                """
                MERGE (t:Tree {sha: $sha})
                SET t += $props
                """,
                sha=tree.sha,
                props=tree_node.to_neo4j_properties(),
            )

            # Create relationships to entries
            for entry in tree.entries:
                if entry.type.value == "tree":
                    tx.run(
                        """
                        MATCH (t:Tree {sha: $tree_sha})
                        MERGE (e:Tree {sha: $entry_sha})
                        MERGE (t)-[:HAS_ENTRY {
                            path: $path,
                            mode: $mode,
                            entry_type: 'tree'
                        }]->(e)
                        """,
                        tree_sha=tree.sha,
                        entry_sha=entry.sha,
                        path=entry.path,
                        mode=entry.mode.value,
                    )
                else:  # blob
                    tx.run(
                        """
                        MATCH (t:Tree {sha: $tree_sha})
                        MERGE (b:Blob {sha: $entry_sha})
                        SET b.path = $path
                        MERGE (t)-[:HAS_ENTRY {
                            path: $path,
                            mode: $mode,
                            entry_type: 'blob'
                        }]->(b)
                        """,
                        tree_sha=tree.sha,
                        entry_sha=entry.sha,
                        path=entry.path,
                        mode=entry.mode.value,
                    )

    @staticmethod
    def _update_repository_stats_tx(
        tx: ManagedTransaction, repo_path: str, stats: dict[str, int]
    ) -> None:
        """Update repository statistics.

        Args:
            tx: Neo4j transaction
            repo_path: Repository path
            stats: Statistics dictionary
        """
        tx.run(
            """
            MATCH (r:Repository {path: $path})
            SET r.commit_count = $commits,
                r.branch_count = $branches,
                r.tag_count = $tags,
                r.last_synced = datetime()
            """,
            path=repo_path,
            commits=stats["commits"],
            branches=stats["branches"],
            tags=stats["tags"],
        )
