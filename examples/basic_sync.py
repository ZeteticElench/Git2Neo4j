"""Basic example: Sync a Git repository to Neo4j."""

from pathlib import Path

from git2neo4j.sync.git_to_neo4j import GitToNeo4jSync


def main() -> None:
    """Sync a Git repository to Neo4j."""
    # Configuration
    repo_path = Path("/path/to/your/git/repo")  # Change this!
    neo4j_uri = "bolt://localhost:7687"
    neo4j_user = "neo4j"
    neo4j_password = "password"

    print(f"Syncing repository: {repo_path}")

    # Create sync engine
    with GitToNeo4jSync(
        repo_path=repo_path,
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password,
        batch_size=100,
        sync_trees=True,
        sync_blobs=False,  # Set to True to sync blob metadata
    ) as sync:
        # Verify connection
        if not sync.verify_connection():
            print("Failed to connect to Neo4j!")
            return

        print("Connected to Neo4j successfully!")

        # Perform sync
        stats = sync.sync_repository(create_schema=True)

        # Display statistics
        print("\nSync completed!")
        print(f"Commits synced: {stats['commits']}")
        print(f"Branches synced: {stats['branches']}")
        print(f"Tags synced: {stats['tags']}")
        print(f"Trees synced: {stats['trees']}")


if __name__ == "__main__":
    main()
