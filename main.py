"""
Точка входу NeuralControl.
Запуск: python main.py
"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.styles import DARK_STYLE


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("NeuralControl")
    app.setOrganizationName("NeuralControl")
    app.setStyleSheet(DARK_STYLE)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()