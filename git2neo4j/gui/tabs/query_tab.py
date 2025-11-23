"""Query and explore tab."""

from PySide6.QtCore import QThread, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from git2neo4j.queries.cypher_ops import CypherGitOps


class QueryWorker(QThread):
    """Worker thread for Cypher queries."""

    finished = Signal(list)  # results
    error = Signal(str)  # error message

    def __init__(self, query: str, settings: dict) -> None:
        """Initialize worker.

        Args:
            query: Cypher query
            settings: Neo4j settings
        """
        super().__init__()
        self.query = query
        self.settings = settings

    def run(self) -> None:
        """Run query."""
        try:
            with CypherGitOps(
                uri=self.settings["neo4j_uri"],
                user=self.settings["neo4j_user"],
                password=self.settings["neo4j_password"],
                database=self.settings["neo4j_database"],
            ) as ops:
                results = ops.execute_cypher(self.query)
                self.finished.emit(results)

        except Exception as e:
            self.error.emit(str(e))


class QueryTab(QWidget):
    """Tab for executing Cypher queries and exploring data."""

    def __init__(self, main_window) -> None:
        """Initialize query tab.

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

        # Example queries dropdown
        examples_group = QGroupBox("Example Queries")
        examples_layout = QHBoxLayout()

        self.examples_combo = QComboBox()
        self.examples_combo.addItems([
            "Custom Query",
            "List All Repositories",
            "Recent Commits (Last 10)",
            "Top Contributors",
            "Branch Overview",
            "File Statistics",
            "Search Commit Messages",
            "Repository Summary",
        ])
        self.examples_combo.currentIndexChanged.connect(self.on_example_selected)
        examples_layout.addWidget(self.examples_combo)

        load_btn = QPushButton("Load Example")
        load_btn.clicked.connect(lambda: self.on_example_selected(self.examples_combo.currentIndex()))
        examples_layout.addWidget(load_btn)

        examples_group.setLayout(examples_layout)
        layout.addWidget(examples_group)

        # Query editor
        query_group = QGroupBox("Cypher Query")
        query_layout = QVBoxLayout()

        self.query_edit = QTextEdit()
        self.query_edit.setPlaceholderText("Enter Cypher query here...")
        self.query_edit.setMaximumHeight(150)
        self.query_edit.setStyleSheet("font-family: monospace; font-size: 12pt;")
        query_layout.addWidget(self.query_edit)

        # Execute button
        execute_btn = QPushButton("Execute Query")
        execute_btn.clicked.connect(self.execute_query)
        execute_btn.setMinimumHeight(35)
        execute_btn.setStyleSheet(
            "QPushButton { background-color: #9C27B0; color: white; font-weight: bold; }"
            "QPushButton:hover { background-color: #7B1FA2; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        query_layout.addWidget(execute_btn)

        query_group.setLayout(query_layout)
        layout.addWidget(query_group)

        # Results table
        results_group = QGroupBox("Query Results")
        results_layout = QVBoxLayout()

        self.results_table = QTableWidget()
        self.results_table.setAlternatingRowColors(True)
        results_layout.addWidget(self.results_table)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

    @Slot(int)
    def on_example_selected(self, index: int) -> None:
        """Load example query.

        Args:
            index: Selected example index
        """
        examples = {
            0: "",  # Custom
            1: """MATCH (r:Repository)
RETURN r.name as name, r.path as path, r.commit_count as commits
ORDER BY commits DESC""",
            2: """MATCH (c:Commit)
RETURN c.sha as sha, c.message as message, c.author_name as author,
       c.author_date as date
ORDER BY c.author_timestamp DESC
LIMIT 10""",
            3: """MATCH (c:Commit)
WITH c.author_email as author, count(c) as commits
RETURN author, commits
ORDER BY commits DESC
LIMIT 10""",
            4: """MATCH (b:Branch)
RETURN b.name as branch, b.repo_name as repository, b.is_head as is_head
ORDER BY repository, is_head DESC""",
            5: """MATCH (b:Blob)
WHERE b.text_content IS NOT NULL
WITH b.extension as ext, count(b) as files, avg(b.size) as avg_size
RETURN ext, files, avg_size
ORDER BY files DESC
LIMIT 20""",
            6: """CALL db.index.fulltext.queryNodes('commit_message_fulltext', $search_term)
YIELD node, score
RETURN node.sha as sha, node.message as message, score
LIMIT 10""",
            7: """MATCH (r:Repository)
OPTIONAL MATCH (r)-[:CONTAINS]->(c:Commit)
OPTIONAL MATCH (r)-[:TRACKS]->(b:Branch)
RETURN r.name as repository,
       count(DISTINCT c) as commits,
       count(DISTINCT b) as branches
ORDER BY commits DESC""",
        }

        query = examples.get(index, "")
        self.query_edit.setPlainText(query)

    @Slot()
    def execute_query(self) -> None:
        """Execute Cypher query."""
        query = self.query_edit.toPlainText().strip()
        if not query:
            self.main_window.log_message.emit("error", "Please enter a query")
            return

        # Clear previous results
        self.results_table.clear()
        self.results_table.setRowCount(0)
        self.results_table.setColumnCount(0)

        # Create and start worker
        settings = self.main_window.get_settings()
        self.worker = QueryWorker(query, settings)
        self.worker.finished.connect(self.on_query_finished)
        self.worker.error.connect(self.on_query_error)
        self.worker.start()

        self.main_window.log_message.emit("info", "Executing query...")

    @Slot(list)
    def on_query_finished(self, results: list) -> None:
        """Handle query completion.

        Args:
            results: Query results
        """
        if not results:
            self.main_window.log_message.emit("warning", "Query returned no results")
            return

        # Set up table
        first_row = results[0]
        columns = list(first_row.keys())

        self.results_table.setColumnCount(len(columns))
        self.results_table.setHorizontalHeaderLabels(columns)
        self.results_table.setRowCount(len(results))

        # Populate table
        for row_idx, row_data in enumerate(results):
            for col_idx, column in enumerate(columns):
                value = row_data.get(column, "")
                # Convert to string for display
                if isinstance(value, (list, dict)):
                    value = str(value)
                elif value is None:
                    value = ""
                else:
                    value = str(value)

                item = QTableWidgetItem(value)
                self.results_table.setItem(row_idx, col_idx, item)

        # Resize columns to content
        self.results_table.resizeColumnsToContents()

        self.main_window.log_message.emit("success", f"Query returned {len(results)} results")
        self.main_window.connection_status_changed.emit(True, "Query executed successfully")

    @Slot(str)
    def on_query_error(self, error: str) -> None:
        """Handle query error.

        Args:
            error: Error message
        """
        self.main_window.log_message.emit("error", f"Query failed: {error}")
        self.main_window.connection_status_changed.emit(False, error)

    def update_settings(self, settings: dict) -> None:
        """Update settings.

        Args:
            settings: New settings
        """
        pass
