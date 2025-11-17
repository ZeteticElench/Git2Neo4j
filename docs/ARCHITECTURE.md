# Git2Neo4j Architecture

This document explains the architecture and design decisions of Git2Neo4j.

## Overview

Git2Neo4j maps Git's directed acyclic graph (DAG) structure to Neo4j's property graph model, enabling powerful graph queries on Git history.

## Core Concepts

### 1. Git as a Graph

Git internally uses a DAG where:
- **Nodes**: Commits, trees (directories), blobs (files), tags
- **Edges**: Parent relationships, tree/blob containment
- **Properties**: Author, timestamp, message, file content, etc.

### 2. Neo4j Mapping

Git2Neo4j creates a natural mapping:

```
Git Object       →  Neo4j Node Label
-----------         ----------------
Commit           →  :Commit
Tree (directory) →  :Tree
Blob (file)      →  :Blob
Tag              →  :Tag
Branch           →  :Branch
Author           →  :Author
Repository       →  :Repository
```

## Graph Schema

### Node Types

#### Commit Node

Represents a Git commit.

```cypher
(:Commit {
  sha: string,              // Unique SHA-1 hash
  message: string,          // Commit message
  author_name: string,      // Author name
  author_email: string,     // Author email
  author_timestamp: datetime,  // When authored
  author_timezone: string,  // Timezone offset
  committer_name: string,   // Committer name
  committer_email: string,  // Committer email
  committer_timestamp: datetime,  // When committed
  committer_timezone: string,
  parent_count: int,        // Number of parents
  tree_sha: string,         // Root tree SHA
  encoding: string,         // Message encoding
  gpg_signature: string     // GPG signature (optional)
})
```

**Constraints**: `sha` is unique
**Indexes**: `author_timestamp`, `author_email`, `message`

#### Tree Node

Represents a directory snapshot.

```cypher
(:Tree {
  sha: string,              // Unique SHA-1 hash
  size: int,                // Size in bytes
  entry_count: int,         // Number of entries
  file_count: int,          // Number of files
  dir_count: int            // Number of subdirectories
})
```

**Constraints**: `sha` is unique

#### Blob Node

Represents a file at a specific version.

```cypher
(:Blob {
  sha: string,              // Unique SHA-1 hash
  size: int,                // Size in bytes
  path: string,             // File path (optional)
  is_binary: bool           // Whether binary
})
```

**Note**: File content is not stored in Neo4j for performance. It can be retrieved from Git when needed.

**Constraints**: `sha` is unique
**Indexes**: `path`

#### Branch Node

Represents a Git branch reference.

```cypher
(:Branch {
  name: string,             // Branch name
  full_name: string,        // Full name (e.g., "origin/main")
  commit_sha: string,       // Current commit SHA
  is_remote: bool,          // Whether remote branch
  remote_name: string,      // Remote name (optional)
  is_head: bool             // Whether current HEAD
})
```

**Constraints**: `full_name` is unique
**Indexes**: `name`

#### Tag Node

Represents an annotated Git tag.

```cypher
(:Tag {
  sha: string,              // Tag object SHA
  name: string,             // Tag name
  target_sha: string,       // Target object SHA
  target_type: string,      // Target type (commit, tree, etc.)
  message: string,          // Tag message
  tagger_name: string,      // Tagger name (optional)
  tagger_email: string,     // Tagger email (optional)
  tagger_timestamp: datetime,  // When tagged (optional)
  gpg_signature: string     // GPG signature (optional)
})
```

**Constraints**: `sha` is unique

#### Author Node

Represents a Git author/committer.

```cypher
(:Author {
  name: string,             // Author name
  email: string,            // Author email (unique)
  commit_count: int         // Number of commits
})
```

**Constraints**: `email` is unique
**Indexes**: `name`

#### Repository Node

Represents the Git repository metadata.

```cypher
(:Repository {
  path: string,             // Repository path (unique)
  name: string,             // Repository name
  head_sha: string,         // HEAD commit SHA
  current_branch: string,   // Current branch name
  is_bare: bool,            // Whether bare repo
  last_synced: datetime,    // Last sync timestamp
  commit_count: int,        // Total commits
  branch_count: int,        // Total branches
  tag_count: int            // Total tags
})
```

**Constraints**: `path` is unique

### Relationship Types

#### PARENT

Links a commit to its parent commit(s).

```cypher
(child:Commit)-[:PARENT {
  parent_index: int         // 0 for first parent, 1+ for merge parents
}]->(parent:Commit)
```

**Properties**:
- `parent_index`: Order of parent (0 = main parent, 1+ = merge parents)

#### TREE

Links a commit to its root tree.

```cypher
(commit:Commit)-[:TREE]->(tree:Tree)
```

#### HAS_ENTRY

Links a tree to its entries (files or subdirectories).

```cypher
(tree:Tree)-[:HAS_ENTRY {
  path: string,             // Entry path
  mode: string,             // File mode (e.g., "100644")
  entry_type: string        // "tree" or "blob"
}]->(entry)  // entry is either :Tree or :Blob
```

**Properties**:
- `path`: File/directory path
- `mode`: Unix file mode
- `entry_type`: Type of entry ("tree" or "blob")

#### POINTS_TO

Links branches and tags to commits.

```cypher
(ref)-[:POINTS_TO {
  ref_type: string          // "branch" or "tag"
}]->(commit:Commit)
```

Where `ref` is either `:Branch` or `:Tag`.

#### AUTHORED_BY

Links commits to authors.

```cypher
(commit:Commit)-[:AUTHORED_BY {
  role: string              // "author" or "committer"
}]->(author:Author)
```

#### TRACKS

Links repository to branches.

```cypher
(repo:Repository)-[:TRACKS]->(branch:Branch)
```

## Data Flow

### Sync: Git → Neo4j

```
┌─────────────┐
│ Git Repo    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ GitParser   │  Parse Git objects using GitPython
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ Pydantic Models │  Strongly-typed Python objects
└──────┬──────────┘
       │
       ▼
┌──────────────────┐
│ GitToNeo4jSync   │  Batch insert into Neo4j
└──────┬───────────┘
       │
       ▼
┌─────────────┐
│ Neo4j DB    │  Graph database
└─────────────┘
```

### Query: Cypher → Git Data

```
┌─────────────┐
│ User Query  │  Cypher or Python API
└──────┬──────┘
       │
       ▼
┌──────────────┐
│ CypherGitOps │  Git-like operations via Cypher
└──────┬───────┘
       │
       ▼
┌─────────────┐
│ Neo4j DB    │  Execute graph traversal
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Results     │  Return data to user
└─────────────┘
```

### Bidirectional: Neo4j → Git

```
┌─────────────┐
│ Neo4j Ops   │  Create/delete branches, tags in Neo4j
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ Neo4jToGitSync   │  Mirror changes to Git
└──────┬───────────┘
       │
       ▼
┌─────────────┐
│ Git Repo    │  Update Git repository
└─────────────┘
```

## Component Architecture

### Layer 1: Models

**Location**: `git2neo4j/models/`

- `git_objects.py`: Pydantic models for Git objects (CommitObject, TreeObject, etc.)
- `neo4j_schema.py`: Neo4j node/relationship definitions (CommitNode, ParentRelationship, etc.)

**Purpose**: Provide strong typing and validation for all data structures.

### Layer 2: Parsers

**Location**: `git2neo4j/parsers/`

- `git_parser.py`: Parse Git repositories using GitPython

**Purpose**: Extract Git objects from repositories and convert to Pydantic models.

### Layer 3: Sync Engines

**Location**: `git2neo4j/sync/`

- `git_to_neo4j.py`: Sync Git → Neo4j
- `neo4j_to_git.py`: Sync Neo4j → Git (bidirectional)

**Purpose**: Synchronize data between Git and Neo4j in both directions.

### Layer 4: Query API

**Location**: `git2neo4j/queries/`

- `cypher_ops.py`: Git-like operations via Cypher

**Purpose**: Provide high-level API for common Git operations using Cypher.

### Layer 5: CLI

**Location**: `git2neo4j/cli.py`

**Purpose**: Command-line interface for end users.

## Design Decisions

### Why Not Store Blob Content?

**Decision**: Don't store file content in Neo4j, only metadata.

**Rationale**:
- Neo4j is optimized for graph traversal, not large binary storage
- Blobs can be very large (images, binaries, etc.)
- Content can be retrieved from Git when needed
- Reduces Neo4j database size significantly

### Why Batch Processing?

**Decision**: Use batch inserts for better performance.

**Rationale**:
- Single transactions for large datasets would be slow
- Batching reduces network overhead
- Default batch size of 100 balances memory and performance

### Why Pydantic Models?

**Decision**: Use Pydantic for all data structures.

**Rationale**:
- Strong typing catches errors at development time
- Automatic validation ensures data integrity
- Easy serialization/deserialization
- Self-documenting code

### Why Separate Author Nodes?

**Decision**: Create separate `:Author` nodes instead of embedding in commits.

**Rationale**:
- Enables author-centric queries (e.g., "show all commits by author X")
- Reduces data duplication
- Supports future analytics (collaboration networks, etc.)

## Performance Considerations

### Indexing Strategy

**Indexes are created on**:
- All unique constraints (SHA hashes, emails, etc.)
- Frequently queried fields (timestamps, paths, names)

**Trade-offs**:
- Faster queries
- Slower writes (minimal impact with batch inserts)

### Batch Sizes

**Default: 100 nodes per batch**

- Smaller batches: Lower memory, slower sync
- Larger batches: Higher memory, faster sync

**Recommendation**: Adjust based on repository size and available memory.

### Sync Options

**Trees**: Optional (default: true)
- Enables file-level queries
- Increases database size

**Blobs**: Optional (default: false)
- Only metadata, not content
- Further increases size

## Extension Points

### Custom Queries

Add new query methods to `CypherGitOps`:

```python
def custom_query(self, param: str) -> list[dict]:
    query = "MATCH ... RETURN ..."
    return self.execute_cypher(query, {"param": param})
```

### Custom Analytics

Use Neo4j Graph Data Science library:

```cypher
// Page Rank on commit graph
CALL gds.pageRank.stream(...)
```

### Custom Sync Logic

Extend `GitToNeo4jSync` or `Neo4jToGitSync`:

```python
class CustomSync(GitToNeo4jSync):
    def custom_sync_logic(self):
        # Your logic here
        pass
```

## Future Enhancements

1. **Incremental Sync**: Only sync new commits since last sync (partially implemented)
2. **Full Bidirectional Sync**: Create commits in Neo4j and mirror to Git
3. **Webhook Integration**: Auto-sync on Git push
4. **Diff Analysis**: Store and query file diffs
5. **Code Metrics**: Integrate with code analysis tools
6. **Visualization**: Built-in graph visualization tools
