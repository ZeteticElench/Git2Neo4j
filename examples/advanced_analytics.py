"""Advanced example: Git analytics using Neo4j graph algorithms."""

from datetime import datetime, timedelta

from git2neo4j.queries.cypher_ops import CypherGitOps


def main() -> None:
    """Demonstrate advanced analytics using Neo4j."""
    neo4j_uri = "bolt://localhost:7687"
    neo4j_user = "neo4j"
    neo4j_password = "password"

    with CypherGitOps(neo4j_uri, neo4j_user, neo4j_password) as ops:
        # Analytics 1: Most active contributors
        print("=== Top 10 Contributors ===")
        authors = ops.author_stats(limit=10)
        for i, author in enumerate(authors, 1):
            print(f"{i}. {author['name']} - {author['commit_count']} commits")
        print()

        # Analytics 2: Commit activity over time
        print("=== Commit Activity (Last 30 Days) ===")
        activity = ops.commit_activity(days=30)
        for day in activity[:10]:  # Show first 10 days
            print(f"{day['commit_date']}: {day['count']} commits")
        print()

        # Analytics 3: Most connected commits (hubs in the DAG)
        print("=== Most Connected Commits (DAG Hubs) ===")
        connected = ops.most_connected_commits(limit=5)
        for commit in connected:
            print(f"{commit['sha'][:8]} - {commit['message'].strip()}")
            print(f"  Connections: {commit['total_connections']}")
            print(f"  Parents: {commit['parent_count']}, Children: {commit['child_count']}")
            print(f"  Branches: {commit['branch_count']}, Tags: {commit['tag_count']}")
            print()

        # Analytics 4: Branch divergence analysis
        print("=== Branch Divergence Analysis ===")
        branches = ops.branch_list(remote=False)
        if len(branches) >= 2:
            branch1 = branches[0]['name']
            branch2 = branches[1]['name'] if len(branches) > 1 else branch1

            divergence = ops.branch_commits(branch1, branch2)
            print(f"Comparing {branch1} and {branch2}:")
            print(f"  Unique to {branch1}: {len(divergence.get('unique_to_branch1', []))} commits")
            print(f"  Unique to {branch2}: {len(divergence.get('unique_to_branch2', []))} commits")
            print()

        # Analytics 5: Custom analysis - Find files changed most frequently
        print("=== Most Frequently Changed Files ===")
        query = """
        MATCH (c:Commit)-[:TREE]->(:Tree)-[:HAS_ENTRY*]->(b:Blob)
        WHERE b.path IS NOT NULL
        WITH b.path as file_path, count(DISTINCT c) as change_count
        RETURN file_path, change_count
        ORDER BY change_count DESC
        LIMIT 10
        """
        results = ops.execute_cypher(query)
        for result in results:
            print(f"{result['file_path']}: {result['change_count']} changes")
        print()

        # Analytics 6: Collaboration network
        print("=== Collaboration Network (Co-authorship) ===")
        query = """
        MATCH (a1:Author)<-[:AUTHORED_BY]-(c:Commit)-[:PARENT]->(pc:Commit)-[:AUTHORED_BY]->(a2:Author)
        WHERE a1 <> a2
        WITH a1.name as author1, a2.name as author2, count(*) as collaborations
        RETURN author1, author2, collaborations
        ORDER BY collaborations DESC
        LIMIT 10
        """
        results = ops.execute_cypher(query)
        print("Authors who frequently build on each other's work:")
        for result in results:
            print(f"{result['author1']} → {result['author2']}: {result['collaborations']} times")
        print()

        # Analytics 7: Hot spots - Files with most authors
        print("=== Hot Spots (Files Modified by Most Authors) ===")
        query = """
        MATCH (a:Author)<-[:AUTHORED_BY]-(c:Commit)-[:TREE]->(:Tree)-[:HAS_ENTRY*]->(b:Blob)
        WHERE b.path IS NOT NULL
        WITH b.path as file_path, count(DISTINCT a) as author_count
        RETURN file_path, author_count
        ORDER BY author_count DESC
        LIMIT 10
        """
        results = ops.execute_cypher(query)
        for result in results:
            print(f"{result['file_path']}: {result['author_count']} authors")
        print()

        # Analytics 8: Orphaned commits (no children, not pointed to by any branch)
        print("=== Orphaned Commits ===")
        query = """
        MATCH (c:Commit)
        WHERE NOT (c)<-[:PARENT]-(:Commit)
          AND NOT (c)<-[:POINTS_TO]-(:Branch)
          AND NOT (c)<-[:POINTS_TO]-(:Tag)
        RETURN c.sha as sha, c.message as message, c.author_timestamp as timestamp
        ORDER BY c.author_timestamp DESC
        LIMIT 5
        """
        results = ops.execute_cypher(query)
        if results:
            for result in results:
                print(f"{result['sha'][:8]} - {result['message'].strip()}")
        else:
            print("No orphaned commits found")
        print()


if __name__ == "__main__":
    main()
