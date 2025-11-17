# Git2Neo4j Quick Start Guide

This guide will help you get started with Git2Neo4j in minutes.

## Prerequisites

1. **Python 3.10+** installed
2. **Neo4j database** running (either locally or remotely)
3. **Git repository** you want to sync

## Installation

```bash
pip install git2neo4j
```

Or install from source:

```bash
git clone https://github.com/ZeteticElench/Git2Neo4j.git
cd Git2Neo4j
pip install -e .
```

## Step 1: Start Neo4j

If you don't have Neo4j running, the easiest way is using Docker:

```bash
docker run \
    --name neo4j \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/password \
    neo4j:latest
```

Access the Neo4j Browser at http://localhost:7474

## Step 2: Sync Your First Repository

### Using the CLI

```bash
# Sync the current directory
git2neo4j sync . --uri bolt://localhost:7687 --password password

# Sync a specific repository
git2neo4j sync /path/to/repo --uri bolt://localhost:7687 --password password
```

### Using Python

```python
from git2neo4j import GitToNeo4jSync

with GitToNeo4jSync(
    repo_path="/path/to/repo",
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="password",
) as sync:
    stats = sync.sync_repository()
    print(f"Synced {stats['commits']} commits!")
```

## Step 3: Query Git Data with Cypher

### Using the CLI

```bash
# Show commit log
git2neo4j log --branch main --limit 10

# Show specific commit
git2neo4j show abc123def456

# List branches
git2neo4j branch --list

# Show repository statistics
git2neo4j stats --authors --limit 20
```

### Using Python

```python
from git2neo4j.queries import CypherGitOps

with CypherGitOps("bolt://localhost:7687", "neo4j", "password") as ops:
    # Get commit log
    commits = ops.log(branch="main", limit=10)
    for commit in commits:
        print(f"{commit['sha'][:8]} - {commit['message']}")

    # Get author statistics
    authors = ops.author_stats(limit=10)
    for author in authors:
        print(f"{author['name']}: {author['commit_count']} commits")
```

### Using Cypher Directly in Neo4j Browser

```cypher
// Show all commits on main branch
MATCH (b:Branch {name: "main"})-[:POINTS_TO]->(c:Commit)
MATCH path = (c)-[:PARENT*0..]->(ancestor:Commit)
RETURN ancestor
ORDER BY ancestor.author_timestamp DESC
LIMIT 10

// Find merge commits
MATCH (c:Commit)
WHERE c.parent_count > 1
RETURN c.sha, c.message, c.author_name
ORDER BY c.author_timestamp DESC

// Show most active authors
MATCH (a:Author)<-[:AUTHORED_BY]-(c:Commit)
WITH a, count(c) as commits
RETURN a.name, a.email, commits
ORDER BY commits DESC
LIMIT 10

// Find files changed most frequently
MATCH (c:Commit)-[:TREE]->(:Tree)-[:HAS_ENTRY*]->(b:Blob)
WHERE b.path IS NOT NULL
WITH b.path as file, count(DISTINCT c) as changes
RETURN file, changes
ORDER BY changes DESC
LIMIT 10
```

## Step 4: Advanced Use Cases

### Incremental Sync

```python
# Only sync new commits since last sync
stats = sync.sync_incremental()
```

### Custom Analytics

```python
# Execute custom Cypher query
query = """
MATCH (c:Commit)
WHERE c.author_timestamp >= datetime() - duration({days: 30})
RETURN count(c) as commits_last_30_days
"""
results = ops.execute_cypher(query)
print(results[0]['commits_last_30_days'])
```

### Branch Management

```python
from git2neo4j.sync import Neo4jToGitSync

with Neo4jToGitSync("/path/to/repo", "bolt://localhost:7687", "neo4j", "password") as sync:
    # Create branch from Neo4j
    sync.create_branch_from_neo4j("feature-branch", from_commit_sha="abc123")
```

## Configuration with Environment Variables

Create a `.env` file:

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
GIT_REPO_PATH=/path/to/repo
```

Then use without specifying parameters:

```python
from git2neo4j import GitToNeo4jSync
from git2neo4j.config import Config

config = Config.from_env()

with GitToNeo4jSync(
    repo_path=config.git.repo_path,
    neo4j_uri=config.neo4j.uri,
    neo4j_user=config.neo4j.user,
    neo4j_password=config.neo4j.password,
) as sync:
    sync.sync_repository()
```

## Next Steps

- Read the [Architecture Guide](ARCHITECTURE.md) to understand the graph model
- See [Examples](../examples/) for more use cases
- Check [Cypher Query Examples](CYPHER_EXAMPLES.md) for advanced queries
- Learn about [Bidirectional Sync](BIDIRECTIONAL_SYNC.md)

## Troubleshooting

### Connection Issues

```python
# Verify Neo4j connection
if not sync.verify_connection():
    print("Cannot connect to Neo4j!")
    print("Check URI, username, and password")
```

### Large Repositories

For large repositories, use batch processing and disable blob sync:

```python
with GitToNeo4jSync(
    repo_path="/path/to/large/repo",
    batch_size=50,  # Smaller batches
    sync_trees=False,  # Skip trees for initial sync
    sync_blobs=False,  # Skip blobs
) as sync:
    sync.sync_repository()
```

### Performance Tuning

```python
# Adjust batch size for your use case
sync = GitToNeo4jSync(
    batch_size=200,  # Larger batches for faster sync
    sync_trees=True,
    sync_blobs=False,  # Blobs can be large
)
```
