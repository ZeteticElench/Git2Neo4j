"""GitHub API integration for Git2Neo4j."""

import base64
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import requests
from pydantic import BaseModel, Field

from git2neo4j.models.git_objects import (
    AuthorInfo,
    BranchInfo,
    CommitObject,
    GitObjectType,
    RepositoryInfo,
    TagObject,
    TreeEntry,
    TreeEntryMode,
    TreeObject,
)


class GitHubConfig(BaseModel):
    """GitHub API configuration."""

    token: str | None = Field(default=None, description="GitHub personal access token")
    api_url: str = Field(
        default="https://api.github.com", description="GitHub API base URL"
    )
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    rate_limit_wait: bool = Field(
        default=True, description="Wait when rate limit is hit"
    )


class GitHubAPIClient:
    """Client for GitHub API v3."""

    def __init__(self, config: GitHubConfig | None = None) -> None:
        """Initialize GitHub API client.

        Args:
            config: GitHub configuration
        """
        self.config = config or GitHubConfig()
        self.session = requests.Session()

        # Set up authentication
        if self.config.token:
            self.session.headers.update(
                {
                    "Authorization": f"token {self.config.token}",
                    "Accept": "application/vnd.github.v3+json",
                }
            )
        else:
            self.session.headers.update({"Accept": "application/vnd.github.v3+json"})

    def _request(
        self, method: str, endpoint: str, params: dict[str, Any] | None = None
    ) -> Any:
        """Make API request with rate limiting and retry logic.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Response JSON

        Raises:
            requests.RequestException: If request fails
        """
        url = f"{self.config.api_url}/{endpoint.lstrip('/')}"

        for attempt in range(self.config.max_retries):
            response = self.session.request(method, url, params=params)

            # Check rate limit
            if response.status_code == 403 and "rate limit" in response.text.lower():
                if self.config.rate_limit_wait:
                    reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                    wait_time = max(reset_time - int(time.time()), 0) + 1
                    print(f"Rate limit hit. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise requests.RequestException("GitHub rate limit exceeded")

            # Retry on server errors
            if response.status_code >= 500 and attempt < self.config.max_retries - 1:
                time.sleep(2**attempt)  # Exponential backoff
                continue

            response.raise_for_status()
            return response.json()

        raise requests.RequestException(f"Failed after {self.config.max_retries} attempts")

    def get_repository(self, owner: str, repo: str) -> dict[str, Any]:
        """Get repository information.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Repository data
        """
        return self._request("GET", f"/repos/{owner}/{repo}")

    def get_commits(
        self, owner: str, repo: str, sha: str | None = None, per_page: int = 100
    ) -> Iterator[dict[str, Any]]:
        """Get commits from repository.

        Args:
            owner: Repository owner
            repo: Repository name
            sha: SHA or branch name to start from
            per_page: Results per page

        Yields:
            Commit data
        """
        page = 1
        params = {"per_page": per_page}
        if sha:
            params["sha"] = sha

        while True:
            params["page"] = page
            commits = self._request("GET", f"/repos/{owner}/{repo}/commits", params)

            if not commits:
                break

            for commit in commits:
                yield commit

            page += 1

    def get_commit(self, owner: str, repo: str, sha: str) -> dict[str, Any]:
        """Get single commit details.

        Args:
            owner: Repository owner
            repo: Repository name
            sha: Commit SHA

        Returns:
            Commit data with full details
        """
        return self._request("GET", f"/repos/{owner}/{repo}/commits/{sha}")

    def get_tree(
        self, owner: str, repo: str, tree_sha: str, recursive: bool = False
    ) -> dict[str, Any]:
        """Get tree object.

        Args:
            owner: Repository owner
            repo: Repository name
            tree_sha: Tree SHA
            recursive: Get tree recursively

        Returns:
            Tree data
        """
        params = {"recursive": "1" if recursive else "0"}
        return self._request("GET", f"/repos/{owner}/{repo}/git/trees/{tree_sha}", params)

    def get_blob(self, owner: str, repo: str, blob_sha: str) -> dict[str, Any]:
        """Get blob object.

        Args:
            owner: Repository owner
            repo: Repository name
            blob_sha: Blob SHA

        Returns:
            Blob data
        """
        return self._request("GET", f"/repos/{owner}/{repo}/git/blobs/{blob_sha}")

    def get_branches(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """Get all branches.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            List of branches
        """
        branches = []
        page = 1
        per_page = 100

        while True:
            params = {"page": page, "per_page": per_page}
            result = self._request("GET", f"/repos/{owner}/{repo}/branches", params)

            if not result:
                break

            branches.extend(result)
            page += 1

        return branches

    def get_tags(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """Get all tags.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            List of tags
        """
        tags = []
        page = 1
        per_page = 100

        while True:
            params = {"page": page, "per_page": per_page}
            result = self._request("GET", f"/repos/{owner}/{repo}/tags", params)

            if not result:
                break

            tags.extend(result)
            page += 1

        return tags

    def get_user_repositories(
        self, username: str, type_filter: str = "owner"
    ) -> list[dict[str, Any]]:
        """Get repositories for a user.

        Args:
            username: GitHub username
            type_filter: Type of repos (owner, member, all)

        Returns:
            List of repositories
        """
        repos = []
        page = 1
        per_page = 100

        while True:
            params = {"page": page, "per_page": per_page, "type": type_filter}
            result = self._request("GET", f"/users/{username}/repos", params)

            if not result:
                break

            repos.extend(result)
            page += 1

        return repos

    def get_org_repositories(self, org: str) -> list[dict[str, Any]]:
        """Get repositories for an organization.

        Args:
            org: Organization name

        Returns:
            List of repositories
        """
        repos = []
        page = 1
        per_page = 100

        while True:
            params = {"page": page, "per_page": per_page}
            result = self._request("GET", f"/orgs/{org}/repos", params)

            if not result:
                break

            repos.extend(result)
            page += 1

        return repos


class GitHubToGitAdapter:
    """Adapter to convert GitHub API data to Git objects."""

    def __init__(self, client: GitHubAPIClient, owner: str, repo: str) -> None:
        """Initialize adapter.

        Args:
            client: GitHub API client
            owner: Repository owner
            repo: Repository name
        """
        self.client = client
        self.owner = owner
        self.repo = repo
        self._repo_data: dict[str, Any] | None = None

    def get_repository_info(self) -> RepositoryInfo:
        """Get repository information.

        Returns:
            Repository metadata
        """
        if not self._repo_data:
            self._repo_data = self.client.get_repository(self.owner, self.repo)

        # Get default branch
        default_branch = self._repo_data.get("default_branch", "main")

        # Get branches
        branches = []
        for branch_data in self.client.get_branches(self.owner, self.repo):
            branches.append(
                BranchInfo(
                    name=branch_data["name"],
                    commit_sha=branch_data["commit"]["sha"],
                    is_remote=True,
                    remote_name="origin",
                    is_head=(branch_data["name"] == default_branch),
                )
            )

        return RepositoryInfo(
            path=f"github.com/{self.owner}/{self.repo}",
            head_sha=self._repo_data.get("default_branch_commit_sha"),
            current_branch=default_branch,
            branches=branches,
            remotes={"origin": self._repo_data["clone_url"]},
            is_bare=False,
        )

    def get_all_commits(self) -> Iterator[CommitObject]:
        """Get all commits from the repository.

        Yields:
            Commit objects
        """
        seen = set()

        # Get commits from default branch
        for commit_data in self.client.get_commits(self.owner, self.repo):
            sha = commit_data["sha"]
            if sha in seen:
                continue

            seen.add(sha)

            # Get full commit details
            full_commit = self.client.get_commit(self.owner, self.repo, sha)
            yield self._parse_commit(full_commit)

    def get_commit(self, sha: str) -> CommitObject:
        """Get a specific commit.

        Args:
            sha: Commit SHA

        Returns:
            Commit object
        """
        commit_data = self.client.get_commit(self.owner, self.repo, sha)
        return self._parse_commit(commit_data)

    def get_tree(self, sha: str) -> TreeObject:
        """Get a tree object.

        Args:
            sha: Tree SHA

        Returns:
            Tree object
        """
        tree_data = self.client.get_tree(self.owner, self.repo, sha, recursive=False)
        return self._parse_tree(tree_data)

    def get_all_trees_for_commit(self, commit_sha: str) -> Iterator[TreeObject]:
        """Get all trees for a commit.

        Args:
            commit_sha: Commit SHA

        Yields:
            Tree objects
        """
        commit = self.get_commit(commit_sha)
        tree = self.get_tree(commit.tree_sha)
        yield tree

        # Get subtrees recursively
        for entry in tree.entries:
            if entry.type == GitObjectType.TREE:
                yield from self.get_all_trees_for_commit(entry.sha)

    def get_all_tags(self) -> Iterator[TagObject]:
        """Get all tags.

        Yields:
            Tag objects
        """
        for tag_data in self.client.get_tags(self.owner, self.repo):
            # GitHub API returns lightweight tags, we'll create simple tag objects
            yield TagObject(
                sha=tag_data["commit"]["sha"],  # Use commit SHA for lightweight tags
                type=GitObjectType.TAG,
                size=0,
                name=tag_data["name"],
                target_sha=tag_data["commit"]["sha"],
                target_type=GitObjectType.COMMIT,
                message="",
                tagger=None,
            )

    def _parse_commit(self, commit_data: dict[str, Any]) -> CommitObject:
        """Parse GitHub commit to CommitObject.

        Args:
            commit_data: GitHub commit data

        Returns:
            Parsed commit object
        """
        commit_info = commit_data["commit"]

        # Parse author
        author = self._parse_author(commit_info["author"])
        committer = self._parse_author(commit_info["committer"])

        # Get parent SHAs
        parent_shas = [p["sha"] for p in commit_data.get("parents", [])]

        return CommitObject(
            sha=commit_data["sha"],
            type=GitObjectType.COMMIT,
            size=0,  # GitHub doesn't provide size
            tree_sha=commit_info["tree"]["sha"],
            parent_shas=parent_shas,
            author=author,
            committer=committer,
            message=commit_info["message"],
            encoding="utf-8",
            gpg_signature=commit_info.get("verification", {}).get("signature"),
        )

    def _parse_tree(self, tree_data: dict[str, Any]) -> TreeObject:
        """Parse GitHub tree to TreeObject.

        Args:
            tree_data: GitHub tree data

        Returns:
            Parsed tree object
        """
        entries = []

        for item in tree_data.get("tree", []):
            # Convert mode to TreeEntryMode
            mode_int = int(item["mode"], 8)  # Convert octal string to int
            mode_str = f"{mode_int:06o}"

            try:
                mode = TreeEntryMode(mode_str)
            except ValueError:
                mode = TreeEntryMode.FILE

            # Determine type
            obj_type = (
                GitObjectType.TREE if item["type"] == "tree" else GitObjectType.BLOB
            )

            entry = TreeEntry(
                mode=mode,
                type=obj_type,
                sha=item["sha"],
                path=item["path"],
            )
            entries.append(entry)

        return TreeObject(
            sha=tree_data["sha"],
            type=GitObjectType.TREE,
            size=0,
            entries=entries,
        )

    def _parse_author(self, author_data: dict[str, Any]) -> AuthorInfo:
        """Parse GitHub author data to AuthorInfo.

        Args:
            author_data: GitHub author data

        Returns:
            Parsed author info
        """
        # Parse ISO 8601 timestamp
        timestamp_str = author_data["date"]
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

        return AuthorInfo(
            name=author_data["name"],
            email=author_data["email"],
            timestamp=timestamp,
            timezone="+0000",  # GitHub uses UTC
        )
