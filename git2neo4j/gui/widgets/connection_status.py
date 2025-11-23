"""Connection status widget."""

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget


class ConnectionStatusWidget(QWidget):
    """Widget showing Neo4j connection status."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize connection status widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._setup_ui()
        self.update_status(False, "Not connected")

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Connection indicator
        self.indicator = QFrame()
        self.indicator.setFixedSize(12, 12)
        self.indicator.setFrameShape(QFrame.Shape.Box)
        layout.addWidget(self.indicator)

        # Status label
        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Style frame
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setMaximumHeight(30)

    @Slot(bool, str)
    def update_status(self, connected: bool, message: str) -> None:
        """Update connection status.

        Args:
            connected: Whether connected to Neo4j
            message: Status message
        """
        if connected:
            self.indicator.setStyleSheet("background-color: #4CAF50; border-radius: 6px;")
            self.status_label.setText(f"✓ Connected: {message}")
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.indicator.setStyleSheet("background-color: #F44336; border-radius: 6px;")
            self.status_label.setText(f"✗ Disconnected: {message}")
            self.status_label.setStyleSheet("color: #F44336; font-weight: bold;")

    def setFrameStyle(self, style: int) -> None:
        """Set frame style for compatibility.

        Args:
            style: Frame style
        """
        # Compatibility method
        pass
