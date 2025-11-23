#!/usr/bin/env python3
"""
Install Git hooks for automatic Neo4j synchronization.

Usage:
    python -m git2neo4j.hooks.install_hooks [--repo-path PATH]
"""

import argparse
import shutil
import stat
from pathlib import Path


def install_local_hook(repo_path: Path, hook_name: str = "post-commit") -> bool:
    """Install a local Git hook.

    Args:
        repo_path: Path to Git repository
        hook_name: Name of hook to install (post-commit, pre-push, etc.)

    Returns:
        True if successful, False otherwise
    """
    git_hooks_dir = repo_path / ".git" / "hooks"

    if not git_hooks_dir.exists():
        print(f"Error: Not a Git repository: {repo_path}")
        return False

    # Source hook file
    hooks_module_dir = Path(__file__).parent
    source_hook = hooks_module_dir / hook_name

    if not source_hook.exists():
        print(f"Error: Hook file not found: {source_hook}")
        return False

    # Destination hook file
    dest_hook = git_hooks_dir / hook_name

    # Backup existing hook if present
    if dest_hook.exists():
        backup_file = git_hooks_dir / f"{hook_name}.backup"
        print(f"Backing up existing hook to: {backup_file}")
        shutil.copy2(dest_hook, backup_file)

    # Copy hook file
    shutil.copy2(source_hook, dest_hook)

    # Make executable
    dest_hook.chmod(dest_hook.stat().st_mode | stat.S_IEXEC)

    print(f"✓ Installed {hook_name} hook to {dest_hook}")
    return True


def create_config_file(repo_path: Path) -> bool:
    """Create a configuration file template.

    Args:
        repo_path: Path to Git repository

    Returns:
        True if successful, False otherwise
    """
    config_file = repo_path / ".git2neo4j.conf"

    if config_file.exists():
        response = input(f"Configuration file already exists. Overwrite? [y/N]: ")
        if response.lower() != 'y':
            print("Skipping configuration file creation.")
            return False

    config_template = """# Git2Neo4j Configuration
# This file configures automatic syncing to Neo4j via Git hooks

# Neo4j connection settings
neo4j_uri=bolt://localhost:7687
neo4j_user=neo4j
neo4j_password=password
neo4j_database=neo4j

# Sync options
sync_trees=true
sync_blobs=false
populate_text=false

# Enable/disable hook (set to false to temporarily disable)
enabled=true
"""

    config_file.write_text(config_template)
    print(f"✓ Created configuration file: {config_file}")
    print("\nIMPORTANT: Edit this file to set your Neo4j connection details!")
    print("Add .git2neo4j.conf to .gitignore to avoid committing credentials.")

    return True


def add_to_gitignore(repo_path: Path) -> None:
    """Add config file to .gitignore.

    Args:
        repo_path: Path to Git repository
    """
    gitignore_file = repo_path / ".gitignore"
    config_pattern = ".git2neo4j.conf"

    # Check if already in gitignore
    if gitignore_file.exists():
        content = gitignore_file.read_text()
        if config_pattern in content:
            return

    # Append to gitignore
    with gitignore_file.open("a") as f:
        f.write(f"\n# Git2Neo4j configuration (contains credentials)\n")
        f.write(f"{config_pattern}\n")

    print(f"✓ Added {config_pattern} to .gitignore")


def install_github_action(repo_path: Path) -> bool:
    """Install GitHub Actions workflow.

    Args:
        repo_path: Path to Git repository

    Returns:
        True if successful, False otherwise
    """
    workflows_dir = repo_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)

    # Source workflow file
    hooks_module_dir = Path(__file__).parent
    source_workflow = hooks_module_dir / "github-actions" / "sync-to-neo4j.yml"

    if not source_workflow.exists():
        print(f"Error: Workflow file not found: {source_workflow}")
        return False

    # Destination workflow file
    dest_workflow = workflows_dir / "sync-to-neo4j.yml"

    if dest_workflow.exists():
        response = input(f"GitHub Action already exists. Overwrite? [y/N]: ")
        if response.lower() != 'y':
            print("Skipping GitHub Action installation.")
            return False

    shutil.copy2(source_workflow, dest_workflow)
    print(f"✓ Installed GitHub Action workflow to {dest_workflow}")
    print("\nNext steps for GitHub:")
    print("1. Add secrets to your GitHub repository:")
    print("   - NEO4J_URI")
    print("   - NEO4J_USER")
    print("   - NEO4J_PASSWORD")
    print("   - NEO4J_DATABASE (optional)")
    print("2. Commit and push the workflow file")
    print("3. The workflow will run on every push to main/master/develop")

    return True


def main() -> None:
    """Main installation function."""
    parser = argparse.ArgumentParser(
        description="Install Git hooks for automatic Neo4j synchronization"
    )
    parser.add_argument(
        "--repo-path",
        type=Path,
        default=Path.cwd(),
        help="Path to Git repository (default: current directory)",
    )
    parser.add_argument(
        "--hook",
        choices=["post-commit", "post-receive", "all"],
        default="post-commit",
        help="Which hook to install",
    )
    parser.add_argument(
        "--github-action",
        action="store_true",
        help="Install GitHub Actions workflow",
    )
    parser.add_argument(
        "--config-only",
        action="store_true",
        help="Only create configuration file",
    )

    args = parser.parse_args()
    repo_path = args.repo_path.resolve()

    print(f"Installing Git2Neo4j hooks in: {repo_path}\n")

    success = True

    # Create configuration file
    if args.config_only or not args.github_action:
        create_config_file(repo_path)
        add_to_gitignore(repo_path)

    if args.config_only:
        return

    # Install local hooks
    if args.github_action:
        success = install_github_action(repo_path)
    else:
        if args.hook == "all":
            success = install_local_hook(repo_path, "post-commit")
            success = install_local_hook(repo_path, "post-receive") and success
        else:
            success = install_local_hook(repo_path, args.hook)

    if success:
        print("\n✓ Installation complete!")
        print("\nTo test the hook, make a commit and check the output.")
        print("To disable temporarily, set enabled=false in .git2neo4j.conf")
    else:
        print("\n✗ Installation failed!")


if __name__ == "__main__":
    main()
