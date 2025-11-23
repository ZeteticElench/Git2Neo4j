"""Example: Syncing GitHub repositories using the GitHub API."""

import os

from git2neo4j.github import sync_github_repository
from git2neo4j.github.sync import sync_github_organization, sync_github_user_repos


def example_sync_single_repo() -> None:
    """Sync a single GitHub repository."""
    print("=== Syncing Single GitHub Repository ===\n")

    # Public repository (no token needed)
    stats = sync_github_repository(
        owner="torvalds",
        repo="linux",
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        sync_trees=True,
    )

    print(f"\nSynced {stats['commits']} commits from torvalds/linux")


def example_sync_private_repo() -> None:
    """Sync a private GitHub repository (requires token)."""
    print("=== Syncing Private GitHub Repository ===\n")

    # Get token from environment
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable not set")
        return

    stats = sync_github_repository(
        owner="your-username",
        repo="your-private-repo",
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        github_token=github_token,
        sync_trees=True,
    )

    print(f"\nSynced {stats['commits']} commits")


def example_sync_organization() -> None:
    """Sync all repositories from a GitHub organization."""
    print("=== Syncing GitHub Organization ===\n")

    github_token = os.getenv("GITHUB_TOKEN")

    stats = sync_github_organization(
        org="anthropics",  # Example organization
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        github_token=github_token,
        sync_trees=True,
        max_repos=5,  # Limit to first 5 repos for testing
    )

    print(f"\nTotal repositories: {stats['repositories']}")
    print(f"Total commits: {stats['total_commits']}")
    print(f"Total branches: {stats['total_branches']}")


def example_sync_user_repos() -> None:
    """Sync all repositories for a GitHub user."""
    print("=== Syncing GitHub User Repositories ===\n")

    github_token = os.getenv("GITHUB_TOKEN")

    stats = sync_github_user_repos(
        username="guido",  # Example: Guido van Rossum
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        github_token=github_token,
        type_filter="owner",  # Only repos they own
        max_repos=10,
    )

    print(f"\nTotal repositories: {stats['repositories']}")
    print(f"Total commits: {stats['total_commits']}")


def example_cli_usage() -> None:
    """Examples of using CLI for GitHub sync."""
    print("=== CLI Usage Examples ===\n")

    print("1. Sync single repository:")
    print("   export GITHUB_TOKEN=your_token_here")
    print("   git2neo4j github-sync torvalds/linux --uri bolt://localhost:7687 -p password\n")

    print("2. Sync organization:")
    print("   git2neo4j github-org anthropics --token $GITHUB_TOKEN -p password\n")

    print("3. Sync user repositories:")
    print("   git2neo4j github-user guido --type owner --max-repos 10 -p password\n")

    print("4. With custom database:")
    print("   git2neo4j github-sync owner/repo -d github_repos -p password\n")


def example_rate_limiting() -> None:
    """Example: Handling GitHub API rate limiting."""
    print("=== GitHub API Rate Limiting ===\n")

    from git2neo4j.github import GitHubAPIClient, GitHubConfig

    # Configure client with rate limit handling
    config = GitHubConfig(
        token=os.getenv("GITHUB_TOKEN"),
        rate_limit_wait=True,  # Wait when rate limit is hit
        max_retries=3,
    )

    client = GitHubAPIClient(config)

    # Rate limits:
    # - Authenticated: 5,000 requests/hour
    # - Unauthenticated: 60 requests/hour
    #
    # The client will automatically:
    # 1. Wait when rate limit is hit
    # 2. Retry on server errors
    # 3. Handle pagination

    print("Client configured with automatic rate limit handling")
    print("Authenticated: 5,000 requests/hour")
    print("Unauthenticated: 60 requests/hour")


def example_query_github_data() -> None:
    """Example: Query GitHub data in Neo4j after sync."""
    print("=== Querying GitHub Data in Neo4j ===\n")

    from git2neo4j.queries import CypherGitOps

    with CypherGitOps("bolt://localhost:7687", "neo4j", "password") as ops:
        # Find all GitHub repositories
        query = """
        MATCH (r:Repository)
        WHERE r.path STARTS WITH 'github.com/'
        RETURN r.name as repo,
               r.commit_count as commits,
               r.path as github_path
        ORDER BY commits DESC
        LIMIT 10
        """
        results = ops.execute_cypher(query)

        print("Top GitHub repositories by commit count:")
        for r in results:
            print(f"  {r['github_path']}: {r['commits']} commits")


def example_compare_github_users() -> None:
    """Example: Compare activity between GitHub users."""
    print("=== Comparing GitHub Users ===\n")

    from git2neo4j.queries import CypherGitOps

    with CypherGitOps("bolt://localhost:7687", "neo4j", "password") as ops:
        # Compare commit activity
        query = """
        MATCH (c:Commit)
        WHERE c.repo_name IN $repos
        WITH c.author_email as author,
             count(c) as commits,
             collect(DISTINCT c.repo_name) as repos
        RETURN author, commits, repos
        ORDER BY commits DESC
        LIMIT 10
        """

        # Compare two GitHub organizations
        results = ops.execute_cypher(query, {"repos": ["repo1", "repo2"]})

        print("Most active contributors:")
        for r in results:
            print(f"  {r['author']}: {r['commits']} commits across {len(r['repos'])} repos")


def example_cross_repo_patterns() -> None:
    """Example: Find patterns across GitHub repositories."""
    print("=== Finding Cross-Repository Patterns ===\n")

    from git2neo4j.queries import CypherGitOps

    with CypherGitOps("bolt://localhost:7687", "neo4j", "password") as ops:
        # Find common file patterns
        query = """
        MATCH (b:Blob)
        WHERE b.path ENDS WITH '.py'
          AND b.text_content IS NOT NULL
        WITH b.path as filename,
             count(DISTINCT b.repo_name) as repo_count,
             collect(DISTINCT b.repo_name) as repos
        WHERE repo_count > 1
        RETURN filename, repo_count, repos
        ORDER BY repo_count DESC
        LIMIT 10
        """

        results = ops.execute_cypher(query)

        print("Common Python files across repositories:")
        for r in results:
            print(f"  {r['filename']}: in {r['repo_count']} repositories")


if __name__ == "__main__":
    print("Git2Neo4j GitHub API Integration Examples\n")
    print("=" * 60)
    print()

    # Set your GitHub token
    # export GITHUB_TOKEN=ghp_your_token_here

    # Choose which example to run:

    # Example 1: Single public repository
    # example_sync_single_repo()

    # Example 2: Private repository (requires token)
    # example_sync_private_repo()

    # Example 3: Organization
    # example_sync_organization()

    # Example 4: User repositories
    # example_sync_user_repos()

    # Example 5: CLI usage
    example_cli_usage()

    # Example 6: Rate limiting
    # example_rate_limiting()

    # Example 7: Query synced data
    # example_query_github_data()

    # Example 8: Compare users
    # example_compare_github_users()

    # Example 9: Cross-repo patterns
    # example_cross_repo_patterns()

    print("\nNote: Set GITHUB_TOKEN environment variable for private repos and higher rate limits!")
