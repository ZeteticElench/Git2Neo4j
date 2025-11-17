"""Example: Using Cypher queries for Git operations."""

from git2neo4j.queries.cypher_ops import CypherGitOps


def main() -> None:
    """Demonstrate Git operations via Cypher queries."""
    # Configuration
    neo4j_uri = "bolt://localhost:7687"
    neo4j_user = "neo4j"
    neo4j_password = "password"

    with CypherGitOps(neo4j_uri, neo4j_user, neo4j_password) as ops:
        # Example 1: Git log equivalent
        print("=== Git Log (last 5 commits on main) ===")
        commits = ops.log(branch="main", limit=5)
        for commit in commits:
            print(f"{commit['sha'][:8]} - {commit['message'].strip()}")
            print(f"  Author: {commit['author_name']} <{commit['author_email']}>")
            print()

        # Example 2: Show specific commit
        print("\n=== Git Show (specific commit) ===")
        if commits:
            first_commit = commits[0]
            details = ops.show(first_commit['sha'])
            if details:
                print(f"Commit: {details['sha']}")
                print(f"Message: {details['message']}")
                print(f"Tree: {details['tree_sha']}")
                print(f"Parents: {details['parent_shas']}")
                print()

        # Example 3: List branches
        print("\n=== Git Branch (list branches) ===")
        branches = ops.branch_list(remote=False)
        for branch in branches:
            marker = "*" if branch['is_head'] else " "
            print(f"{marker} {branch['name']}")
        print()

        # Example 4: Author statistics
        print("\n=== Author Statistics ===")
        authors = ops.author_stats(limit=10)
        for author in authors:
            print(f"{author['name']} <{author['email']}>")
            print(f"  Commits: {author['commit_count']}")
            print(f"  First: {author['first_commit']}")
            print(f"  Last: {author['last_commit']}")
            print()

        # Example 5: File history
        print("\n=== File History (README.md) ===")
        file_commits = ops.file_history("README.md", branch="main", limit=5)
        for fc in file_commits:
            print(f"{fc['sha'][:8]} - {fc['message'].strip()}")
            print(f"  Author: {fc['author_name']}")
            print()

        # Example 6: Find merge base (common ancestor)
        print("\n=== Merge Base ===")
        if len(commits) >= 2:
            commit1 = commits[0]['sha']
            commit2 = commits[1]['sha']
            merge_base = ops.merge_base(commit1, commit2)
            if merge_base:
                print(f"Common ancestor of {commit1[:8]} and {commit2[:8]}:")
                print(f"  {merge_base['sha'][:8]} - {merge_base['message'].strip()}")
                print()

        # Example 7: Custom Cypher query
        print("\n=== Custom Cypher Query ===")
        query = """
        MATCH (c:Commit)
        WHERE c.parent_count > 1
        RETURN c.sha as sha, c.message as message, c.parent_count as parents
        ORDER BY c.author_timestamp DESC
        LIMIT 5
        """
        merge_commits = ops.execute_cypher(query)
        print("Recent merge commits:")
        for mc in merge_commits:
            print(f"{mc['sha'][:8]} - {mc['message'].strip()} ({mc['parents']} parents)")


if __name__ == "__main__":
    main()
