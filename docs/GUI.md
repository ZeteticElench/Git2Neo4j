# Git2Neo4j GUI Documentation

## Overview

The Git2Neo4j GUI provides a user-friendly graphical interface for syncing Git repositories to Neo4j and exploring the data. Built with PySide6 (Qt for Python), it offers all the functionality of the CLI in an intuitive desktop application.

## Installation

Install Git2Neo4j with GUI support:

```bash
pip install "git2neo4j[gui]"
```

Or for development:

```bash
pip install -e ".[dev,gui]"
```

## Launching the GUI

After installation, launch the GUI with:

```bash
git2neo4j-gui
```

Or from Python:

```python
from git2neo4j.gui.main_window import main
main()
```

## Main Window

The main window consists of:

1. **Connection Status Bar** - Shows Neo4j connection status
2. **Tabbed Interface** - Four main tabs for different operations
3. **Log Panel** - Real-time activity logs at the bottom
4. **Menu Bar** - Access to settings and help

## Tabs

### 1. Local Repository Tab

Sync local Git repositories to Neo4j.

**Features:**
- Browse for repository folder
- Configure sync options (create schema, sync trees, etc.)
- Background synchronization with progress updates
- Results display showing commit/branch/tag counts

**Usage:**
1. Click "Browse..." to select a Git repository
2. Configure options (use defaults for first sync)
3. Click "Sync Repository"
4. Monitor progress in the log panel
5. View results when complete

### 2. GitHub Sync Tab

Sync repositories from GitHub without cloning.

**Features:**
- Three sync modes:
  - Single Repository
  - Organization (all repos)
  - User Repositories
- Optional GitHub token for private repos
- Rate limit handling
- Configurable repository limits

**Usage:**

**Single Repository:**
1. Select "Single Repository" from dropdown
2. Enter owner and repository name (e.g., "torvalds" and "linux")
3. Optionally enter GitHub token
4. Click "Sync from GitHub"

**Organization:**
1. Select "Organization" from dropdown
2. Enter organization name
3. Set max repositories (0 = all)
4. Enter GitHub token (recommended)
5. Click "Sync from GitHub"

**User Repositories:**
1. Select "User Repositories" from dropdown
2. Enter GitHub username
3. Select type (owner/member/all)
4. Set max repositories
5. Click "Sync from GitHub"

### 3. Bulk Import Tab

Import multiple Git repositories from a folder.

**Features:**
- Recursive folder scanning
- Batch processing
- Automatic repository detection
- Progress tracking
- Error reporting per repository

**Usage:**
1. Click "Browse..." to select a folder
2. Enable "Search Recursively" to scan subfolders
3. Click "Import Repositories"
4. Monitor progress in log panel
5. Review results showing success/error counts

### 4. Query & Explore Tab

Execute Cypher queries and view results.

**Features:**
- Example query templates
- Syntax-highlighted query editor
- Tabular result display
- Auto-resizing columns
- Full-text search examples

**Example Queries:**
- List All Repositories
- Recent Commits (Last 10)
- Top Contributors
- Branch Overview
- File Statistics
- Search Commit Messages
- Repository Summary

**Usage:**
1. Select an example from dropdown or write custom query
2. Click "Load Example" if using template
3. Modify query as needed
4. Click "Execute Query"
5. View results in table below

## Settings Dialog

Access via **File → Settings** or `Ctrl+,`

**Neo4j Connection:**
- URI: bolt://localhost:7687
- User: neo4j
- Password: (your password)
- Database: neo4j

**Synchronization Options:**
- Batch Size: Number of operations per transaction (default: 100)
- Sync tree objects: Include Git tree objects
- Sync blob metadata: Include blob metadata
- Extract text content: Extract text from files for full-text search

**Note:** Settings apply to all tabs and persist during the session.

## Connection Status

The status bar at the top shows:
- **Green indicator** - Connected to Neo4j
- **Red indicator** - Not connected or error

Connection is tested when operations are performed.

## Log Panel

The log panel at the bottom displays:
- **INFO** (blue) - General information
- **SUCCESS** (green) - Successful operations
- **WARNING** (orange) - Non-critical issues
- **ERROR** (red) - Errors and failures

All operations are logged with timestamps for debugging.

## Background Operations

All sync operations run in background threads to keep the UI responsive:

- Repository syncing
- GitHub API calls
- Bulk imports
- Cypher queries

Progress updates appear in the log panel in real-time.

## Keyboard Shortcuts

- `Ctrl+,` - Open Settings
- `Ctrl+Q` - Quit Application

## Error Handling

The GUI provides comprehensive error handling:

- Connection errors are displayed in status bar
- Operation errors appear in results area
- All errors logged to log panel
- Graceful degradation on failures

Common errors:
- **"Repository not found"** - Check path is correct
- **"Could not connect to Neo4j"** - Verify Neo4j is running and credentials
- **"GitHub rate limit exceeded"** - Wait or use token for higher limits
- **"Permission denied"** - Check file/folder permissions

## Tips and Best Practices

1. **First-time setup:**
   - Configure Neo4j settings first
   - Test with a small repository
   - Enable "Create Schema" on first sync

2. **GitHub syncing:**
   - Use personal access token for private repos
   - Start with small max_repos limit
   - Check rate limits in log panel

3. **Bulk imports:**
   - Test on small folder first
   - Use recursive search for nested repos
   - Monitor errors in results

4. **Querying:**
   - Start with example queries
   - Use full-text indexes for code search
   - Check Neo4j Browser for advanced visualization

5. **Performance:**
   - Increase batch size for faster sync (up to 1000)
   - Disable trees/blobs for commit-only analysis
   - Use incremental syncs after initial import

## Architecture

The GUI is built with:

- **PySide6** - Qt for Python framework
- **Threading** - Background workers for operations
- **Signals/Slots** - Event-driven communication
- **Pydantic** - Type-safe configuration

**Project structure:**
```
git2neo4j/gui/
├── __init__.py
├── main_window.py          # Main application window
├── tabs/
│   ├── __init__.py
│   ├── repo_sync_tab.py    # Local repository sync
│   ├── github_sync_tab.py  # GitHub integration
│   ├── bulk_import_tab.py  # Bulk import
│   └── query_tab.py        # Query execution
└── widgets/
    ├── __init__.py
    ├── connection_status.py # Status indicator
    ├── log_panel.py         # Log display
    └── settings_dialog.py   # Settings window
```

## Extending the GUI

To add new features:

1. **New tab:**
   - Create class inheriting from `QWidget`
   - Add to `main_window.py`
   - Implement `update_settings()` method

2. **New query template:**
   - Edit `query_tab.py`
   - Add to `examples` dictionary in `on_example_selected()`

3. **New widget:**
   - Create in `widgets/` directory
   - Import in main window
   - Connect signals as needed

## Troubleshooting

**GUI won't start:**
```bash
# Check PySide6 installation
pip show PySide6

# Reinstall if needed
pip install --force-reinstall "git2neo4j[gui]"
```

**Missing icons or styling:**
- PySide6 should handle platform-specific styling
- Check Qt platform plugins are installed

**High memory usage:**
- Reduce batch size in settings
- Limit number of repositories in bulk import
- Clear results before new operations

## Platform Support

The GUI is tested on:
- **Linux** - Full support
- **macOS** - Full support
- **Windows** - Full support

Qt provides native look and feel on each platform.

## See Also

- [Quick Start Guide](QUICKSTART.md)
- [Git Hooks Documentation](GIT_HOOKS.md)
- [GitHub API Integration](../examples/github_api_sync.py)
- [CLI Documentation](../README.md)
