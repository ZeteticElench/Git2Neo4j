"""Git hooks for automatic Neo4j synchronization."""

from git2neo4j.hooks.install_hooks import install_github_action, install_local_hook

__all__ = ["install_local_hook", "install_github_action"]
