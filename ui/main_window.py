"""
Головне вікно NeuralControl.
Каркас з 4 вкладками + темна тема.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QLabel,
    QStatusBar,
)

from core.types import GESTURES_JSON, RADIAL_MENU_JSON


class PlaceholderTab(QWidget):
    """Заглушка для Етапу 0."""

    def __init__(self, title: str, description: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            "font-size: 28px; font-weight: bold; color: #00d4ff;"
        )
        title_label.setAlignment(Qt.AlignCenter)

        desc_label = QLabel(description)
        desc_label.setStyleSheet("font-size: 14px; color: #64748b;")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(desc_label)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("⚡ NeuralControl — Neural Hand Control")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 700)

        self._build_ui()
        self._build_status_bar()

    def _build_ui(self):
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.tab_control = PlaceholderTab(
            "📷 Управління",
            "Камера, скелет руки, режими (Жести / Мишка / Малювання).\n"
            "(Етап 3)"
        )
        self.tabs.addTab(self.tab_control, "📷 Управління")

        self.tab_training = PlaceholderTab(
            "🎓 Навчання",
            "Запис нових жестів, таблиця класів,\n"
            "перенавчання моделі (MLP / SVC / RF).\n"
            "(Етап 4)"
        )
        self.tabs.addTab(self.tab_training, "🎓 Навчання")

        self.tab_labs = PlaceholderTab(
            "🧪 Лабораторні",
            "Вбудовані лаби 4-8:\n"
            "Fuzzy, GA, Регресія, Дерева, CNN.\n"
            "(Етап 5)"
        )
        self.tabs.addTab(self.tab_labs, "🧪 Лаби")

        self.tab_help = PlaceholderTab(
            "📖 Довідка",
            f"Список жестів та їхніх дій.\n"
            f"Джерело: {GESTURES_JSON.name}\n"
            f"Кругове меню: {RADIAL_MENU_JSON.name}\n"
            "(Етап 5)"
        )
        self.tabs.addTab(self.tab_help, "📖 Довідка")

        self.setCentralWidget(self.tabs)

    def _build_status_bar(self):
        status = QStatusBar()
        status.setStyleSheet(
            "background-color: #131826; color: #64748b; "
            "border-top: 1px solid #2a3350; padding: 4px;"
        )
        status.showMessage("● Готово | Камера: вимкнена | Режим: очікування")
        self.setStatusBar(status)