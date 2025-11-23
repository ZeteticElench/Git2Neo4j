"""Main window for Git2Neo4j GUI."""

import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from git2neo4j.gui.tabs.bulk_import_tab import BulkImportTab
from git2neo4j.gui.tabs.github_sync_tab import GitHubSyncTab
from git2neo4j.gui.tabs.query_tab import QueryTab
from git2neo4j.gui.tabs.repo_sync_tab import RepoSyncTab
from git2neo4j.gui.widgets.connection_status import ConnectionStatusWidget
from git2neo4j.gui.widgets.log_panel import LogPanel
from git2neo4j.gui.widgets.settings_dialog import SettingsDialog


class Git2Neo4jMainWindow(QMainWindow):
    """Main window for Git2Neo4j GUI application."""

    # Signals
    connection_status_changed = Signal(bool, str)  # connected, message
    log_message = Signal(str, str)  # level, message

    def __init__(self) -> None:
        """Initialize main window."""
        super().__init__()
        self.setWindowTitle("Git2Neo4j - Git to Neo4j Synchronization")
        self.setMinimumSize(1000, 700)

        # Settings
        self.settings = {
            "neo4j_uri": "bolt://localhost:7687",
            "neo4j_user": "neo4j",
            "neo4j_password": "password",
            "neo4j_database": "neo4j",
            "batch_size": 100,
            "sync_trees": True,
            "sync_blobs": False,
            "populate_text": False,
        }

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Connection status bar at top
        self.connection_status = ConnectionStatusWidget()
        main_layout.addWidget(self.connection_status)

        # Tab widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs, stretch=3)

        # Create tabs
        self.repo_sync_tab = RepoSyncTab(self)
        self.github_sync_tab = GitHubSyncTab(self)
        self.bulk_import_tab = BulkImportTab(self)
        self.query_tab = QueryTab(self)

        self.tabs.addTab(self.repo_sync_tab, "Local Repository")
        self.tabs.addTab(self.github_sync_tab, "GitHub Sync")
        self.tabs.addTab(self.bulk_import_tab, "Bulk Import")
        self.tabs.addTab(self.query_tab, "Query & Explore")

        # Log panel at bottom
        self.log_panel = LogPanel()
        main_layout.addWidget(self.log_panel, stretch=1)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Menu bar
        self._setup_menu()

    def _setup_menu(self) -> None:
        """Set up menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        settings_action = file_menu.addAction("&Settings...")
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.show_settings)

        file_menu.addSeparator()

        exit_action = file_menu.addAction("E&xit")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = help_menu.addAction("&About")
        about_action.triggered.connect(self.show_about)

        docs_action = help_menu.addAction("&Documentation")
        docs_action.triggered.connect(self.show_documentation)

    def _connect_signals(self) -> None:
        """Connect signals and slots."""
        self.connection_status_changed.connect(self.connection_status.update_status)
        self.log_message.connect(self.log_panel.add_log)

    @Slot()
    def show_settings(self) -> None:
        """Show settings dialog."""
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            self.settings = dialog.get_settings()
            self.log_message.emit("info", "Settings updated")
            # Notify tabs of settings change
            self.repo_sync_tab.update_settings(self.settings)
            self.github_sync_tab.update_settings(self.settings)
            self.bulk_import_tab.update_settings(self.settings)
            self.query_tab.update_settings(self.settings)

    @Slot()
    def show_about(self) -> None:
        """Show about dialog."""
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.about(
            self,
            "About Git2Neo4j",
            "<h2>Git2Neo4j</h2>"
            "<p>Synchronize Git repositories with Neo4j graph database.</p>"
            "<p>Version 0.1.0</p>"
            "<p>Built with Python, PySide6, and Neo4j.</p>"
            "<p><a href='https://github.com/yourusername/git2neo4j'>GitHub</a></p>",
        )

    @Slot()
    def show_documentation(self) -> None:
        """Show documentation."""
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl

        QDesktopServices.openUrl(QUrl("https://github.com/yourusername/git2neo4j/docs"))

    def get_settings(self) -> dict:
        """Get current settings.

        Returns:
            Current settings dictionary
        """
        return self.settings.copy()


def main() -> None:
    """Run the GUI application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Git2Neo4j")
    app.setOrganizationName("Git2Neo4j")

    window = Git2Neo4jMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
