"""Bulk import tab."""

from pathlib import Path

from PySide6.QtCore import QThread, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from git2neo4j.sync.bulk_import import import_repositories_from_folder


class BulkImportWorker(QThread):
    """Worker thread for bulk import."""

    finished = Signal(dict)  # stats
    error = Signal(str)  # error message
    progress = Signal(str)  # progress message

    def __init__(self, folder_path: str, recursive: bool, settings: dict) -> None:
        """Initialize worker.

        Args:
            folder_path: Folder containing repositories
            recursive: Search recursively
            settings: Import settings
        """
        super().__init__()
        self.folder_path = folder_path
        self.recursive = recursive
        self.settings = settings

    def run(self) -> None:
        """Run bulk import."""
        try:
            self.progress.emit(f"Scanning folder: {self.folder_path}...")

            stats = import_repositories_from_folder(
                folder_path=self.folder_path,
                recursive=self.recursive,
                neo4j_uri=self.settings["neo4j_uri"],
                neo4j_user=self.settings["neo4j_user"],
                neo4j_password=self.settings["neo4j_password"],
                neo4j_database=self.settings["neo4j_database"],
                batch_size=self.settings["batch_size"],
                sync_trees=self.settings["sync_trees"],
                sync_blobs=self.settings["sync_blobs"],
                populate_blob_text=self.settings.get("populate_text", False),
            )

            self.finished.emit(stats)

        except Exception as e:
            self.error.emit(str(e))


class BulkImportTab(QWidget):
    """Tab for bulk importing multiple repositories."""

    def __init__(self, main_window) -> None:
        """Initialize bulk import tab.

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

        # Folder selection group
        folder_group = QGroupBox("Folder Selection")
        folder_layout = QHBoxLayout()

        self.folder_path_edit = QLineEdit()
        self.folder_path_edit.setPlaceholderText("Select a folder containing Git repositories...")
        folder_layout.addWidget(self.folder_path_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_folder)
        folder_layout.addWidget(browse_btn)

        folder_group.setLayout(folder_layout)
        layout.addWidget(folder_group)

        # Options group
        options_group = QGroupBox("Import Options")
        options_layout = QFormLayout()

        self.recursive_check = QCheckBox()
        self.recursive_check.setChecked(True)
        options_layout.addRow("Search Recursively:", self.recursive_check)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Import button
        self.import_btn = QPushButton("Import Repositories")
        self.import_btn.clicked.connect(self.import_repositories)
        self.import_btn.setMinimumHeight(40)
        self.import_btn.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: white; font-weight: bold; }"
            "QPushButton:hover { background-color: #F57C00; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        layout.addWidget(self.import_btn)

        # Results display
        results_group = QGroupBox("Import Results")
        results_layout = QVBoxLayout()

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

    @Slot()
    def browse_folder(self) -> None:
        """Browse for folder."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Folder Containing Repositories", str(Path.home())
        )
        if directory:
            self.folder_path_edit.setText(directory)

    @Slot()
    def import_repositories(self) -> None:
        """Start bulk import."""
        folder_path = self.folder_path_edit.text().strip()
        if not folder_path:
            self.main_window.log_message.emit("error", "Please select a folder")
            return

        if not Path(folder_path).exists():
            self.main_window.log_message.emit("error", f"Folder not found: {folder_path}")
            return

        # Disable button during import
        self.import_btn.setEnabled(False)
        self.import_btn.setText("Importing...")
        self.results_text.clear()

        # Create and start worker
        settings = self.main_window.get_settings()
        recursive = self.recursive_check.isChecked()
        self.worker = BulkImportWorker(folder_path, recursive, settings)
        self.worker.finished.connect(self.on_import_finished)
        self.worker.error.connect(self.on_import_error)
        self.worker.progress.connect(self.on_import_progress)
        self.worker.start()

    @Slot(dict)
    def on_import_finished(self, stats: dict) -> None:
        """Handle import completion.

        Args:
            stats: Import statistics
        """
        self.import_btn.setEnabled(True)
        self.import_btn.setText("Import Repositories")

        # Display results
        results = "<h3>Bulk Import Completed Successfully!</h3><br>"
        results += f"<b>Repositories Found:</b> {stats.get('repositories_found', 0)}<br>"
        results += f"<b>Repositories Synced:</b> {stats.get('repositories_synced', 0)}<br>"
        results += f"<b>Total Commits:</b> {stats.get('total_commits', 0)}<br>"
        results += f"<b>Total Branches:</b> {stats.get('total_branches', 0)}<br>"
        results += f"<b>Total Tags:</b> {stats.get('total_tags', 0)}<br>"
        results += f"<b>Total Trees:</b> {stats.get('total_trees', 0)}<br>"
        results += f"<b>Total Blobs:</b> {stats.get('total_blobs', 0)}<br>"

        if stats.get("errors"):
            results += "<br><b style='color: red;'>Errors:</b><br>"
            for error in stats["errors"]:
                results += f"  - {error['repository']}: {error['error']}<br>"

        self.results_text.setHtml(results)
        self.main_window.log_message.emit("success", "Bulk import completed successfully")
        self.main_window.connection_status_changed.emit(True, "Import completed")

    @Slot(str)
    def on_import_error(self, error: str) -> None:
        """Handle import error.

        Args:
            error: Error message
        """
        self.import_btn.setEnabled(True)
        self.import_btn.setText("Import Repositories")

        self.results_text.setHtml(f'<span style="color: red;"><b>Error:</b> {error}</span>')
        self.main_window.log_message.emit("error", f"Bulk import failed: {error}")
        self.main_window.connection_status_changed.emit(False, error)

    @Slot(str)
    def on_import_progress(self, message: str) -> None:
        """Handle import progress.

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
