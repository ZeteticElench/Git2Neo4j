"""Bulk import utilities for importing multiple Git repositories."""

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from git2neo4j.sync.git_to_neo4j import GitToNeo4jSync


console = Console()


def import_repositories_from_folder(
    folder_path: str | Path,
    neo4j_uri: str = "bolt://localhost:7687",
    neo4j_user: str = "neo4j",
    neo4j_password: str = "password",
    neo4j_database: str = "neo4j",
    batch_size: int = 100,
    sync_trees: bool = True,
    sync_blobs: bool = False,
    populate_blob_text: bool = False,
    recursive: bool = False,
    create_schema: bool = True,
) -> dict[str, Any]:
    """Import all Git repositories from a folder.

    Args:
        folder_path: Path to folder containing Git repositories
        neo4j_uri: Neo4j connection URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password
        neo4j_database: Neo4j database name
        batch_size: Batch size for operations
        sync_trees: Whether to sync tree objects
        sync_blobs: Whether to sync blob metadata
        populate_blob_text: Whether to populate text content for blobs
        recursive: Whether to search for repositories recursively
        create_schema: Whether to create schema on first sync

    Returns:
        Dictionary with import statistics
    """
    folder = Path(folder_path).resolve()

    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"Folder does not exist: {folder}")

    console.print(f"[bold blue]Searching for Git repositories in:[/bold blue] {folder}")

    # Find all Git repositories
    repositories = find_git_repositories(folder, recursive=recursive)

    if not repositories:
        console.print("[yellow]No Git repositories found[/yellow]")
        return {"repositories": 0, "total_commits": 0, "errors": []}

    console.print(f"[green]Found {len(repositories)} Git repositories[/green]\n")

    stats = {
        "repositories": 0,
        "total_commits": 0,
        "total_branches": 0,
        "total_tags": 0,
        "total_trees": 0,
        "total_blobs_with_text": 0,
        "errors": [],
    }

    # Import each repository
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        main_task = progress.add_task(
            "Importing repositories...",
            total=len(repositories),
        )

        for idx, repo_path in enumerate(repositories):
            repo_name = repo_path.name
            progress.update(
                main_task,
                description=f"Importing {repo_name}...",
            )

            try:
                with GitToNeo4jSync(
                    repo_path=repo_path,
                    neo4j_uri=neo4j_uri,
                    neo4j_user=neo4j_user,
                    neo4j_password=neo4j_password,
                    neo4j_database=neo4j_database,
                    batch_size=batch_size,
                    sync_trees=sync_trees,
                    sync_blobs=sync_blobs,
                ) as sync:
                    # Only create schema for first repository
                    repo_stats = sync.sync_repository(
                        create_schema=(create_schema and idx == 0)
                    )

                    stats["repositories"] += 1
                    stats["total_commits"] += repo_stats.get("commits", 0)
                    stats["total_branches"] += repo_stats.get("branches", 0)
                    stats["total_tags"] += repo_stats.get("tags", 0)
                    stats["total_trees"] += repo_stats.get("trees", 0)

                    # Optionally populate blob text content
                    if populate_blob_text and sync_trees:
                        blob_count = sync.populate_blob_content()
                        stats["total_blobs_with_text"] += blob_count

                    console.print(
                        f"  [green]✓[/green] {repo_name}: "
                        f"{repo_stats.get('commits', 0)} commits, "
                        f"{repo_stats.get('branches', 0)} branches"
                    )

            except Exception as e:
                stats["errors"].append({
                    "repository": str(repo_path),
                    "error": str(e),
                })
                console.print(f"  [red]✗[/red] {repo_name}: {e}")

            progress.update(main_task, advance=1)

    # Print summary
    console.print("\n[bold green]Import Complete![/bold green]")
    console.print(f"Repositories imported: {stats['repositories']}")
    console.print(f"Total commits: {stats['total_commits']}")
    console.print(f"Total branches: {stats['total_branches']}")
    console.print(f"Total tags: {stats['total_tags']}")
    console.print(f"Total trees: {stats['total_trees']}")
    if populate_blob_text:
        console.print(f"Blobs with text content: {stats['total_blobs_with_text']}")

    if stats["errors"]:
        console.print(f"\n[yellow]Errors: {len(stats['errors'])}[/yellow]")
        for error in stats["errors"]:
            console.print(f"  - {error['repository']}: {error['error']}")

    return stats


def find_git_repositories(
    root_path: Path,
    recursive: bool = False,
) -> list[Path]:
    """Find all Git repositories in a folder.

    Args:
        root_path: Root path to search
        recursive: Whether to search recursively in subdirectories

    Returns:
        List of paths to Git repositories
    """
    repositories = []

    if recursive:
        # Recursively find all .git directories
        for git_dir in root_path.rglob(".git"):
            if git_dir.is_dir():
                repo_path = git_dir.parent
                repositories.append(repo_path)
    else:
        # Only check immediate subdirectories
        for item in root_path.iterdir():
            if item.is_dir():
                git_dir = item / ".git"
                if git_dir.exists() and git_dir.is_dir():
                    repositories.append(item)

    return sorted(repositories)
