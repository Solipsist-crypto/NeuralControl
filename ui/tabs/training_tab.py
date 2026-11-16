import time
import numpy as np

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QMessageBox, QFrame, QCheckBox)
from PySide6.QtCore import Signal, QTimer

from ui.widgets.glow_button import GlowButton
from ui.widgets.video_view import VideoView
from services.training_service import TrainingService

class TrainingTab(QWidget):
    # Сигнали для зв'язку з головним вікном (щоб брати кадри з камери)
    request_current_features = Signal()
    model_trained = Signal()
    gesture_recorded = Signal()
    
    def __init__(self):
        super().__init__()
        self.training_service = TrainingService()
        self.current_features = None  # Сюди будемо отримувати координати з камери
        self._capture_samples = []
        self._capture_name = ""
        self._capture_deadline = 0.0
        self._capture_controls = []
        self._capture_timer = QTimer(self)
        self._capture_timer.setInterval(100)
        self._capture_timer.timeout.connect(self._collect_training_sample)
        
        self.build_ui()
        self.update_table()
        self._update_model_status()

    def build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # ЛІВА ПАНЕЛЬ: Додавання жестів
        left_panel = QFrame()
        left_panel.setObjectName("SidePanel")
        left_layout = QVBoxLayout(left_panel)
        
        title = QLabel("ЗАПИС НОВОГО ЖЕСТУ")
        title.setObjectName("TrainingPanelTitle")
        left_layout.addWidget(title)

        self.preview_view = VideoView()
        self.preview_view.setMinimumSize(240, 180)
        self.preview_view.setMaximumHeight(260)
        self.preview_view.holo = True
        self.preview_view.skeleton = True
        self.preview_view.scan = False
        left_layout.addWidget(self.preview_view)

        self.show_skeleton_checkbox = QCheckBox("ПОКАЗАТИ СКЕЛЕТ")
        self.show_skeleton_checkbox.setChecked(True)
        self.show_skeleton_checkbox.toggled.connect(self._set_skeleton_visible)
        left_layout.addWidget(self.show_skeleton_checkbox)

        self.input_gesture = QLineEdit()
        self.input_gesture.setObjectName("TrainingGestureInput")
        self.input_gesture.setPlaceholderText("Назва жесту (напр. 'Серце')")
        left_layout.addWidget(self.input_gesture)

        self.capture_sample_button = GlowButton(
            "📸 ЗАПИСАТИ 1 ПРИКЛАД", color="#4da6ff"
        )
        self.capture_sample_button.clicked.connect(self.capture_sample)
        left_layout.addWidget(self.capture_sample_button)
        self._capture_controls.append(self.capture_sample_button)

        self.capture_5s_button = GlowButton(
            "⏱️ ЗАПИСАТИ 5 СЕКУНД", color="#8b5cf6"
        )
        self.capture_5s_button.clicked.connect(self.capture_5s)
        left_layout.addWidget(self.capture_5s_button)

        left_layout.addStretch()
        
        # Права панель: Таблиця та навчання
        right_panel = QVBoxLayout()
        
        title2 = QLabel("БАЗА ЗНАНЬ (ДАТАСЕТ)")
        title2.setObjectName("TrainingDatasetTitle")
        right_panel.addWidget(title2)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["ЖЕСТ", "ПРИКЛАДІВ"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        right_panel.addWidget(self.table)

        btn_train = GlowButton("🧠 НАВЧИТИ НЕЙРОМЕРЕЖУ", color="#4ade80")
        btn_train.clicked.connect(self.train_model)
        right_panel.addWidget(btn_train)
        self._capture_controls.append(btn_train)
        self.model_status_label = QLabel()
        self.model_status_label.setWordWrap(True)
        self.model_status_label.setStyleSheet("color:#94a3b8;")
        right_panel.addWidget(self.model_status_label)

        btn_clear = GlowButton("🗑️ ОЧИСТИТИ БАЗУ", color="#f472b6")
        btn_clear.clicked.connect(self.clear_data)
        right_panel.addWidget(btn_clear)
        self._capture_controls.append(btn_clear)

        layout.addWidget(left_panel, 1)
        layout.addLayout(right_panel, 2)

    def set_current_features(self, features):
        """Викликається з головного вікна, коли є новий кадр"""
        self.current_features = np.asarray(features, dtype=np.float32).reshape(-1)

    def update_preview(self, frame, tracked_hands=None, predictions=None, fps=0.0):
        self.preview_view.set_frame(
            frame,
            tracked_hands or {},
            fps,
            predictions,
        )

    def _set_skeleton_visible(self, visible):
        self.preview_view.skeleton = visible
        self.preview_view.update()

    def capture_sample(self):
        name = self.input_gesture.text().strip()
        if not name:
            QMessageBox.warning(self, "Помилка", "Введіть назву жесту!")
            return
        
        if self.current_features is None:
            QMessageBox.warning(self, "Помилка", "Руку не знайдено в кадрі!")
            return

        try:
            normalized_name = self.training_service.add_sample(
                name, self.current_features
            )
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Помилка запису", str(error))
            return

        self.update_table()
        self._update_model_status()
        self.gesture_recorded.emit()
        QMessageBox.information(
            self,
            "Успіх",
            f"Приклад для '{normalized_name}' додано до бази знань.",
        )

    def capture_5s(self):
        name = self.input_gesture.text().strip()
        if not name:
            QMessageBox.warning(self, "Помилка", "Введіть назву жесту!")
            return
        if self.current_features is None:
            QMessageBox.warning(self, "Помилка", "Руку не знайдено в кадрі!")
            return

        self._capture_name = name
        self._capture_samples = []
        self._capture_deadline = time.monotonic() + 5.0
        self._set_capture_active(True)
        self._capture_timer.start()
        self._collect_training_sample()

    def _collect_training_sample(self):
        remaining = self._capture_deadline - time.monotonic()
        if remaining <= 0:
            self._finish_capture()
            return

        if self.current_features is not None:
            self._capture_samples.append(self.current_features.copy())
        self.capture_5s_button.setText(
            f"ЗАПИС... {int(remaining + 0.999)} С"
        )

    def _finish_capture(self):
        self._capture_timer.stop()
        self._set_capture_active(False)
        samples = self._capture_samples
        self._capture_samples = []

        if not samples:
            QMessageBox.warning(
                self, "Помилка запису", "За 5 секунд не знайдено жодної руки."
            )
            return

        try:
            normalized_name = self.training_service.add_samples(
                self._capture_name, np.stack(samples)
            )
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Помилка запису", str(error))
            return

        self.update_table()
        self._update_model_status()
        self.gesture_recorded.emit()
        QMessageBox.information(
            self,
            "Успіх",
            f"Для '{normalized_name}' записано {len(samples)} прикладів за 5 секунд.",
        )

    def _set_capture_active(self, active):
        self.capture_5s_button.setEnabled(not active)
        self.capture_5s_button.setText(
            "ЗАПИС..." if active else "⏱️ ЗАПИСАТИ 5 СЕКУНД"
        )
        for control in self._capture_controls:
            control.setEnabled(not active)

    def train_model(self):
        try:
            success, msg = self.training_service.train_model()
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Помилка навчання", str(error))
            return
        if success:
            QMessageBox.information(self, "Успіх", msg)
            self._update_model_status()
            self.model_trained.emit()
        else:
            QMessageBox.warning(self, "Помилка", msg)

    def clear_data(self):
        reply = QMessageBox.question(self, "Очистити", "Ви впевнені, що хочете видалити всі дані?", 
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.training_service.clear_data()
            self.update_table()
            self._update_model_status()
            self.gesture_recorded.emit()
            self.model_trained.emit()

    def update_table(self):
        stats = self.training_service.get_stats()
        self.table.setRowCount(len(stats))
        for row, (gesture, count) in enumerate(stats.items()):
            self.table.setItem(row, 0, QTableWidgetItem(gesture))
            self.table.setItem(row, 1, QTableWidgetItem(str(count)))

    def _update_model_status(self):
        if self.training_service.data_error:
            message = self.training_service.data_error
            color = "#f87171"
        elif self.training_service.model_error:
            message = self.training_service.model_error
            if self.training_service.migration_notice:
                message += " " + self.training_service.migration_notice
            color = "#fbbf24"
        elif self.training_service.model_stale:
            message = "Приклади змінилися — перенавчіть модель перед використанням."
            color = "#fbbf24"
        elif self.training_service.model is not None:
            message = "Модель навчена на 126 ознаках."
            if self.training_service.migration_notice:
                message += " " + self.training_service.migration_notice
            color = "#4ade80"
        elif self.training_service.migration_notice:
            message = self.training_service.migration_notice
            color = "#fbbf24"
        else:
            message = "Модель ще не навчена."
            color = "#94a3b8"
        self.model_status_label.setText(message)
        self.model_status_label.setStyleSheet(f"color:{color};")