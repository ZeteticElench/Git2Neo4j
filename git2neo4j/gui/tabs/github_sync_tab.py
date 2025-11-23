"""GitHub repository sync tab."""

from PySide6.QtCore import QThread, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from git2neo4j.github.sync import (
    sync_github_organization,
    sync_github_repository,
    sync_github_user_repos,
)


class GitHubSyncWorker(QThread):
    """Worker thread for GitHub synchronization."""

    finished = Signal(dict)  # stats
    error = Signal(str)  # error message
    progress = Signal(str)  # progress message

    def __init__(self, sync_type: str, params: dict, settings: dict) -> None:
        """Initialize worker.

        Args:
            sync_type: Type of sync (repo, org, user)
            params: Sync parameters
            settings: Neo4j settings
        """
        super().__init__()
        self.sync_type = sync_type
        self.params = params
        self.settings = settings

    def run(self) -> None:
        """Run synchronization."""
        try:
            if self.sync_type == "repo":
                self.progress.emit(f"Syncing repository {self.params['repo']}...")
                stats = sync_github_repository(
                    owner=self.params["owner"],
                    repo=self.params["repo"],
                    neo4j_uri=self.settings["neo4j_uri"],
                    neo4j_user=self.settings["neo4j_user"],
                    neo4j_password=self.settings["neo4j_password"],
                    neo4j_database=self.settings["neo4j_database"],
                    github_token=self.params.get("token"),
                    batch_size=self.settings["batch_size"],
                    sync_trees=self.settings["sync_trees"],
                )
                self.finished.emit(stats)

            elif self.sync_type == "org":
                self.progress.emit(f"Syncing organization {self.params['org']}...")
                stats = sync_github_organization(
                    org=self.params["org"],
                    neo4j_uri=self.settings["neo4j_uri"],
                    neo4j_user=self.settings["neo4j_user"],
                    neo4j_password=self.settings["neo4j_password"],
                    neo4j_database=self.settings["neo4j_database"],
                    github_token=self.params.get("token"),
                    batch_size=self.settings["batch_size"],
                    sync_trees=self.settings["sync_trees"],
                    max_repos=self.params.get("max_repos"),
                )
                self.finished.emit(stats)

            elif self.sync_type == "user":
                self.progress.emit(f"Syncing user {self.params['username']} repos...")
                stats = sync_github_user_repos(
                    username=self.params["username"],
                    neo4j_uri=self.settings["neo4j_uri"],
                    neo4j_user=self.settings["neo4j_user"],
                    neo4j_password=self.settings["neo4j_password"],
                    neo4j_database=self.settings["neo4j_database"],
                    github_token=self.params.get("token"),
                    batch_size=self.settings["batch_size"],
                    sync_trees=self.settings["sync_trees"],
                    type_filter=self.params.get("type_filter", "owner"),
                    max_repos=self.params.get("max_repos"),
                )
                self.finished.emit(stats)

        except Exception as e:
            self.error.emit(str(e))


class GitHubSyncTab(QWidget):
    """Tab for synchronizing GitHub repositories."""

    def __init__(self, main_window) -> None:
        """Initialize GitHub sync tab.

        Args:
            main_window: Reference to main window
        """
        super().__init__()
        self.main_window = main_window
        self.worker = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Sync type selection
        type_group = QGroupBox("Sync Type")
        type_layout = QVBoxLayout()

        self.sync_type_combo = QComboBox()
        self.sync_type_combo.addItems(["Single Repository", "Organization", "User Repositories"])
        self.sync_type_combo.currentIndexChanged.connect(self.on_sync_type_changed)
        type_layout.addWidget(self.sync_type_combo)

        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        # Repository group (for single repo)
        self.repo_group = QGroupBox("Repository")
        repo_layout = QFormLayout()

        self.owner_edit = QLineEdit()
        self.owner_edit.setPlaceholderText("e.g., torvalds")
        repo_layout.addRow("Owner:", self.owner_edit)

        self.repo_edit = QLineEdit()
        self.repo_edit.setPlaceholderText("e.g., linux")
        repo_layout.addRow("Repository:", self.repo_edit)

        self.repo_group.setLayout(repo_layout)
        layout.addWidget(self.repo_group)

        # Organization group
        self.org_group = QGroupBox("Organization")
        org_layout = QFormLayout()

        self.org_edit = QLineEdit()
        self.org_edit.setPlaceholderText("e.g., microsoft")
        org_layout.addRow("Organization:", self.org_edit)

        self.org_max_repos_spin = QSpinBox()
        self.org_max_repos_spin.setRange(0, 1000)
        self.org_max_repos_spin.setValue(10)
        self.org_max_repos_spin.setSpecialValueText("All")
        org_layout.addRow("Max Repositories:", self.org_max_repos_spin)

        self.org_group.setLayout(org_layout)
        self.org_group.setVisible(False)
        layout.addWidget(self.org_group)

        # User group
        self.user_group = QGroupBox("User")
        user_layout = QFormLayout()

        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("e.g., guido")
        user_layout.addRow("Username:", self.user_edit)

        self.user_type_combo = QComboBox()
        self.user_type_combo.addItems(["owner", "member", "all"])
        user_layout.addRow("Type:", self.user_type_combo)

        self.user_max_repos_spin = QSpinBox()
        self.user_max_repos_spin.setRange(0, 1000)
        self.user_max_repos_spin.setValue(10)
        self.user_max_repos_spin.setSpecialValueText("All")
        user_layout.addRow("Max Repositories:", self.user_max_repos_spin)

        self.user_group.setLayout(user_layout)
        self.user_group.setVisible(False)
        layout.addWidget(self.user_group)

        # GitHub token
        token_group = QGroupBox("GitHub Token (Optional)")
        token_layout = QHBoxLayout()

        self.token_edit = QLineEdit()
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_edit.setPlaceholderText("GitHub Personal Access Token (for private repos)")
        token_layout.addWidget(self.token_edit)

        token_group.setLayout(token_layout)
        layout.addWidget(token_group)

        # Sync button
        self.sync_btn = QPushButton("Sync from GitHub")
        self.sync_btn.clicked.connect(self.sync_github)
        self.sync_btn.setMinimumHeight(40)
        self.sync_btn.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; font-weight: bold; }"
            "QPushButton:hover { background-color: #1976D2; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        layout.addWidget(self.sync_btn)

        # Results display
        results_group = QGroupBox("Sync Results")
        results_layout = QVBoxLayout()

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(200)
        results_layout.addWidget(self.results_text)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        layout.addStretch()

    @Slot(int)
    def on_sync_type_changed(self, index: int) -> None:
        """Handle sync type change.

        Args:
            index: Selected index
        """
        self.repo_group.setVisible(index == 0)
        self.org_group.setVisible(index == 1)
        self.user_group.setVisible(index == 2)

    @Slot()
    def sync_github(self) -> None:
        """Start GitHub synchronization."""
        sync_type_index = self.sync_type_combo.currentIndex()
        token = self.token_edit.text().strip() or None

        params = {"token": token}

        if sync_type_index == 0:  # Single repo
            owner = self.owner_edit.text().strip()
            repo = self.repo_edit.text().strip()

            if not owner or not repo:
                self.main_window.log_message.emit("error", "Please enter owner and repository")
                return

            params["owner"] = owner
            params["repo"] = repo
            sync_type = "repo"

        elif sync_type_index == 1:  # Organization
            org = self.org_edit.text().strip()

            if not org:
                self.main_window.log_message.emit("error", "Please enter organization name")
                return

            params["org"] = org
            max_repos = self.org_max_repos_spin.value()
            if max_repos > 0:
                params["max_repos"] = max_repos
            sync_type = "org"

        else:  # User repos
            username = self.user_edit.text().strip()

            if not username:
                self.main_window.log_message.emit("error", "Please enter username")
                return

            params["username"] = username
            params["type_filter"] = self.user_type_combo.currentText()
            max_repos = self.user_max_repos_spin.value()
            if max_repos > 0:
                params["max_repos"] = max_repos
            sync_type = "user"

        # Disable button during sync
        self.sync_btn.setEnabled(False)
        self.sync_btn.setText("Syncing from GitHub...")
        self.results_text.clear()

        # Create and start worker
        settings = self.main_window.get_settings()
        self.worker = GitHubSyncWorker(sync_type, params, settings)
        self.worker.finished.connect(self.on_sync_finished)
        self.worker.error.connect(self.on_sync_error)
        self.worker.progress.connect(self.on_sync_progress)
        self.worker.start()

    @Slot(dict)
    def on_sync_finished(self, stats: dict) -> None:
        """Handle sync completion.

        Args:
            stats: Sync statistics
        """
        self.sync_btn.setEnabled(True)
        self.sync_btn.setText("Sync from GitHub")

        # Display results
        results = "<h3>GitHub Sync Completed Successfully!</h3><br>"

        if "repositories" in stats:
            # Multi-repo sync
            results += f"<b>Repositories:</b> {stats.get('repositories', 0)}<br>"
            results += f"<b>Total Commits:</b> {stats.get('total_commits', 0)}<br>"
            results += f"<b>Total Branches:</b> {stats.get('total_branches', 0)}<br>"
            results += f"<b>Total Tags:</b> {stats.get('total_tags', 0)}<br>"

            if stats.get("errors"):
                results += "<br><b>Errors:</b><br>"
                for error in stats["errors"]:
                    results += f"  - {error['repository']}: {error['error']}<br>"
        else:
            # Single repo sync
            results += f"<b>Commits:</b> {stats.get('commits', 0)}<br>"
            results += f"<b>Branches:</b> {stats.get('branches', 0)}<br>"
            results += f"<b>Tags:</b> {stats.get('tags', 0)}<br>"
            results += f"<b>Trees:</b> {stats.get('trees', 0)}<br>"

        self.results_text.setHtml(results)
        self.main_window.log_message.emit("success", "GitHub sync completed successfully")
        self.main_window.connection_status_changed.emit(True, "Sync completed")

    @Slot(str)
    def on_sync_error(self, error: str) -> None:
        """Handle sync error.

        Args:
            error: Error message
        """
        self.sync_btn.setEnabled(True)
        self.sync_btn.setText("Sync from GitHub")

        self.results_text.setHtml(f'<span style="color: red;"><b>Error:</b> {error}</span>')
        self.main_window.log_message.emit("error", f"GitHub sync failed: {error}")
        self.main_window.connection_status_changed.emit(False, error)

    @Slot(str)
    def on_sync_progress(self, message: str) -> None:
        """Handle sync progress.

        Args:
            message: Progress message
        """
        self.main_window.log_message.emit("info", message)

    def update_settings(self, settings: dict) -> None:
        """Update settings.

        Args:
            settings: New settings
        """
        pass
