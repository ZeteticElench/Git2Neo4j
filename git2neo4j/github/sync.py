"""Sync GitHub repositories to Neo4j using GitHub API."""

import os
from pathlib import Path
from typing import Any

from git2neo4j.github.api_client import GitHubAPIClient, GitHubConfig, GitHubToGitAdapter
from git2neo4j.sync.git_to_neo4j import GitToNeo4jSync


def sync_github_repository(
    owner: str,
    repo: str,
    neo4j_uri: str = "bolt://localhost:7687",
    neo4j_user: str = "neo4j",
    neo4j_password: str = "password",
    neo4j_database: str = "neo4j",
    github_token: str | None = None,
    batch_size: int = 100,
    sync_trees: bool = True,
    create_schema: bool = True,
) -> dict[str, int]:
    """Sync a GitHub repository directly to Neo4j without local clone.

    Args:
        owner: GitHub repository owner (user or organization)
        repo: Repository name
        neo4j_uri: Neo4j connection URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password
        neo4j_database: Neo4j database name
        github_token: GitHub personal access token (optional, for private repos)
        batch_size: Batch size for operations
        sync_trees: Whether to sync tree objects
        create_schema: Whether to create schema

    Returns:
        Dictionary with sync statistics

    Example:
        >>> stats = sync_github_repository(
        ...     owner="torvalds",
        ...     repo="linux",
        ...     github_token=os.getenv("GITHUB_TOKEN"),
        ... )
        >>> print(f"Synced {stats['commits']} commits")
    """
    # Initialize GitHub API client
    github_config = GitHubConfig(
        token=github_token or os.getenv("GITHUB_TOKEN"),
    )
    client = GitHubAPIClient(github_config)

    # Create adapter
    adapter = GitHubToGitAdapter(client, owner, repo)

    # Sync using adapter (duck typing - adapter has same interface as GitParser)
    return _sync_with_adapter(
        adapter=adapter,
        repo_name=repo,
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password,
        neo4j_database=neo4j_database,
        batch_size=batch_size,
        sync_trees=sync_trees,
        create_schema=create_schema,
    )


def sync_github_organization(
    org: str,
    neo4j_uri: str = "bolt://localhost:7687",
    neo4j_user: str = "neo4j",
    neo4j_password: str = "password",
    neo4j_database: str = "neo4j",
    github_token: str | None = None,
    batch_size: int = 100,
    sync_trees: bool = True,
    max_repos: int | None = None,
) -> dict[str, Any]:
    """Sync all repositories from a GitHub organization.

    Args:
        org: GitHub organization name
        neo4j_uri: Neo4j connection URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password
        neo4j_database: Neo4j database name
        github_token: GitHub personal access token
        batch_size: Batch size for operations
        sync_trees: Whether to sync tree objects
        max_repos: Maximum repositories to sync (None = all)

    Returns:
        Dictionary with overall statistics
    """
    github_config = GitHubConfig(
        token=github_token or os.getenv("GITHUB_TOKEN"),
    )
    client = GitHubAPIClient(github_config)

    # Get all org repositories
    repos = client.get_org_repositories(org)

    if max_repos:
        repos = repos[:max_repos]

    print(f"Found {len(repos)} repositories in {org}")

    stats = {
        "repositories": 0,
        "total_commits": 0,
        "total_branches": 0,
        "total_tags": 0,
        "errors": [],
    }

    for idx, repo_data in enumerate(repos, 1):
        repo_name = repo_data["name"]
        print(f"[{idx}/{len(repos)}] Syncing {org}/{repo_name}...")

        try:
            repo_stats = sync_github_repository(
                owner=org,
                repo=repo_name,
                neo4j_uri=neo4j_uri,
                neo4j_user=neo4j_user,
                neo4j_password=neo4j_password,
                neo4j_database=neo4j_database,
                github_token=github_token,
                batch_size=batch_size,
                sync_trees=sync_trees,
                create_schema=(idx == 1),  # Only create schema for first repo
            )

            stats["repositories"] += 1
            stats["total_commits"] += repo_stats.get("commits", 0)
            stats["total_branches"] += repo_stats.get("branches", 0)
            stats["total_tags"] += repo_stats.get("tags", 0)

            print(f"  ✓ {repo_stats.get('commits', 0)} commits")

        except Exception as e:
            stats["errors"].append({"repository": f"{org}/{repo_name}", "error": str(e)})
            print(f"  ✗ Error: {e}")

    return stats


def sync_github_user_repos(
    username: str,
    neo4j_uri: str = "bolt://localhost:7687",
    neo4j_user: str = "neo4j",
    neo4j_password: str = "password",
    neo4j_database: str = "neo4j",
    github_token: str | None = None,
    batch_size: int = 100,
    sync_trees: bool = True,
    type_filter: str = "owner",
    max_repos: int | None = None,
) -> dict[str, Any]:
    """Sync all repositories for a GitHub user.

    Args:
        username: GitHub username
        neo4j_uri: Neo4j connection URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password
        neo4j_database: Neo4j database name
        github_token: GitHub personal access token
        batch_size: Batch size for operations
        sync_trees: Whether to sync tree objects
        type_filter: Repository type filter (owner, member, all)
        max_repos: Maximum repositories to sync (None = all)

    Returns:
        Dictionary with overall statistics
    """
    github_config = GitHubConfig(
        token=github_token or os.getenv("GITHUB_TOKEN"),
    )
    client = GitHubAPIClient(github_config)

    # Get all user repositories
    repos = client.get_user_repositories(username, type_filter)

    if max_repos:
        repos = repos[:max_repos]

    print(f"Found {len(repos)} repositories for {username}")

    stats = {
        "repositories": 0,
        "total_commits": 0,
        "total_branches": 0,
        "total_tags": 0,
        "errors": [],
    }

    for idx, repo_data in enumerate(repos, 1):
        repo_name = repo_data["name"]
        repo_owner = repo_data["owner"]["login"]
        print(f"[{idx}/{len(repos)}] Syncing {repo_owner}/{repo_name}...")

        try:
            repo_stats = sync_github_repository(
                owner=repo_owner,
                repo=repo_name,
                neo4j_uri=neo4j_uri,
                neo4j_user=neo4j_user,
                neo4j_password=neo4j_password,
                neo4j_database=neo4j_database,
                github_token=github_token,
                batch_size=batch_size,
                sync_trees=sync_trees,
                create_schema=(idx == 1),
            )

            stats["repositories"] += 1
            stats["total_commits"] += repo_stats.get("commits", 0)
            stats["total_branches"] += repo_stats.get("branches", 0)
            stats["total_tags"] += repo_stats.get("tags", 0)

            print(f"  ✓ {repo_stats.get('commits', 0)} commits")

        except Exception as e:
            stats["errors"].append(
                {"repository": f"{repo_owner}/{repo_name}", "error": str(e)}
            )
            print(f"  ✗ Error: {e}")

    return stats


def _sync_with_adapter(
    adapter: GitHubToGitAdapter,
    repo_name: str,
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    neo4j_database: str,
    batch_size: int,
    sync_trees: bool,
    create_schema: bool,
) -> dict[str, int]:
    """Internal method to sync using GitHubToGitAdapter.

    This reuses the GitToNeo4jSync logic by substituting the adapter
    for the GitParser (duck typing).

    Args:
        adapter: GitHub to Git adapter
        repo_name: Repository name
        neo4j_uri: Neo4j URI
        neo4j_user: Neo4j user
        neo4j_password: Neo4j password
        neo4j_database: Neo4j database
        batch_size: Batch size
        sync_trees: Sync trees flag
        create_schema: Create schema flag

    Returns:
        Sync statistics
    """
    from git2neo4j.sync.git_to_neo4j import GitToNeo4jSync
    from neo4j import GraphDatabase

    # Get repository info
    repo_info = adapter.get_repository_info()

    # Initialize sync engine (without parser)
    sync = GitToNeo4jSync.__new__(GitToNeo4jSync)
    sync.repo_path = Path(repo_info.path)
    sync.parser = adapter  # Use adapter as parser!
    sync.batch_size = batch_size
    sync.sync_trees = sync_trees
    sync.sync_blobs = False

    # Initialize Neo4j driver
    sync.driver = GraphDatabase.driver(
        neo4j_uri,
        auth=(neo4j_user, neo4j_password),
    )
    sync.database = neo4j_database

    try:
        # Set up schema if needed
        if create_schema:
            sync.setup_schema()

        stats = {
            "commits": 0,
            "trees": 0,
            "blobs": 0,
            "tags": 0,
            "branches": 0,
            "authors": 0,
        }

        # Sync repository metadata
        sync._sync_repository_node(repo_info)

        # Sync commits
        commits = list(adapter.get_all_commits())
        stats["commits"] = len(commits)
        sync._sync_commits_batch(commits, repo_name, repo_info.path)

        # Sync branches
        stats["branches"] = len(repo_info.branches)
        sync._sync_branches_batch(repo_info.branches, repo_name, repo_info.path)

        # Sync tags
        tags = list(adapter.get_all_tags())
        stats["tags"] = len(tags)
        sync._sync_tags_batch(tags, repo_name)

        # Optionally sync trees
        if sync_trees and commits:
            tree_count = sync._sync_all_trees(commits, repo_name)
            stats["trees"] = tree_count

        # Update repository stats
        sync._update_repository_stats(repo_info, stats)

        return stats

    finally:
        sync.close()
