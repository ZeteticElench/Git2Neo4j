# Git2Neo4j

A strongly-typed Python program that keeps a Neo4j database in sync with Git repositories and enables Git operations via Cypher queries.

## Overview

Git uses a directed acyclic graph (DAG) to track code edits, making it a natural fit to model in Neo4j. Git2Neo4j bridges these two worlds by:

1. **Primary Goal**: Syncing Git repositories to Neo4j databases with full type safety
2. **Secondary Goal**: Enabling Git operations directly in Neo4j using Cypher queries, with changes mirrored back to the Git repository

## Architecture

### Git Object Model in Neo4j

Git2Neo4j models Git's core objects as Neo4j nodes and relationships:

```
Nodes:
- (:Commit)      - Represents a Git commit with metadata
- (:Tree)        - Represents a Git tree (directory snapshot)
- (:Blob)        - Represents a Git blob (file content)
- (:Tag)         - Represents a Git tag
- (:Branch)      - Represents a Git branch reference
- (:Author)      - Represents a commit author
- (:Repository)  - Represents the repository itself

Relationships:
- [:PARENT]      - Links commits to parent commits (DAG structure)
- [:TREE]        - Links commits to their root tree
- [:HAS_ENTRY]   - Links trees to their entries (subtrees or blobs)
- [:POINTS_TO]   - Links branches/tags to commits
- [:AUTHORED_BY] - Links commits to authors
- [:TRACKS]      - Links repository to branches
```

### Key Features

- **Strongly Typed**: Full type safety using Pydantic models
- **Bidirectional Sync**: Changes in Neo4j can be mirrored back to Git
- **Cypher-based Git Operations**: Perform Git operations using Cypher queries
- **Incremental Updates**: Efficient syncing of only changed objects
- **Full History**: Complete Git history preserved in the graph
- **Automatic Sync**: Git hooks for automatic syncing on commit or push
- **Full-Text Search**: Search code content, commit messages, and file paths
- **Bulk Import**: Import entire workspaces of Git repositories
- **Multi-Repository Support**: Manage multiple repositories in single database

## Installation

```bash
pip install git2neo4j
```

Or for development:

```bash
git clone https://github.com/ZeteticElench/Git2Neo4j.git
cd Git2Neo4j
pip install -e ".[dev]"
```

## Quick Start

### 1. Sync a Git Repository to Neo4j

```python
from git2neo4j import GitToNeo4jSync

# Initialize the sync engine
sync = GitToNeo4jSync(
    repo_path="/path/to/git/repo",
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="password"
)

# Perform initial sync
sync.sync_repository()
```

### 2. Query Git History with Cypher

```cypher
// Find all commits by a specific author
MATCH (a:Author {email: "dev@example.com"})-[:AUTHORED]->(c:Commit)
RETURN c.sha, c.message, c.timestamp
ORDER BY c.timestamp DESC

// Find the commit history (equivalent to git log)
MATCH path = (head:Branch {name: "main"})-[:POINTS_TO]->(c:Commit)-[:PARENT*]->(ancestor:Commit)
RETURN path
ORDER BY c.timestamp DESC

// Find files modified in a commit (equivalent to git show)
MATCH (c:Commit {sha: "abc123"})-[:TREE]->(root:Tree)-[:HAS_ENTRY*]->(blob:Blob)
RETURN blob.path, blob.sha

// Find common ancestor (merge base)
MATCH (c1:Commit {sha: "abc123"}), (c2:Commit {sha: "def456"})
MATCH path1 = (c1)-[:PARENT*]->(ancestor:Commit)
MATCH path2 = (c2)-[:PARENT*]->(ancestor)
RETURN ancestor
ORDER BY ancestor.timestamp DESC
LIMIT 1
```

### 3. Use the CLI

```bash
# Sync a repository
git2neo4j sync /path/to/repo --uri bolt://localhost:7687

# Query commits (git log equivalent)
git2neo4j log --branch main --limit 10

# Show commit details (git show equivalent)
git2neo4j show abc123

# List branches
git2neo4j branch --list

# Create a new branch in Neo4j (mirrors to Git)
git2neo4j branch --create feature-branch --from main
```

## Cypher to Git Command Mapping

| Git Command | Cypher Equivalent |
|-------------|-------------------|
| `git log` | `MATCH (b:Branch)-[:POINTS_TO]->(c:Commit)-[:PARENT*]->(h) RETURN h` |
| `git show <sha>` | `MATCH (c:Commit {sha: $sha})-[:TREE]->(:Tree)-[:HAS_ENTRY*]->(entry) RETURN entry` |
| `git branch` | `MATCH (b:Branch) RETURN b.name` |
| `git diff <sha1> <sha2>` | Compare trees between commits |
| `git merge-base <sha1> <sha2>` | Find common ancestor in DAG |
| `git blame <file>` | Traverse commit history for specific blob changes |

## Automatic Sync with Git Hooks

Automatically sync your repository to Neo4j on every commit or push:

### Local Hook (sync on commit)

```bash
# Install post-commit hook
git2neo4j install-hook /path/to/repo

# Configure Neo4j connection
nano .git2neo4j.conf

# Make a commit - it will automatically sync!
git commit -m "Auto-sync to Neo4j"
# Output: ✓ Synced to Neo4j: 1 commits
```

### GitHub Actions (sync on push)

```bash
# Install GitHub Actions workflow
git2neo4j install-hook /path/to/repo --hook github-action

# Add secrets to GitHub repository settings:
# - NEO4J_URI
# - NEO4J_USER
# - NEO4J_PASSWORD

# Commit and push the workflow
git add .github/workflows/sync-to-neo4j.yml
git commit -m "Add Neo4j auto-sync"
git push  # Will automatically sync to Neo4j!
```

**See [Git Hooks Documentation](docs/GIT_HOOKS.md) for detailed setup and configuration options.**

## Configuration

Create a `.env` file or set environment variables:

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
GIT_REPO_PATH=/path/to/repo
```

## Development

### Running Tests

```bash
pytest
```

### Type Checking

```bash
mypy git2neo4j
```

### Code Formatting

```bash
black git2neo4j
ruff check git2neo4j
```

## Project Structure

```
git2neo4j/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── git_objects.py      # Pydantic models for Git objects
│   └── neo4j_schema.py     # Neo4j node/relationship definitions
├── parsers/
│   ├── __init__.py
│   └── git_parser.py       # Git repository parsing
├── sync/
│   ├── __init__.py
│   ├── git_to_neo4j.py     # Git → Neo4j sync
│   └── neo4j_to_git.py     # Neo4j → Git sync
├── queries/
│   ├── __init__.py
│   └── cypher_ops.py       # Cypher query templates for Git ops
├── cli.py                  # Command-line interface
└── config.py               # Configuration management
```

## Use Cases

1. **Advanced Git Analytics**: Use Neo4j's graph algorithms to analyze code evolution
2. **Code Archaeology**: Find patterns in how code changes over time
3. **Dependency Analysis**: Track how files and commits relate across branches
4. **Team Analytics**: Analyze collaboration patterns between developers
5. **Graph-based Git Operations**: Leverage Cypher for complex Git queries

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details.
