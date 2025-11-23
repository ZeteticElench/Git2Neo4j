"""Example: Bulk import multiple Git repositories."""

from pathlib import Path

from git2neo4j.sync.bulk_import import import_repositories_from_folder


def example_bulk_import_workspace() -> None:
    """Import all repositories in a workspace folder."""
    # Path to your workspace with multiple Git repositories
    workspace_path = Path.home() / "projects"

    print(f"Importing all repositories from: {workspace_path}\n")

    stats = import_repositories_from_folder(
        folder_path=workspace_path,
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        neo4j_database="neo4j",
        batch_size=100,
        sync_trees=True,  # Include tree objects
        sync_blobs=False,  # Don't sync all blobs initially
        populate_blob_text=False,  # Don't populate text content initially
        recursive=False,  # Only check immediate subdirectories
        create_schema=True,  # Create indexes and constraints
    )

    print("\n" + "=" * 60)
    print("Import Summary")
    print("=" * 60)
    print(f"Repositories imported: {stats['repositories']}")
    print(f"Total commits: {stats['total_commits']}")
    print(f"Total branches: {stats['total_branches']}")
    print(f"Total tags: {stats['total_tags']}")

    if stats['errors']:
        print(f"\nErrors: {len(stats['errors'])}")
        for error in stats['errors']:
            print(f"  - {error['repository']}: {error['error']}")


def example_bulk_import_with_text_content() -> None:
    """Import repositories and populate text content for code search."""
    workspace_path = Path.home() / "projects"

    print(f"Importing repositories with text content from: {workspace_path}\n")

    stats = import_repositories_from_folder(
        folder_path=workspace_path,
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        batch_size=50,  # Smaller batches for large operations
        sync_trees=True,
        populate_blob_text=True,  # Enable text content extraction
        recursive=False,
    )

    print(f"\nBlobs with text content: {stats['total_blobs_with_text']}")
    print("You can now use full-text search on code!")


def example_recursive_search() -> None:
    """Recursively find and import all Git repositories."""
    root_path = Path.home() / "Development"

    print(f"Recursively searching for repositories in: {root_path}\n")

    stats = import_repositories_from_folder(
        folder_path=root_path,
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        recursive=True,  # Search all subdirectories recursively
        sync_trees=True,
        populate_blob_text=False,
    )

    print(f"\nFound and imported {stats['repositories']} repositories")


def example_cli_bulk_import() -> None:
    """Example using CLI instead of Python API."""
    print("Using CLI for bulk import:\n")

    print("Basic import:")
    print("  git2neo4j bulk-import ~/projects --uri bolt://localhost:7687 -p password\n")

    print("With text content:")
    print("  git2neo4j bulk-import ~/projects --populate-text --uri bolt://localhost:7687\n")

    print("Recursive search:")
    print("  git2neo4j bulk-import ~/Development --recursive --uri bolt://localhost:7687\n")

    print("Custom database:")
    print("  git2neo4j bulk-import ~/projects -d my_database --uri bolt://localhost:7687\n")

    print("Full example with all options:")
    print("""
  git2neo4j bulk-import ~/projects \\
    --uri bolt://localhost:7687 \\
    --user neo4j \\
    --password mypassword \\
    --database git_repos \\
    --batch-size 50 \\
    --trees \\
    --populate-text \\
    --recursive
    """)


def example_post_import_operations() -> None:
    """Example operations after bulk import."""
    from git2neo4j.queries.cypher_ops import CypherGitOps

    print("Post-Import Operations\n")

    with CypherGitOps(
        "bolt://localhost:7687",
        "neo4j",
        "password",
    ) as ops:
        # List all imported repositories
        print("1. Listing all imported repositories:")
        query = """
        MATCH (r:Repository)
        RETURN r.name as name,
               r.commit_count as commits,
               r.current_branch as current_branch,
               r.last_synced as last_synced
        ORDER BY r.name
        """
        results = ops.execute_cypher(query)

        for repo in results:
            print(f"  {repo['name']}")
            print(f"    Commits: {repo['commits']}")
            print(f"    Current branch: {repo['current_branch']}")
            print(f"    Last synced: {repo['last_synced']}")
            print()

        # Find cross-repository dependencies (same author working on multiple repos)
        print("2. Developers working across multiple repositories:")
        query = """
        MATCH (c:Commit)
        WITH c.author_email as email,
             collect(DISTINCT c.repo_name) as repos
        WHERE size(repos) > 1
        RETURN email,
               repos,
               size(repos) as repo_count
        ORDER BY repo_count DESC
        LIMIT 10
        """
        results = ops.execute_cypher(query)

        for dev in results:
            print(f"  {dev['email']}: {dev['repo_count']} repositories")
            print(f"    Repos: {', '.join(dev['repos'][:5])}")
            if len(dev['repos']) > 5:
                print(f"    ... and {len(dev['repos']) - 5} more")
            print()

        # Find repositories with most recent activity
        print("3. Most recently active repositories:")
        query = """
        MATCH (r:Repository)-[:HAS_HEAD]->(head:Commit)
        RETURN r.name as repo,
               head.author_timestamp as last_commit
        ORDER BY last_commit DESC
        LIMIT 10
        """
        results = ops.execute_cypher(query)

        for repo in results:
            print(f"  {repo['repo']}: {repo['last_commit']}")


if __name__ == "__main__":
    print("Git2Neo4j Bulk Import Examples\n")
    print("=" * 60)
    print()

    # Choose which example to run:

    # Example 1: Basic bulk import
    # example_bulk_import_workspace()

    # Example 2: Import with text content for code search
    # example_bulk_import_with_text_content()

    # Example 3: Recursive search
    # example_recursive_search()

    # Example 4: CLI examples
    example_cli_bulk_import()

    # Example 5: Post-import operations
    # example_post_import_operations()

    print("\nNote: Update the workspace paths and credentials before running!")
