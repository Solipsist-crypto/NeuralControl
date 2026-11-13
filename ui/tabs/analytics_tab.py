import csv
from datetime import datetime

import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.types import GESTURE_TRANSLATIONS, ROOT
from services.training_service import TrainingService
from ui.dialogs.lab_dialog import LabDialog
from ui.widgets.glow_button import GlowButton


BG = "#0a0e1a"
CYAN = "#4da6ff"
VIOLET = "#8b5cf6"
TEXT = "#e2e8f0"
MUTED = "#64748b"


class HudPanel(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setObjectName("AnalyticsPanel")
        self.setStyleSheet(
            f"QFrame#AnalyticsPanel {{ background-color: {BG}; "
            "border: 1px solid #2a3350; border-radius: 12px; }"
        )
        self.content_layout = QVBoxLayout(self)
        self.content_layout.setContentsMargins(16, 14, 16, 14)
        self.content_layout.setSpacing(10)

        heading = QLabel(title)
        heading.setStyleSheet(
            f"color: {CYAN}; font-weight: bold; font-size: 13px; "
            "border: none; background: transparent;"
        )
        self.content_layout.addWidget(heading)


class AnalyticsTab(QWidget):
    def __init__(self, training_service=None):
        super().__init__()
        self.setStyleSheet("background-color: #0a0e1a;")
        self.training_service = training_service or TrainingService()
        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background-color: #0a0e1a; border: none; }"
        )
        scroll.viewport().setStyleSheet("background-color: #0a0e1a;")
        content = QWidget()
        content.setStyleSheet("background-color: #0a0e1a;")
        layout = QGridLayout(content)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(14)

        stats_panel = HudPanel("СТАТИСТИКА МОДЕЛІ")
        self.examples_value = self._add_metric(
            stats_panel, "ЗАГАЛЬНА КІЛЬКІСТЬ ПРИКЛАДІВ"
        )
        self.classes_value = self._add_metric(stats_panel, "КІЛЬКІСТЬ КЛАСІВ")
        self.accuracy_value = self._add_metric(
            stats_panel, "ТОЧНІСТЬ (ТЕСТОВА ВИБІРКА)"
        )
        layout.addWidget(stats_panel, 0, 0)

        controls_panel = HudPanel("КЕРУВАННЯ ДАНИМИ")
        delete_button = GlowButton("🗑️ Видалити вибрані приклади", "#f472b6")
        delete_button.clicked.connect(self._delete_selected_samples)
        controls_panel.content_layout.addWidget(delete_button)

        export_button = GlowButton("📥 Експортувати базу (CSV)", CYAN)
        export_button.clicked.connect(self._export_csv)
        controls_panel.content_layout.addWidget(export_button)

        labs_button = GlowButton("🧪 Лабораторні роботи", VIOLET)
        labs_button.clicked.connect(self._open_labs_dialog)
        controls_panel.content_layout.addWidget(labs_button)

        report_button = GlowButton("📄 Експорт звіту (PDF)", "#4ade80")
        report_button.clicked.connect(self._export_pdf)
        controls_panel.content_layout.addWidget(report_button)
        layout.addWidget(controls_panel, 0, 1)

        distribution_panel = HudPanel("РОЗПОДІЛ ЖЕСТІВ")
        self.distribution_figure = Figure(
            figsize=(7, 3.2), dpi=100, facecolor=BG
        )
        self.distribution_canvas = FigureCanvasQTAgg(self.distribution_figure)
        self.distribution_canvas.setMinimumHeight(260)
        distribution_panel.content_layout.addWidget(self.distribution_canvas)
        layout.addWidget(distribution_panel, 1, 0)

        confusion_panel = HudPanel("МАТРИЦЯ ПОМИЛОК")
        self.confusion_figure = Figure(figsize=(7, 3.2), dpi=100, facecolor=BG)
        self.confusion_canvas = FigureCanvasQTAgg(self.confusion_figure)
        self.confusion_canvas.setMinimumHeight(260)
        confusion_panel.content_layout.addWidget(self.confusion_canvas)
        layout.addWidget(confusion_panel, 1, 1)

        samples_panel = HudPanel("СПИСОК ПРИКЛАДІВ")
        self.samples_table = QTableWidget(0, 3)
        self.samples_table.setStyleSheet(
            "QTableWidget { background-color: #0a0e1a; border: none; }"
        )
        self.samples_table.setFrameShape(QFrame.NoFrame)
        self.samples_table.setContentsMargins(0, 0, 0, 0)
        self.samples_table.setHorizontalHeaderLabels(["ID (час)", "ЖЕСТ", "ДІЯ"])
        self.samples_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.samples_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.samples_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.samples_table.setSortingEnabled(False)
        self.samples_table.verticalHeader().setVisible(False)
        header = self.samples_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.samples_table.setMinimumHeight(240)
        samples_panel.content_layout.addWidget(self.samples_table)
        layout.addWidget(samples_panel, 2, 0, 1, 2)

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setRowStretch(1, 1)
        layout.setRowStretch(2, 1)
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    @staticmethod
    def _add_metric(panel, title):
        row = QHBoxLayout()
        label = QLabel(title)
        label.setStyleSheet("color: #94a3b8; border: none; background: transparent;")
        value = QLabel("—")
        value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        value.setStyleSheet(
            f"color: {TEXT}; font-size: 20px; font-weight: bold; "
            "border: none; background: transparent;"
        )
        row.addWidget(label)
        row.addStretch()
        row.addWidget(value)
        panel.content_layout.addLayout(row)
        return value

    @staticmethod
    def _style_axes(axes):
        axes.set_facecolor(BG)
        axes.tick_params(colors=TEXT)
        axes.xaxis.label.set_color(TEXT)
        axes.yaxis.label.set_color(TEXT)
        axes.grid(axis="y", color="#2a3350", alpha=0.8)
        axes.set_axisbelow(True)
        for spine in axes.spines.values():
            spine.set_color("#2a3350")

    def refresh_data(self):
        stats = self.training_service.get_stats()
        self.examples_value.setText(str(sum(stats.values())))
        self.classes_value.setText(str(len(stats)))

        accuracy = self.training_service.get_accuracy()
        self.accuracy_value.setText(
            f"{accuracy:.1%}" if accuracy is not None else "—"
        )

        self._refresh_distribution(stats)
        self._refresh_confusion_matrix(accuracy)
        self._refresh_samples()

    def _refresh_distribution(self, stats):
        self.distribution_figure.clear()
        axes = self.distribution_figure.add_subplot(111)
        self._style_axes(axes)
        axes.set_xlabel("ЖЕСТ", color=TEXT)
        axes.set_ylabel("КІЛЬКІСТЬ ПРИКЛАДІВ", color=TEXT)

        if stats:
            labels = [
                GESTURE_TRANSLATIONS.get(str(gesture), str(gesture))
                for gesture in stats
            ]
            bars = axes.bar(
                labels, list(stats.values()), color=CYAN, edgecolor=VIOLET
            )
            axes.bar_label(bars, padding=3, color=TEXT)
            axes.tick_params(axis="x", labelrotation=20)
        else:
            axes.text(
                0.5,
                0.5,
                "ПОКИ НЕМАЄ ДАНИХ",
                color=MUTED,
                ha="center",
                va="center",
                transform=axes.transAxes,
            )

        self.distribution_figure.tight_layout()
        self.distribution_canvas.draw_idle()

    def _refresh_confusion_matrix(self, accuracy):
        self.confusion_figure.clear()
        self.confusion_figure.patch.set_facecolor(BG)
        axes = self.confusion_figure.add_subplot(111)
        self._style_axes(axes)
        axes.tick_params(colors="white")
        axes.set_facecolor(BG)

        if accuracy is None:
            axes.text(
                0.5,
                0.5,
                "Спочатку навчіть модель",
                color=TEXT,
                ha="center",
                va="center",
                transform=axes.transAxes,
            )
        else:
            matrix, classes = self.training_service.get_confusion_matrix()
            if matrix is None or not classes:
                axes.text(
                    0.5,
                    0.5,
                    "Спочатку навчіть модель",
                    color=TEXT,
                    ha="center",
                    va="center",
                    transform=axes.transAxes,
                )
            else:
                labels = [
                    GESTURE_TRANSLATIONS.get(gesture, gesture)
                    for gesture in classes
                ]
                image = axes.imshow(matrix, interpolation="nearest", cmap="magma")
                colorbar = self.confusion_figure.colorbar(image, ax=axes)
                colorbar.ax.tick_params(colors="white")
                colorbar.ax.set_facecolor(BG)
                positions = np.arange(len(labels))
                axes.set_xticks(positions, labels, rotation=35, ha="right")
                axes.set_yticks(positions, labels)
                axes.set_xlabel("Передбачений клас", color=TEXT)
                axes.set_ylabel("Справжній клас", color=TEXT)
                threshold = matrix.max() / 2
                for row in range(matrix.shape[0]):
                    for column in range(matrix.shape[1]):
                        color = BG if matrix[row, column] > threshold else TEXT
                        axes.text(
                            column,
                            row,
                            str(matrix[row, column]),
                            ha="center",
                            va="center",
                            color=color,
                        )

        self.confusion_figure.tight_layout()
        self.confusion_canvas.draw_idle()

    def _refresh_samples(self):
        _, labels = self.training_service.get_raw_data()
        sample_ids = self.training_service.get_sample_ids()
        self.samples_table.setRowCount(len(labels))

        for row, (sample_id, gesture) in enumerate(zip(sample_ids, labels)):
            timestamp = datetime.fromtimestamp(float(sample_id)).strftime(
                "%Y-%m-%d %H:%M:%S.%f"
            )
            self.samples_table.setItem(row, 0, QTableWidgetItem(timestamp))
            self.samples_table.setItem(
                row,
                1,
                QTableWidgetItem(
                    GESTURE_TRANSLATIONS.get(str(gesture), str(gesture))
                ),
            )
            button = QPushButton("Видалити")
            button.setStyleSheet(
                "background-color: #131826; color: #f472b6; "
                "border: 1px solid #f472b6; border-radius: 4px; padding: 4px 8px;"
            )
            button.clicked.connect(
                lambda checked=False, index=row: self._delete_sample(index)
            )
            self.samples_table.setCellWidget(row, 2, button)

    def _delete_sample(self, index):
        self.training_service.delete_sample(index)
        self.refresh_data()

    def _delete_selected_samples(self):
        rows = sorted(
            {item.row() for item in self.samples_table.selectionModel().selectedRows()},
            reverse=True,
        )
        if not rows:
            QMessageBox.information(
                self, "Видалення прикладів", "Спочатку виберіть один або кілька рядків."
            )
            return

        confirmation = QMessageBox.question(
            self,
            "Підтвердження",
            f"Видалити вибрані приклади ({len(rows)})?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirmation != QMessageBox.Yes:
            return

        for row in rows:
            self.training_service.delete_sample(row)
        self.refresh_data()

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Експортувати базу жестів",
            "gesture_samples.csv",
            "CSV файли (*.csv)",
        )
        if not path:
            return

        features, labels = self.training_service.get_raw_data()
        sample_ids = self.training_service.get_sample_ids()
        feature_count = features.shape[1] if features.ndim == 2 else 0
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                writer.writerow(
                    ["id", "gesture"]
                    + [f"feature_{i + 1}" for i in range(feature_count)]
                )
                for sample_id, label, sample in zip(sample_ids, labels, features):
                    writer.writerow(
                        [float(sample_id), str(label)]
                        + [float(value) for value in sample]
                    )
        except OSError as error:
            QMessageBox.critical(
                self, "Помилка експорту", f"Не вдалося записати CSV-файл:\n{error}"
            )
            return

        QMessageBox.information(self, "Експорт завершено", f"Файл збережено:\n{path}")

    def _feature_importance_figure(self):
        figure = Figure(figsize=(9, 7), dpi=100, facecolor=BG)
        axes = figure.add_subplot(111)
        self._style_axes(axes)
        try:
            importances = self.training_service.get_feature_importance()
        except ValueError as error:
            axes.text(
                0.5,
                0.5,
                str(error),
                color=TEXT,
                ha="center",
                va="center",
                transform=axes.transAxes,
            )
        else:
            names = self.training_service.get_feature_names(len(importances))
            order = np.argsort(importances)
            axes.barh(
                [names[index] for index in order],
                importances[order],
                color=VIOLET,
                edgecolor=CYAN,
            )
            axes.set_xlabel("Важливість ознаки", color=TEXT)
            axes.set_ylabel("Координати руки", color=TEXT)
            axes.set_title("Random Forest: важливість ознак", color=TEXT)
        figure.tight_layout()
        return figure

    def _export_pdf(self):
        results_dir = ROOT / "results"
        try:
            results_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            QMessageBox.critical(
                self, "Помилка експорту", f"Не вдалося створити папку results:\n{error}"
            )
            return

        default_path = results_dir / (
            f"analytics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Експортувати звіт",
            str(default_path),
            "PDF файли (*.pdf)",
        )
        if not path:
            return

        feature_figure = self._feature_importance_figure()
        try:
            with PdfPages(path) as report:
                report.savefig(self.distribution_figure, facecolor=BG)
                report.savefig(self.confusion_figure, facecolor=BG)
                report.savefig(feature_figure, facecolor=BG)
        except (OSError, ValueError) as error:
            QMessageBox.critical(
                self, "Помилка експорту", f"Не вдалося створити PDF-звіт:\n{error}"
            )
            return
        finally:
            feature_figure.clear()

        QMessageBox.information(self, "Звіт експортовано", f"Файл збережено:\n{path}")

    def _open_labs_dialog(self):
        dialog = LabDialog(self.training_service, self)
        dialog.exec()
