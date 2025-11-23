"""Log panel widget."""

from datetime import datetime

from PySide6.QtCore import Slot
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QTextEdit, QVBoxLayout, QWidget


class LogPanel(QWidget):
    """Widget for displaying log messages."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize log panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Text edit for logs
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        layout.addWidget(self.log_text)

        # Initial message
        self.add_log("info", "Git2Neo4j GUI started")

    @Slot(str, str)
    def add_log(self, level: str, message: str) -> None:
        """Add a log message.

        Args:
            level: Log level (info, warning, error, success)
            message: Log message
        """
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Color based on level
        color_map = {
            "info": "#2196F3",
            "warning": "#FF9800",
            "error": "#F44336",
            "success": "#4CAF50",
        }
        color = color_map.get(level, "#000000")

        # Format message
        html = f'<span style="color: #666;">[{timestamp}]</span> '
        html += f'<span style="color: {color}; font-weight: bold;">[{level.upper()}]</span> '
        html += f'<span>{message}</span>'

        # Append to log
        self.log_text.append(html)

        # Auto-scroll to bottom
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)

    def clear(self) -> None:
        """Clear all log messages."""
        self.log_text.clear()
