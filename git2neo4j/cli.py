"""Command-line interface for Git2Neo4j."""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from git2neo4j.config import Config
from git2neo4j.queries.cypher_ops import CypherGitOps
from git2neo4j.sync.bulk_import import import_repositories_from_folder
from git2neo4j.sync.git_to_neo4j import GitToNeo4jSync
from git2neo4j.sync.neo4j_to_git import Neo4jToGitSync

app = typer.Typer(
    name="git2neo4j",
    help="Sync Git repositories with Neo4j and perform Git operations via Cypher",
    add_completion=False,
)
console = Console()


@app.command()
def sync(
    repo_path: str = typer.Argument(
        ".",
        help="Path to Git repository",
    ),
    uri: str = typer.Option(
        "bolt://localhost:7687",
        "--uri",
        "-u",
        help="Neo4j connection URI",
    ),
    user: str = typer.Option(
        "neo4j",
        "--user",
        help="Neo4j username",
    ),
    password: str = typer.Option(
        "password",
        "--password",
        "-p",
        help="Neo4j password",
    ),
    database: str = typer.Option(
        "neo4j",
        "--database",
        "-d",
        help="Neo4j database name",
    ),
    batch_size: int = typer.Option(
        100,
        "--batch-size",
        "-b",
        help="Batch size for operations",
    ),
    sync_trees: bool = typer.Option(
        True,
        "--trees/--no-trees",
        help="Sync tree objects",
    ),
    sync_blobs: bool = typer.Option(
        False,
        "--blobs/--no-blobs",
        help="Sync blob metadata",
    ),
) -> None:
    """Sync a Git repository to Neo4j database."""
    repo_path_obj = Path(repo_path).resolve()

    if not repo_path_obj.exists():
        console.print(f"[red]Error: Repository path does not exist: {repo_path}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold blue]Syncing repository:[/bold blue] {repo_path}")
    console.print(f"[bold blue]Neo4j URI:[/bold blue] {uri}")

    try:
        with GitToNeo4jSync(
            repo_path=repo_path_obj,
            neo4j_uri=uri,
            neo4j_user=user,
            neo4j_password=password,
            neo4j_database=database,
            batch_size=batch_size,
            sync_trees=sync_trees,
            sync_blobs=sync_blobs,
        ) as sync_engine:
            # Verify connection
            console.print("[yellow]Verifying Neo4j connection...[/yellow]")
            if not sync_engine.verify_connection():
                console.print("[red]Failed to connect to Neo4j[/red]")
                raise typer.Exit(1)

            console.print("[green]Connected successfully![/green]")

            # Perform sync
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Syncing repository...", total=None)

                stats = sync_engine.sync_repository(create_schema=True)

                progress.update(task, completed=True)

            # Display statistics
            table = Table(title="Sync Statistics")
            table.add_column("Object Type", style="cyan")
            table.add_column("Count", style="green", justify="right")

            table.add_row("Commits", str(stats["commits"]))
            table.add_row("Branches", str(stats["branches"]))
            table.add_row("Tags", str(stats["tags"]))
            table.add_row("Trees", str(stats["trees"]))

            console.print(table)
            console.print("[bold green]Sync completed successfully![/bold green]")

    except Exception as e:
        console.print(f"[red]Sync failed: {e}[/red]")
        raise typer.Exit(1)


@app.command(name="bulk-import")
def bulk_import(
    folder_path: str = typer.Argument(
        ".",
        help="Path to folder containing Git repositories",
    ),
    uri: str = typer.Option(
        "bolt://localhost:7687",
        "--uri",
        "-u",
        help="Neo4j connection URI",
    ),
    user: str = typer.Option(
        "neo4j",
        "--user",
        help="Neo4j username",
    ),
    password: str = typer.Option(
        "password",
        "--password",
        "-p",
        help="Neo4j password",
    ),
    database: str = typer.Option(
        "neo4j",
        "--database",
        "-d",
        help="Neo4j database name",
    ),
    batch_size: int = typer.Option(
        100,
        "--batch-size",
        "-b",
        help="Batch size for operations",
    ),
    sync_trees: bool = typer.Option(
        True,
        "--trees/--no-trees",
        help="Sync tree objects",
    ),
    sync_blobs: bool = typer.Option(
        False,
        "--blobs/--no-blobs",
        help="Sync blob metadata",
    ),
    populate_text: bool = typer.Option(
        False,
        "--populate-text/--no-populate-text",
        help="Populate text content for blobs",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive/--no-recursive",
        "-r",
        help="Recursively search for repositories",
    ),
) -> None:
    """Import all Git repositories from a folder."""
    folder_path_obj = Path(folder_path).resolve()

    if not folder_path_obj.exists():
        console.print(f"[red]Error: Folder does not exist: {folder_path}[/red]")
        raise typer.Exit(1)

    try:
        stats = import_repositories_from_folder(
            folder_path=folder_path_obj,
            neo4j_uri=uri,
            neo4j_user=user,
            neo4j_password=password,
            neo4j_database=database,
            batch_size=batch_size,
            sync_trees=sync_trees,
            sync_blobs=sync_blobs,
            populate_blob_text=populate_text,
            recursive=recursive,
            create_schema=True,
        )

    except Exception as e:
        console.print(f"[red]Bulk import failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def log(
    branch: str = typer.Option(
        "main",
        "--branch",
        "-b",
        help="Branch to show log for",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        help="Number of commits to show",
    ),
    author: Optional[str] = typer.Option(
        None,
        "--author",
        "-a",
        help="Filter by author email",
    ),
    uri: str = typer.Option(
        "bolt://localhost:7687",
        "--uri",
        "-u",
        help="Neo4j connection URI",
    ),
    user: str = typer.Option(
        "neo4j",
        "--user",
        help="Neo4j username",
    ),
    password: str = typer.Option(
        "password",
        "--password",
        "-p",
        help="Neo4j password",
    ),
) -> None:
    """Show commit log (equivalent to git log)."""
    try:
        with CypherGitOps(uri, user, password) as ops:
            commits = ops.log(branch=branch, limit=limit, author=author)

            if not commits:
                console.print(f"[yellow]No commits found for branch '{branch}'[/yellow]")
                return

            for commit in commits:
                console.print(f"[bold yellow]commit {commit['sha']}[/bold yellow]")
                console.print(f"Author: {commit['author_name']} <{commit['author_email']}>")
                console.print(f"Date:   {commit['timestamp']}")
                console.print()
                console.print(f"    {commit['message'].strip()}")
                console.print()

    except Exception as e:
        console.print(f"[red]Failed to fetch log: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def show(
    commit_sha: str = typer.Argument(..., help="Commit SHA to show"),
    uri: str = typer.Option(
        "bolt://localhost:7687",
        "--uri",
        "-u",
        help="Neo4j connection URI",
    ),
    user: str = typer.Option(
        "neo4j",
        "--user",
        help="Neo4j username",
    ),
    password: str = typer.Option(
        "password",
        "--password",
        "-p",
        help="Neo4j password",
    ),
) -> None:
    """Show commit details (equivalent to git show)."""
    try:
        with CypherGitOps(uri, user, password) as ops:
            commit = ops.show(commit_sha)

            if not commit:
                console.print(f"[red]Commit not found: {commit_sha}[/red]")
                raise typer.Exit(1)

            console.print(f"[bold yellow]commit {commit['sha']}[/bold yellow]")
            console.print(f"Author: {commit['author_name']} <{commit['author_email']}>")
            console.print(f"Date:   {commit['timestamp']}")
            console.print()
            console.print(f"    {commit['message'].strip()}")
            console.print()

            if commit['parent_shas']:
                console.print(f"Parents: {', '.join(commit['parent_shas'])}")

            console.print(f"Tree: {commit['tree_sha']}")

    except Exception as e:
        console.print(f"[red]Failed to show commit: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def branch(
    list_branches: bool = typer.Option(
        True,
        "--list",
        "-l",
        help="List branches",
    ),
    create: Optional[str] = typer.Option(
        None,
        "--create",
        "-c",
        help="Create new branch",
    ),
    from_commit: Optional[str] = typer.Option(
        None,
        "--from",
        "-f",
        help="Create branch from commit SHA",
    ),
    remote: bool = typer.Option(
        False,
        "--remote",
        "-r",
        help="Show remote branches",
    ),
    uri: str = typer.Option(
        "bolt://localhost:7687",
        "--uri",
        "-u",
        help="Neo4j connection URI",
    ),
    user: str = typer.Option(
        "neo4j",
        "--user",
        help="Neo4j username",
    ),
    password: str = typer.Option(
        "password",
        "--password",
        "-p",
        help="Neo4j password",
    ),
) -> None:
    """Manage branches (equivalent to git branch)."""
    try:
        with CypherGitOps(uri, user, password) as ops:
            if create:
                # TODO: Implement branch creation via Neo4j
                console.print(f"[yellow]Branch creation not yet implemented: {create}[/yellow]")
                return

            if list_branches:
                branches = ops.branch_list(remote=remote)

                if not branches:
                    console.print("[yellow]No branches found[/yellow]")
                    return

                table = Table(title="Branches" if not remote else "Remote Branches")
                table.add_column("Name", style="cyan")
                table.add_column("Commit SHA", style="yellow")
                table.add_column("Last Commit", style="green")

                for branch_info in branches:
                    name = branch_info['name']
                    if branch_info['is_head']:
                        name = f"* {name}"

                    table.add_row(
                        name,
                        branch_info['commit_sha'][:8],
                        str(branch_info.get('last_commit_time', 'N/A')),
                    )

                console.print(table)

    except Exception as e:
        console.print(f"[red]Failed to list branches: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def stats(
    authors: bool = typer.Option(
        True,
        "--authors/--no-authors",
        help="Show author statistics",
    ),
    activity: bool = typer.Option(
        False,
        "--activity",
        help="Show commit activity",
    ),
    days: int = typer.Option(
        30,
        "--days",
        "-d",
        help="Days for activity analysis",
    ),
    limit: int = typer.Option(
        20,
        "--limit",
        "-n",
        help="Number of results",
    ),
    uri: str = typer.Option(
        "bolt://localhost:7687",
        "--uri",
        "-u",
        help="Neo4j connection URI",
    ),
    user: str = typer.Option(
        "neo4j",
        "--user",
        help="Neo4j username",
    ),
    password: str = typer.Option(
        "password",
        "--password",
        "-p",
        help="Neo4j password",
    ),
) -> None:
    """Show repository statistics and analytics."""
    try:
        with CypherGitOps(uri, user, password) as ops:
            if authors:
                author_stats = ops.author_stats(limit=limit)

                if not author_stats:
                    console.print("[yellow]No author statistics available[/yellow]")
                    return

                table = Table(title="Author Statistics")
                table.add_column("Author", style="cyan")
                table.add_column("Email", style="blue")
                table.add_column("Commits", style="green", justify="right")
                table.add_column("First Commit", style="yellow")
                table.add_column("Last Commit", style="yellow")

                for stat in author_stats:
                    table.add_row(
                        stat['name'],
                        stat['email'],
                        str(stat['commit_count']),
                        str(stat.get('first_commit', 'N/A')),
                        str(stat.get('last_commit', 'N/A')),
                    )

                console.print(table)

            if activity:
                activity_data = ops.commit_activity(days=days)

                if not activity_data:
                    console.print(f"[yellow]No activity in last {days} days[/yellow]")
                    return

                table = Table(title=f"Commit Activity (Last {days} Days)")
                table.add_column("Date", style="cyan")
                table.add_column("Commits", style="green", justify="right")

                for data in activity_data:
                    table.add_row(
                        str(data['commit_date']),
                        str(data['count']),
                    )

                console.print(table)

    except Exception as e:
        console.print(f"[red]Failed to fetch statistics: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def cypher(
    query: str = typer.Argument(..., help="Cypher query to execute"),
    uri: str = typer.Option(
        "bolt://localhost:7687",
        "--uri",
        "-u",
        help="Neo4j connection URI",
    ),
    user: str = typer.Option(
        "neo4j",
        "--user",
        help="Neo4j username",
    ),
    password: str = typer.Option(
        "password",
        "--password",
        "-p",
        help="Neo4j password",
    ),
) -> None:
    """Execute custom Cypher query."""
    try:
        with CypherGitOps(uri, user, password) as ops:
            results = ops.execute_cypher(query)

            if not results:
                console.print("[yellow]Query returned no results[/yellow]")
                return

            # Display results as table
            if results:
                table = Table(title="Query Results")

                # Add columns from first result
                for key in results[0].keys():
                    table.add_column(key, style="cyan")

                # Add rows
                for result in results:
                    table.add_row(*[str(v) for v in result.values()])

                console.print(table)

    except Exception as e:
        console.print(f"[red]Query failed: {e}[/red]")
        raise typer.Exit(1)


@app.command(name="github-sync")
def github_sync(
    repo: str = typer.Argument(
        ...,
        help="GitHub repository in format 'owner/repo'",
    ),
    uri: str = typer.Option(
        "bolt://localhost:7687",
        "--uri",
        "-u",
        help="Neo4j connection URI",
    ),
    user: str = typer.Option(
        "neo4j",
        "--user",
        help="Neo4j username",
    ),
    password: str = typer.Option(
        "password",
        "--password",
        "-p",
        help="Neo4j password",
    ),
    database: str = typer.Option(
        "neo4j",
        "--database",
        "-d",
        help="Neo4j database name",
    ),
    github_token: str = typer.Option(
        None,
        "--token",
        "-t",
        envvar="GITHUB_TOKEN",
        help="GitHub personal access token",
    ),
    sync_trees: bool = typer.Option(
        True,
        "--trees/--no-trees",
        help="Sync tree objects",
    ),
) -> None:
    """Sync a GitHub repository to Neo4j without cloning."""
    from git2neo4j.github.sync import sync_github_repository

    try:
        # Parse owner/repo
        if "/" not in repo:
            console.print("[red]Error: Repository must be in format 'owner/repo'[/red]")
            raise typer.Exit(1)

        owner, repo_name = repo.split("/", 1)

        console.print(f"[bold blue]Syncing GitHub repository:[/bold blue] {owner}/{repo_name}")
        console.print(f"[bold blue]Neo4j URI:[/bold blue] {uri}\n")

        stats = sync_github_repository(
            owner=owner,
            repo=repo_name,
            neo4j_uri=uri,
            neo4j_user=user,
            neo4j_password=password,
            neo4j_database=database,
            github_token=github_token,
            sync_trees=sync_trees,
        )

        # Display statistics
        table = Table(title="Sync Statistics")
        table.add_column("Object Type", style="cyan")
        table.add_column("Count", style="green", justify="right")

        table.add_row("Commits", str(stats["commits"]))
        table.add_row("Branches", str(stats["branches"]))
        table.add_row("Tags", str(stats["tags"]))
        table.add_row("Trees", str(stats["trees"]))

        console.print(table)
        console.print("[bold green]✓ GitHub repository synced successfully![/bold green]")

    except Exception as e:
        console.print(f"[red]Sync failed: {e}[/red]")
        raise typer.Exit(1)


@app.command(name="github-org")
def github_org(
    org: str = typer.Argument(
        ...,
        help="GitHub organization name",
    ),
    uri: str = typer.Option(
        "bolt://localhost:7687",
        "--uri",
        "-u",
        help="Neo4j connection URI",
    ),
    user: str = typer.Option(
        "neo4j",
        "--user",
        help="Neo4j username",
    ),
    password: str = typer.Option(
        "password",
        "--password",
        "-p",
        help="Neo4j password",
    ),
    database: str = typer.Option(
        "neo4j",
        "--database",
        "-d",
        help="Neo4j database name",
    ),
    github_token: str = typer.Option(
        None,
        "--token",
        "-t",
        envvar="GITHUB_TOKEN",
        help="GitHub personal access token",
    ),
    sync_trees: bool = typer.Option(
        True,
        "--trees/--no-trees",
        help="Sync tree objects",
    ),
    max_repos: int = typer.Option(
        None,
        "--max-repos",
        "-m",
        help="Maximum number of repositories to sync",
    ),
) -> None:
    """Sync all repositories from a GitHub organization."""
    from git2neo4j.github.sync import sync_github_organization

    try:
        console.print(f"[bold blue]Syncing GitHub organization:[/bold blue] {org}\n")

        stats = sync_github_organization(
            org=org,
            neo4j_uri=uri,
            neo4j_user=user,
            neo4j_password=password,
            neo4j_database=database,
            github_token=github_token,
            sync_trees=sync_trees,
            max_repos=max_repos,
        )

        # Display summary
        console.print("\n[bold green]✓ Organization sync complete![/bold green]")
        console.print(f"Repositories synced: {stats['repositories']}")
        console.print(f"Total commits: {stats['total_commits']}")
        console.print(f"Total branches: {stats['total_branches']}")

        if stats['errors']:
            console.print(f"\n[yellow]Errors: {len(stats['errors'])}[/yellow]")
            for error in stats['errors'][:5]:
                console.print(f"  - {error['repository']}: {error['error']}")

    except Exception as e:
        console.print(f"[red]Sync failed: {e}[/red]")
        raise typer.Exit(1)


@app.command(name="github-user")
def github_user(
    username: str = typer.Argument(
        ...,
        help="GitHub username",
    ),
    uri: str = typer.Option(
        "bolt://localhost:7687",
        "--uri",
        "-u",
        help="Neo4j connection URI",
    ),
    user: str = typer.Option(
        "neo4j",
        "--user",
        help="Neo4j username",
    ),
    password: str = typer.Option(
        "password",
        "--password",
        "-p",
        help="Neo4j password",
    ),
    database: str = typer.Option(
        "neo4j",
        "--database",
        "-d",
        help="Neo4j database name",
    ),
    github_token: str = typer.Option(
        None,
        "--token",
        "-t",
        envvar="GITHUB_TOKEN",
        help="GitHub personal access token",
    ),
    sync_trees: bool = typer.Option(
        True,
        "--trees/--no-trees",
        help="Sync tree objects",
    ),
    type_filter: str = typer.Option(
        "owner",
        "--type",
        help="Repository type filter (owner, member, all)",
    ),
    max_repos: int = typer.Option(
        None,
        "--max-repos",
        "-m",
        help="Maximum number of repositories to sync",
    ),
) -> None:
    """Sync all repositories for a GitHub user."""
    from git2neo4j.github.sync import sync_github_user_repos

    try:
        console.print(f"[bold blue]Syncing GitHub user repositories:[/bold blue] {username}\n")

        stats = sync_github_user_repos(
            username=username,
            neo4j_uri=uri,
            neo4j_user=user,
            neo4j_password=password,
            neo4j_database=database,
            github_token=github_token,
            sync_trees=sync_trees,
            type_filter=type_filter,
            max_repos=max_repos,
        )

        # Display summary
        console.print("\n[bold green]✓ User repositories synced![/bold green]")
        console.print(f"Repositories synced: {stats['repositories']}")
        console.print(f"Total commits: {stats['total_commits']}")
        console.print(f"Total branches: {stats['total_branches']}")

        if stats['errors']:
            console.print(f"\n[yellow]Errors: {len(stats['errors'])}[/yellow]")

    except Exception as e:
        console.print(f"[red]Sync failed: {e}[/red]")
        raise typer.Exit(1)


@app.command(name="install-hook")
def install_hook(
    repo_path: str = typer.Argument(
        ".",
        help="Path to Git repository",
    ),
    hook_type: str = typer.Option(
        "post-commit",
        "--hook",
        "-h",
        help="Hook type to install (post-commit, post-receive, github-action)",
    ),
    config_only: bool = typer.Option(
        False,
        "--config-only",
        help="Only create configuration file",
    ),
) -> None:
    """Install Git hook for automatic Neo4j synchronization."""
    from git2neo4j.hooks.install_hooks import (
        add_to_gitignore,
        create_config_file,
        install_github_action,
        install_local_hook,
    )

    repo_path_obj = Path(repo_path).resolve()

    if not repo_path_obj.exists():
        console.print(f"[red]Error: Repository path does not exist: {repo_path}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold blue]Installing Git2Neo4j hooks in:[/bold blue] {repo_path_obj}\n")

    # Create configuration file
    if config_only or hook_type != "github-action":
        create_config_file(repo_path_obj)
        add_to_gitignore(repo_path_obj)

    if config_only:
        console.print("\n[green]✓ Configuration file created![/green]")
        console.print("Edit .git2neo4j.conf to set your Neo4j connection details.")
        return

    # Install hooks
    try:
        if hook_type == "github-action":
            success = install_github_action(repo_path_obj)
        else:
            success = install_local_hook(repo_path_obj, hook_type)

        if success:
            console.print("\n[bold green]✓ Installation complete![/bold green]")
            if hook_type == "github-action":
                console.print("\nAdd GitHub secrets and commit the workflow file.")
            else:
                console.print("\nMake a commit to test the hook.")
                console.print("Configure Neo4j connection in .git2neo4j.conf")
        else:
            console.print("\n[red]✗ Installation failed![/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Installation error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show version information."""
    from git2neo4j import __version__

    console.print(f"[bold blue]git2neo4j[/bold blue] version [green]{__version__}[/green]")


if __name__ == "__main__":
    app()
