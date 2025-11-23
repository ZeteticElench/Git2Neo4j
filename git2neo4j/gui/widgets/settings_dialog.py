"""Settings dialog."""

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)


class SettingsDialog(QDialog):
    """Dialog for application settings."""

    def __init__(self, settings: dict, parent=None) -> None:
        """Initialize settings dialog.

        Args:
            settings: Current settings dictionary
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)

        self.settings = settings.copy()
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Neo4j connection group
        neo4j_group = QGroupBox("Neo4j Connection")
        neo4j_layout = QFormLayout()

        self.uri_edit = QLineEdit()
        neo4j_layout.addRow("URI:", self.uri_edit)

        self.user_edit = QLineEdit()
        neo4j_layout.addRow("User:", self.user_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        neo4j_layout.addRow("Password:", self.password_edit)

        self.database_edit = QLineEdit()
        neo4j_layout.addRow("Database:", self.database_edit)

        neo4j_group.setLayout(neo4j_layout)
        layout.addWidget(neo4j_group)

        # Sync options group
        sync_group = QGroupBox("Synchronization Options")
        sync_layout = QFormLayout()

        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(1, 10000)
        self.batch_size_spin.setValue(100)
        sync_layout.addRow("Batch Size:", self.batch_size_spin)

        self.sync_trees_check = QCheckBox("Sync tree objects")
        sync_layout.addRow("", self.sync_trees_check)

        self.sync_blobs_check = QCheckBox("Sync blob metadata")
        sync_layout.addRow("", self.sync_blobs_check)

        self.populate_text_check = QCheckBox("Extract text content from files")
        sync_layout.addRow("", self.populate_text_check)

        sync_group.setLayout(sync_layout)
        layout.addWidget(sync_group)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_settings(self) -> None:
        """Load settings into UI."""
        self.uri_edit.setText(self.settings.get("neo4j_uri", "bolt://localhost:7687"))
        self.user_edit.setText(self.settings.get("neo4j_user", "neo4j"))
        self.password_edit.setText(self.settings.get("neo4j_password", "password"))
        self.database_edit.setText(self.settings.get("neo4j_database", "neo4j"))
        self.batch_size_spin.setValue(self.settings.get("batch_size", 100))
        self.sync_trees_check.setChecked(self.settings.get("sync_trees", True))
        self.sync_blobs_check.setChecked(self.settings.get("sync_blobs", False))
        self.populate_text_check.setChecked(self.settings.get("populate_text", False))

    def get_settings(self) -> dict:
        """Get settings from UI.

        Returns:
            Settings dictionary
        """
        return {
            "neo4j_uri": self.uri_edit.text(),
            "neo4j_user": self.user_edit.text(),
            "neo4j_password": self.password_edit.text(),
            "neo4j_database": self.database_edit.text(),
            "batch_size": self.batch_size_spin.value(),
            "sync_trees": self.sync_trees_check.isChecked(),
            "sync_blobs": self.sync_blobs_check.isChecked(),
            "populate_text": self.populate_text_check.isChecked(),
        }
