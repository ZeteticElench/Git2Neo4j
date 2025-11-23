"""Example: Full-text search across Git repositories."""

from git2neo4j.queries.cypher_ops import CypherGitOps
from git2neo4j.sync.git_to_neo4j import GitToNeo4jSync


def example_populate_text_content() -> None:
    """Example: Populate text content for blobs."""
    print("=== Populating Text Content for Blobs ===\n")

    with GitToNeo4jSync(
        repo_path="/path/to/repo",
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
    ) as sync:
        # Populate text content for text files
        count = sync.populate_blob_content(
            max_file_size=1024 * 1024,  # 1MB max
            text_extensions={".py", ".js", ".java", ".md"},  # Only these extensions
        )
        print(f"Populated text content for {count} blobs\n")


def example_fulltext_search() -> None:
    """Example: Full-text search on code and commits."""
    print("=== Full-Text Search Examples ===\n")

    with CypherGitOps(
        "bolt://localhost:7687",
        "neo4j",
        "password",
    ) as ops:
        # Search for TODO comments in code
        print("1. Search for TODO comments:")
        query = """
        CALL db.index.fulltext.queryNodes("blob_content_fulltext", "TODO")
        YIELD node, score
        WHERE node.repo_name = $repo_name
        RETURN node.path as file,
               node.repo_name as repo,
               score
        ORDER BY score DESC
        LIMIT 10
        """
        results = ops.execute_cypher(query, {"repo_name": "my-repo"})
        for r in results:
            print(f"  {r['repo']}/{r['file']} (score: {r['score']:.2f})")
        print()

        # Search for specific function definitions
        print("2. Search for function definitions:")
        query = """
        CALL db.index.fulltext.queryNodes("blob_content_fulltext", "def authenticate")
        YIELD node, score
        WHERE node.extension = '.py'
        RETURN node.path as file,
               node.repo_name as repo,
               score
        ORDER BY score DESC
        LIMIT 5
        """
        results = ops.execute_cypher(query)
        for r in results:
            print(f"  {r['repo']}/{r['file']}")
        print()

        # Search commit messages
        print("3. Search commit messages:")
        query = """
        CALL db.index.fulltext.queryNodes("commit_message_fulltext", "fix bug")
        YIELD node, score
        RETURN node.sha as sha,
               node.message as message,
               node.repo_name as repo,
               score
        ORDER BY score DESC
        LIMIT 5
        """
        results = ops.execute_cypher(query)
        for r in results:
            print(f"  [{r['repo']}] {r['sha'][:8]}: {r['message'][:50]}...")
        print()

        # Search file paths
        print("4. Search file paths:")
        query = """
        CALL db.index.fulltext.queryNodes("blob_path_fulltext", "test")
        YIELD node, score
        WHERE node.extension = '.py'
        RETURN node.path as path,
               node.repo_name as repo
        ORDER BY score DESC
        LIMIT 10
        """
        results = ops.execute_cypher(query)
        for r in results:
            print(f"  {r['repo']}/{r['path']}")
        print()


def example_multi_repo_queries() -> None:
    """Example: Queries across multiple repositories."""
    print("=== Multi-Repository Queries ===\n")

    with CypherGitOps(
        "bolt://localhost:7687",
        "neo4j",
        "password",
    ) as ops:
        # List all repositories
        print("1. All repositories in database:")
        query = """
        MATCH (r:Repository)
        RETURN r.name as name,
               r.commit_count as commits,
               r.branch_count as branches,
               r.last_synced as last_synced
        ORDER BY r.name
        """
        results = ops.execute_cypher(query)
        for r in results:
            print(f"  {r['name']}: {r['commits']} commits, {r['branches']} branches")
        print()

        # Find commits across all repositories by author
        print("2. Commits by author across all repos:")
        query = """
        MATCH (c:Commit)
        WHERE c.author_email = $email
        RETURN c.repo_name as repo,
               count(c) as commit_count
        ORDER BY commit_count DESC
        """
        results = ops.execute_cypher(query, {"email": "dev@example.com"})
        for r in results:
            print(f"  {r['repo']}: {r['commit_count']} commits")
        print()

        # Find most active repositories
        print("3. Most active repositories (by commit count):")
        query = """
        MATCH (c:Commit)
        WITH c.repo_name as repo, count(c) as commits
        RETURN repo, commits
        ORDER BY commits DESC
        LIMIT 10
        """
        results = ops.execute_cypher(query)
        for r in results:
            print(f"  {r['repo']}: {r['commits']} commits")
        print()

        # Find common files across repositories
        print("4. Common file names across repositories:")
        query = """
        MATCH (b:Blob)
        WHERE b.path IS NOT NULL
        WITH b.path as path, collect(DISTINCT b.repo_name) as repos
        WHERE size(repos) > 1
        RETURN path, repos, size(repos) as repo_count
        ORDER BY repo_count DESC
        LIMIT 10
        """
        results = ops.execute_cypher(query)
        for r in results:
            print(f"  {r['path']}: in {r['repo_count']} repos ({', '.join(r['repos'][:3])}...)")
        print()


def example_repository_centric_queries() -> None:
    """Example: Repository-centric graph traversal."""
    print("=== Repository-Centric Queries ===\n")

    with CypherGitOps(
        "bolt://localhost:7687",
        "neo4j",
        "password",
    ) as ops:
        # Get repository with all its branches
        print("1. Repository with branches:")
        query = """
        MATCH (r:Repository {name: $repo_name})-[:TRACKS]->(b:Branch)
        RETURN r.name as repo,
               collect(b.name) as branches
        """
        results = ops.execute_cypher(query, {"repo_name": "my-repo"})
        for r in results:
            print(f"  {r['repo']}: {', '.join(r['branches'])}")
        print()

        # Get repository HEAD and recent commits
        print("2. Repository HEAD and recent commits:")
        query = """
        MATCH (r:Repository {name: $repo_name})-[:HAS_HEAD]->(head:Commit)
        MATCH path = (head)-[:PARENT*0..10]->(c:Commit)
        WITH DISTINCT c
        ORDER BY c.author_timestamp DESC
        LIMIT 5
        RETURN c.sha as sha,
               c.message as message,
               c.author_timestamp as timestamp
        """
        results = ops.execute_cypher(query, {"repo_name": "my-repo"})
        for r in results:
            print(f"  {r['sha'][:8]}: {r['message'][:50]}...")
        print()

        # Get all commits in repository
        print("3. All commits in repository:")
        query = """
        MATCH (r:Repository {name: $repo_name})-[:CONTAINS]->(c:Commit)
        RETURN count(c) as total_commits
        """
        results = ops.execute_cypher(query, {"repo_name": "my-repo"})
        print(f"  Total commits: {results[0]['total_commits']}")
        print()


if __name__ == "__main__":
    print("Git2Neo4j Full-Text Search Examples\n")
    print("=" * 60)
    print()

    # Uncomment the examples you want to run:

    # example_populate_text_content()
    # example_fulltext_search()
    # example_multi_repo_queries()
    # example_repository_centric_queries()

    print("\nNote: Update the connection details and repo paths before running!")
