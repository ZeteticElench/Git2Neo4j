"""Cypher query operations that mimic Git commands."""

from datetime import datetime
from typing import Any

from neo4j import GraphDatabase, Neo4jDriver, Record


class CypherGitOps:
    """Git-like operations using Cypher queries."""

    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "password",
        neo4j_database: str = "neo4j",
    ) -> None:
        """Initialize Cypher Git operations.

        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            neo4j_database: Neo4j database name
        """
        self.driver: Neo4jDriver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password),
        )
        self.database = neo4j_database

    def __enter__(self) -> "CypherGitOps":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    def close(self) -> None:
        """Close Neo4j driver connection."""
        if self.driver:
            self.driver.close()

    # Git log equivalents

    def log(
        self,
        branch: str = "main",
        limit: int = 10,
        skip: int = 0,
        author: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get commit history (equivalent to git log).

        Args:
            branch: Branch name to traverse
            limit: Maximum number of commits to return
            skip: Number of commits to skip
            author: Filter by author email (optional)

        Returns:
            List of commit dictionaries
        """
        query = """
        MATCH (b:Branch {name: $branch})-[:POINTS_TO]->(head:Commit)
        MATCH path = (head)-[:PARENT*0..]->(c:Commit)
        """

        if author:
            query += """
            MATCH (c)-[:AUTHORED_BY]->(a:Author {email: $author})
            """

        query += """
        WITH DISTINCT c
        ORDER BY c.author_timestamp DESC
        SKIP $skip
        LIMIT $limit
        RETURN c.sha as sha,
               c.message as message,
               c.author_name as author_name,
               c.author_email as author_email,
               c.author_timestamp as timestamp,
               c.parent_count as parent_count
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(
                query,
                branch=branch,
                limit=limit,
                skip=skip,
                author=author,
            )
            return [dict(record) for record in result]

    def log_all(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get all commits across all branches (git log --all).

        Args:
            limit: Maximum number of commits

        Returns:
            List of commit dictionaries
        """
        query = """
        MATCH (c:Commit)
        RETURN c.sha as sha,
               c.message as message,
               c.author_name as author_name,
               c.author_email as author_email,
               c.author_timestamp as timestamp,
               c.parent_count as parent_count
        ORDER BY c.author_timestamp DESC
        LIMIT $limit
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, limit=limit)
            return [dict(record) for record in result]

    def show(self, commit_sha: str) -> dict[str, Any] | None:
        """Show commit details (equivalent to git show).

        Args:
            commit_sha: Commit SHA to show

        Returns:
            Commit details with file changes
        """
        query = """
        MATCH (c:Commit {sha: $sha})
        OPTIONAL MATCH (c)-[:TREE]->(t:Tree)-[:HAS_ENTRY*]->(entry)
        OPTIONAL MATCH (c)-[:PARENT]->(p:Commit)
        RETURN c.sha as sha,
               c.message as message,
               c.author_name as author_name,
               c.author_email as author_email,
               c.author_timestamp as timestamp,
               c.tree_sha as tree_sha,
               collect(DISTINCT p.sha) as parent_shas,
               collect(DISTINCT {
                   sha: entry.sha,
                   path: entry.path,
                   type: labels(entry)[0]
               }) as entries
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, sha=commit_sha)
            record = result.single()
            return dict(record) if record else None

    # Branch operations

    def branch_list(self, remote: bool = False) -> list[dict[str, Any]]:
        """List branches (equivalent to git branch).

        Args:
            remote: Show remote branches

        Returns:
            List of branch dictionaries
        """
        query = """
        MATCH (b:Branch)
        WHERE b.is_remote = $remote
        OPTIONAL MATCH (b)-[:POINTS_TO]->(c:Commit)
        RETURN b.name as name,
               b.full_name as full_name,
               b.commit_sha as commit_sha,
               b.is_head as is_head,
               b.remote_name as remote_name,
               c.author_timestamp as last_commit_time
        ORDER BY b.name
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, remote=remote)
            return [dict(record) for record in result]

    def branch_commits(
        self, branch1: str, branch2: str
    ) -> dict[str, list[dict[str, Any]]]:
        """Show commits in branch1 but not in branch2.

        Args:
            branch1: First branch
            branch2: Second branch

        Returns:
            Dictionary with commits unique to each branch
        """
        query = """
        MATCH (b1:Branch {name: $branch1})-[:POINTS_TO]->(c1:Commit)
        MATCH (b2:Branch {name: $branch2})-[:POINTS_TO]->(c2:Commit)

        // Commits in branch1 not in branch2
        OPTIONAL MATCH path1 = (c1)-[:PARENT*0..]->(commit1:Commit)
        WHERE NOT (c2)-[:PARENT*0..]->(commit1)

        // Commits in branch2 not in branch1
        OPTIONAL MATCH path2 = (c2)-[:PARENT*0..]->(commit2:Commit)
        WHERE NOT (c1)-[:PARENT*0..]->(commit2)

        RETURN collect(DISTINCT {
                   sha: commit1.sha,
                   message: commit1.message,
                   timestamp: commit1.author_timestamp
               }) as unique_to_branch1,
               collect(DISTINCT {
                   sha: commit2.sha,
                   message: commit2.message,
                   timestamp: commit2.author_timestamp
               }) as unique_to_branch2
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, branch1=branch1, branch2=branch2)
            record = result.single()
            return dict(record) if record else {}

    # Merge base (common ancestor)

    def merge_base(self, commit1_sha: str, commit2_sha: str) -> dict[str, Any] | None:
        """Find common ancestor of two commits (git merge-base).

        Args:
            commit1_sha: First commit SHA
            commit2_sha: Second commit SHA

        Returns:
            Common ancestor commit details
        """
        query = """
        MATCH (c1:Commit {sha: $sha1})
        MATCH (c2:Commit {sha: $sha2})

        // Find all ancestors of c1
        MATCH path1 = (c1)-[:PARENT*0..]->(ancestor:Commit)
        WITH c1, c2, collect(DISTINCT ancestor) as ancestors1

        // Find all ancestors of c2
        MATCH path2 = (c2)-[:PARENT*0..]->(ancestor2:Commit)
        WHERE ancestor2 IN ancestors1

        // Return the most recent common ancestor
        RETURN ancestor2.sha as sha,
               ancestor2.message as message,
               ancestor2.author_timestamp as timestamp,
               ancestor2.author_name as author_name
        ORDER BY ancestor2.author_timestamp DESC
        LIMIT 1
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, sha1=commit1_sha, sha2=commit2_sha)
            record = result.single()
            return dict(record) if record else None

    # File history and blame

    def file_history(
        self, file_path: str, branch: str = "main", limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get commit history for a specific file.

        Args:
            file_path: File path to track
            branch: Branch to traverse
            limit: Maximum commits to return

        Returns:
            List of commits that modified the file
        """
        query = """
        MATCH (b:Branch {name: $branch})-[:POINTS_TO]->(head:Commit)
        MATCH path = (head)-[:PARENT*0..]->(c:Commit)
        MATCH (c)-[:TREE]->(t:Tree)-[:HAS_ENTRY*]->(blob:Blob)
        WHERE blob.path = $file_path

        RETURN DISTINCT c.sha as sha,
               c.message as message,
               c.author_name as author_name,
               c.author_email as author_email,
               c.author_timestamp as timestamp,
               blob.sha as blob_sha
        ORDER BY c.author_timestamp DESC
        LIMIT $limit
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, file_path=file_path, branch=branch, limit=limit)
            return [dict(record) for record in result]

    # Statistics and analytics

    def author_stats(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get commit statistics per author.

        Args:
            limit: Maximum authors to return

        Returns:
            List of author statistics
        """
        query = """
        MATCH (a:Author)<-[:AUTHORED_BY]-(c:Commit)
        WITH a, count(c) as commit_count,
             min(c.author_timestamp) as first_commit,
             max(c.author_timestamp) as last_commit
        RETURN a.name as name,
               a.email as email,
               commit_count,
               first_commit,
               last_commit
        ORDER BY commit_count DESC
        LIMIT $limit
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, limit=limit)
            return [dict(record) for record in result]

    def commit_activity(self, days: int = 30) -> list[dict[str, Any]]:
        """Get commit activity over time.

        Args:
            days: Number of days to look back

        Returns:
            Commit counts by date
        """
        query = """
        MATCH (c:Commit)
        WHERE c.author_timestamp >= datetime() - duration({days: $days})
        WITH date(c.author_timestamp) as commit_date, count(c) as count
        RETURN commit_date, count
        ORDER BY commit_date DESC
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, days=days)
            return [dict(record) for record in result]

    # Graph analytics

    def most_connected_commits(self, limit: int = 10) -> list[dict[str, Any]]:
        """Find commits with most relationships (merges, references).

        Args:
            limit: Number of commits to return

        Returns:
            Most connected commits
        """
        query = """
        MATCH (c:Commit)
        OPTIONAL MATCH (c)-[:PARENT]->(p:Commit)
        OPTIONAL MATCH (c)<-[:PARENT]-(child:Commit)
        OPTIONAL MATCH (b:Branch)-[:POINTS_TO]->(c)
        OPTIONAL MATCH (t:Tag)-[:POINTS_TO]->(c)

        WITH c,
             count(DISTINCT p) as parent_count,
             count(DISTINCT child) as child_count,
             count(DISTINCT b) as branch_count,
             count(DISTINCT t) as tag_count

        RETURN c.sha as sha,
               c.message as message,
               c.author_timestamp as timestamp,
               parent_count,
               child_count,
               branch_count,
               tag_count,
               (parent_count + child_count + branch_count + tag_count) as total_connections
        ORDER BY total_connections DESC
        LIMIT $limit
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, limit=limit)
            return [dict(record) for record in result]

    def shortest_path_between_commits(
        self, commit1_sha: str, commit2_sha: str
    ) -> dict[str, Any] | None:
        """Find shortest path between two commits in the DAG.

        Args:
            commit1_sha: First commit SHA
            commit2_sha: Second commit SHA

        Returns:
            Path information
        """
        query = """
        MATCH (c1:Commit {sha: $sha1})
        MATCH (c2:Commit {sha: $sha2})
        MATCH path = shortestPath((c1)-[:PARENT*]-(c2))

        RETURN length(path) as path_length,
               [node in nodes(path) | node.sha] as commit_shas,
               [node in nodes(path) | node.message] as messages
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, sha1=commit1_sha, sha2=commit2_sha)
            record = result.single()
            return dict(record) if record else None

    # Custom Cypher execution

    def execute_cypher(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute custom Cypher query.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            Query results as list of dictionaries
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]


# Commonly used Cypher query templates
CYPHER_TEMPLATES = {
    "git_log": """
        MATCH (b:Branch {name: $branch})-[:POINTS_TO]->(head:Commit)
        MATCH path = (head)-[:PARENT*0..]->(c:Commit)
        RETURN DISTINCT c
        ORDER BY c.author_timestamp DESC
        LIMIT $limit
    """,
    "git_show": """
        MATCH (c:Commit {sha: $sha})
        OPTIONAL MATCH (c)-[:TREE]->(t:Tree)
        OPTIONAL MATCH (c)-[:PARENT]->(p:Commit)
        RETURN c, t, collect(p) as parents
    """,
    "git_branch": """
        MATCH (b:Branch)
        OPTIONAL MATCH (b)-[:POINTS_TO]->(c:Commit)
        RETURN b, c
        ORDER BY b.name
    """,
    "git_merge_base": """
        MATCH (c1:Commit {sha: $sha1})
        MATCH (c2:Commit {sha: $sha2})
        MATCH path1 = (c1)-[:PARENT*0..]->(ancestor:Commit)
        MATCH path2 = (c2)-[:PARENT*0..]->(ancestor)
        RETURN ancestor
        ORDER BY ancestor.author_timestamp DESC
        LIMIT 1
    """,
    "git_diff": """
        MATCH (c1:Commit {sha: $sha1})-[:TREE]->(t1:Tree)
        MATCH (c2:Commit {sha: $sha2})-[:TREE]->(t2:Tree)
        OPTIONAL MATCH (t1)-[:HAS_ENTRY*]->(entry1)
        OPTIONAL MATCH (t2)-[:HAS_ENTRY*]->(entry2)
        RETURN collect(DISTINCT entry1) as entries1,
               collect(DISTINCT entry2) as entries2
    """,
    "git_blame": """
        MATCH (b:Blob {path: $file_path})<-[:HAS_ENTRY*]-(t:Tree)<-[:TREE]-(c:Commit)
        RETURN c.sha, c.author_name, c.author_timestamp, b.sha
        ORDER BY c.author_timestamp DESC
        LIMIT 1
    """,
}
