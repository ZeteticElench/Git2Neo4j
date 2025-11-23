"""Local repository sync tab."""

from pathlib import Path

from PySide6.QtCore import QThread, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from git2neo4j.sync.git_to_neo4j import GitToNeo4jSync


class SyncWorker(QThread):
    """Worker thread for repository synchronization."""

    finished = Signal(dict)  # stats
    error = Signal(str)  # error message
    progress = Signal(str)  # progress message

    def __init__(self, repo_path: str, settings: dict) -> None:
        """Initialize worker.

        Args:
            repo_path: Repository path
            settings: Sync settings
        """
        super().__init__()
        self.repo_path = repo_path
        self.settings = settings

    def run(self) -> None:
        """Run synchronization."""
        try:
            self.progress.emit("Starting synchronization...")

            with GitToNeo4jSync(
                repo_path=Path(self.repo_path),
                neo4j_uri=self.settings["neo4j_uri"],
                neo4j_user=self.settings["neo4j_user"],
                neo4j_password=self.settings["neo4j_password"],
                neo4j_database=self.settings["neo4j_database"],
                batch_size=self.settings["batch_size"],
                sync_trees=self.settings["sync_trees"],
                sync_blobs=self.settings["sync_blobs"],
            ) as sync:
                self.progress.emit("Testing connection...")
                if not sync.verify_connection():
                    self.error.emit("Could not connect to Neo4j")
                    return

                self.progress.emit("Syncing repository...")
                stats = sync.sync_repository()

                if self.settings.get("populate_text", False):
                    self.progress.emit("Extracting text content...")
                    blob_count = sync.populate_blob_content()
                    stats["text_blobs"] = blob_count

                self.finished.emit(stats)

        except Exception as e:
            self.error.emit(str(e))


class RepoSyncTab(QWidget):
    """Tab for synchronizing local Git repositories."""

    def __init__(self, main_window) -> None:
        """Initialize repository sync tab.

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

        # Repository selection group
        repo_group = QGroupBox("Repository Selection")
        repo_layout = QHBoxLayout()

        self.repo_path_edit = QLineEdit()
        self.repo_path_edit.setPlaceholderText("Select a Git repository...")
        repo_layout.addWidget(self.repo_path_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_repository)
        repo_layout.addWidget(browse_btn)

        repo_group.setLayout(repo_layout)
        layout.addWidget(repo_group)

        # Options group
        options_group = QGroupBox("Sync Options")
        options_layout = QFormLayout()

        self.create_schema_check = QCheckBox()
        self.create_schema_check.setChecked(True)
        options_layout.addRow("Create Schema:", self.create_schema_check)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Sync button
        self.sync_btn = QPushButton("Sync Repository")
        self.sync_btn.clicked.connect(self.sync_repository)
        self.sync_btn.setMinimumHeight(40)
        self.sync_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }"
            "QPushButton:hover { background-color: #45a049; }"
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

    @Slot()
    def browse_repository(self) -> None:
        """Browse for repository."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Git Repository", str(Path.home())
        )
        if directory:
            self.repo_path_edit.setText(directory)

    @Slot()
    def sync_repository(self) -> None:
        """Start repository synchronization."""
        repo_path = self.repo_path_edit.text().strip()
        if not repo_path:
            self.main_window.log_message.emit("error", "Please select a repository")
            return

        if not Path(repo_path).exists():
            self.main_window.log_message.emit("error", f"Repository not found: {repo_path}")
            return

        # Disable button during sync
        self.sync_btn.setEnabled(False)
        self.sync_btn.setText("Syncing...")
        self.results_text.clear()

        # Create and start worker
        settings = self.main_window.get_settings()
        self.worker = SyncWorker(repo_path, settings)
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
        self.sync_btn.setText("Sync Repository")

        # Display results
        results = "<h3>Sync Completed Successfully!</h3><br>"
        results += f"<b>Commits:</b> {stats.get('commits', 0)}<br>"
        results += f"<b>Branches:</b> {stats.get('branches', 0)}<br>"
        results += f"<b>Tags:</b> {stats.get('tags', 0)}<br>"
        results += f"<b>Trees:</b> {stats.get('trees', 0)}<br>"
        results += f"<b>Blobs:</b> {stats.get('blobs', 0)}<br>"
        results += f"<b>Authors:</b> {stats.get('authors', 0)}<br>"

        if "text_blobs" in stats:
            results += f"<b>Text Blobs:</b> {stats['text_blobs']}<br>"

        self.results_text.setHtml(results)
        self.main_window.log_message.emit("success", "Repository synced successfully")
        self.main_window.connection_status_changed.emit(True, "Sync completed")

    @Slot(str)
    def on_sync_error(self, error: str) -> None:
        """Handle sync error.

        Args:
            error: Error message
        """
        self.sync_btn.setEnabled(True)
        self.sync_btn.setText("Sync Repository")

        self.results_text.setHtml(f'<span style="color: red;"><b>Error:</b> {error}</span>')
        self.main_window.log_message.emit("error", f"Sync failed: {error}")
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
        # Settings are retrieved from main window when needed
        pass
