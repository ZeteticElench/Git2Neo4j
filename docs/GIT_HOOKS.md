# Git Hooks for Automatic Neo4j Synchronization

Git2Neo4j can automatically sync your repository to Neo4j whenever you commit or push using Git hooks.

## Quick Start

### Option 1: Local Git Hook (post-commit)

Automatically sync after every local commit:

```bash
# Install the post-commit hook
git2neo4j install-hook /path/to/repo

# Edit the configuration file with your Neo4j credentials
nano .git2neo4j.conf

# Make a commit to test
git commit -m "Test automatic sync"
# Output: ✓ Synced to Neo4j: 1 commits
```

### Option 2: GitHub Actions (on push to GitHub)

Automatically sync when you push to GitHub:

```bash
# Install GitHub Actions workflow
git2neo4j install-hook /path/to/repo --hook github-action

# Add secrets to your GitHub repository:
# Settings → Secrets and variables → Actions → New repository secret
# - NEO4J_URI: bolt://your-neo4j-server:7687
# - NEO4J_USER: neo4j
# - NEO4J_PASSWORD: your-password
# - NEO4J_DATABASE: neo4j (optional)

# Commit and push the workflow file
git add .github/workflows/sync-to-neo4j.yml
git commit -m "Add Neo4j sync workflow"
git push
```

### Option 3: Server-Side Hook (post-receive)

Automatically sync when receiving pushes on a Git server:

```bash
# On your Git server
git2neo4j install-hook /path/to/bare/repo.git --hook post-receive

# Edit configuration
nano /path/to/bare/repo.git/git2neo4j.conf

# Test by pushing to the server
git push origin main
# Output: ✓ Synced to Neo4j: 5 commits
```

## Configuration

### Local Configuration File: `.git2neo4j.conf`

The configuration file is created automatically when you install a hook:

```ini
# Git2Neo4j Configuration
# This file configures automatic syncing to Neo4j via Git hooks

# Neo4j connection settings
neo4j_uri=bolt://localhost:7687
neo4j_user=neo4j
neo4j_password=your-password-here
neo4j_database=neo4j

# Sync options
sync_trees=true          # Include tree objects
sync_blobs=false         # Include blob metadata
populate_text=false      # Extract text content (slower)

# Enable/disable hook
enabled=true             # Set to false to temporarily disable
```

**Important:** Add `.git2neo4j.conf` to `.gitignore` to avoid committing credentials!

### Environment Variables

You can also configure via environment variables:

```bash
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=password
export NEO4J_DATABASE=neo4j
export GIT2NEO4J_SYNC_TREES=true
export GIT2NEO4J_SYNC_BLOBS=false
export GIT2NEO4J_POPULATE_TEXT=false
export GIT2NEO4J_ENABLED=true
```

Environment variables take precedence over the config file.

## Hook Types

### 1. Post-Commit Hook

Runs after every local commit.

**Install:**
```bash
git2neo4j install-hook . --hook post-commit
```

**Use case:** Development workflow where you want immediate sync to Neo4j.

**Pros:**
- Immediate feedback
- Works offline (with local Neo4j)

**Cons:**
- Adds small delay to commits (usually < 1 second)
- Only syncs your local commits

### 2. Post-Receive Hook

Runs on the server after receiving a push.

**Install:**
```bash
# On your Git server
git2neo4j install-hook /path/to/repo.git --hook post-receive
```

**Use case:** Centralized Git server where multiple developers push.

**Pros:**
- Syncs all developers' commits
- Doesn't slow down local development
- Single source of truth

**Cons:**
- Requires server-side installation
- Delayed sync (only on push)

### 3. GitHub Actions

Runs as a GitHub Actions workflow on push.

**Install:**
```bash
git2neo4j install-hook . --hook github-action
```

**Use case:** Public/private repositories on GitHub.

**Pros:**
- No server infrastructure needed
- Works with GitHub-hosted repos
- Can run on schedule or manually

**Cons:**
- Requires GitHub Actions minutes
- Network latency to Neo4j server
- Needs publicly accessible Neo4j (or GitHub-hosted runner in same network)

## Advanced Configuration

### Custom GitHub Actions

Edit `.github/workflows/sync-to-neo4j.yml`:

```yaml
# Run on specific branches only
on:
  push:
    branches:
      - main
      - develop
      - 'feature/**'

# Add custom steps
jobs:
  sync-to-neo4j:
    steps:
      # ... existing steps ...

      - name: Run custom Cypher query
        run: |
          git2neo4j cypher "MATCH (c:Commit) RETURN count(c)"

      - name: Notify on sync
        uses: some-notification-action@v1
        with:
          message: "Synced to Neo4j successfully"
```

### Conditional Sync

Only sync certain branches or file types:

```bash
# In post-commit hook, add before sync_to_neo4j():
current_branch=$(git branch --show-current)
if [[ "$current_branch" != "main" && "$current_branch" != "develop" ]]; then
    echo "Skipping sync for branch: $current_branch"
    exit 0
fi
```

### Performance Tuning

For large repositories:

```ini
# .git2neo4j.conf
sync_trees=false         # Skip trees initially
sync_blobs=false         # Skip blobs
populate_text=false      # Skip text extraction

# Run full sync manually later:
# git2neo4j sync . --trees --populate-text
```

## Troubleshooting

### Hook Not Running

1. Check if hook is executable:
   ```bash
   chmod +x .git/hooks/post-commit
   ```

2. Check if hook is enabled:
   ```bash
   grep enabled .git2neo4j.conf
   # Should show: enabled=true
   ```

3. Test manually:
   ```bash
   .git/hooks/post-commit
   ```

### Connection Issues

The hook will fail gracefully without blocking your commit:

```
Warning: Could not connect to Neo4j. Skipping sync.
```

To debug:
```bash
# Test connection manually
git2neo4j sync . --uri bolt://localhost:7687 -p password
```

### Slow Commits

If syncing takes too long:

1. Reduce sync scope:
   ```ini
   sync_trees=false
   sync_blobs=false
   populate_text=false
   ```

2. Use server-side hooks instead of post-commit

3. Use GitHub Actions for async sync

### GitHub Actions Fails

1. Check secrets are set correctly:
   - Go to Settings → Secrets and variables → Actions
   - Verify NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

2. Check Neo4j is accessible from GitHub:
   - Must be publicly accessible or use self-hosted runner
   - Test connection with `telnet your-neo4j-server 7687`

3. Check workflow logs:
   - Go to Actions tab in GitHub
   - Click on failed workflow
   - Check "Sync to Neo4j" step for errors

## Security Considerations

1. **Never commit credentials:**
   - Always add `.git2neo4j.conf` to `.gitignore`
   - Use GitHub Secrets for Actions

2. **Restrict Neo4j access:**
   - Use read-only user for sensitive repos
   - Enable Neo4j authentication
   - Use SSL/TLS for Neo4j connection

3. **Review hook code:**
   - Hooks run with your permissions
   - Review hook scripts before installation
   - Keep git2neo4j updated

## Uninstalling Hooks

### Local Hook

```bash
# Simply delete the hook file
rm .git/hooks/post-commit

# Or disable via config
echo "enabled=false" >> .git2neo4j.conf
```

### GitHub Actions

```bash
# Delete the workflow file
rm .github/workflows/sync-to-neo4j.yml
git commit -m "Remove Neo4j sync workflow"
git push
```

## Examples

### Example 1: Development Workflow

```bash
# Initial setup
git2neo4j install-hook ~/my-project
nano .git2neo4j.conf  # Set credentials

# Daily work
git add .
git commit -m "Add feature"
# ✓ Synced to Neo4j: 1 commits

# Query in Neo4j Browser:
# MATCH (c:Commit) WHERE c.message CONTAINS "Add feature" RETURN c
```

### Example 2: Team Repository on GitHub

```bash
# One-time setup by team lead
git2neo4j install-hook . --hook github-action

# Team lead adds secrets to GitHub
# Team members just push:
git push origin feature-branch
# GitHub Actions automatically syncs to Neo4j
```

### Example 3: Monorepo with Multiple Projects

```bash
# Different config per project
git2neo4j install-hook ~/monorepo/project-a
git2neo4j install-hook ~/monorepo/project-b

# Each project syncs to different Neo4j database
# project-a/.git2neo4j.conf:
neo4j_database=project_a

# project-b/.git2neo4j.conf:
neo4j_database=project_b
```

## CLI Reference

```bash
# Install post-commit hook
git2neo4j install-hook [REPO_PATH] --hook post-commit

# Install post-receive hook
git2neo4j install-hook [REPO_PATH] --hook post-receive

# Install GitHub Actions
git2neo4j install-hook [REPO_PATH] --hook github-action

# Create config file only
git2neo4j install-hook [REPO_PATH] --config-only

# Install to current directory
git2neo4j install-hook .
```

## See Also

- [Quick Start Guide](QUICKSTART.md)
- [Architecture Documentation](ARCHITECTURE.md)
- [Full-Text Search Examples](../examples/fulltext_search.py)
