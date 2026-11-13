import cv2

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QMessageBox, QFrame)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap

from ui.widgets.glow_button import GlowButton
from services.training_service import TrainingService

class TrainingTab(QWidget):
    # Сигнали для зв'язку з головним вікном (щоб брати кадри з камери)
    request_current_features = Signal()
    
    def __init__(self):
        super().__init__()
        self.training_service = TrainingService()
        self.current_features = None  # Сюди будемо отримувати координати з камери
        
        self.build_ui()
        self.update_table()

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

        self.preview_label = QLabel()
        self.preview_label.setObjectName("TrainingPreview")
        self.preview_label.setFixedSize(320, 240)
        self.preview_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.preview_label)

        self.input_gesture = QLineEdit()
        self.input_gesture.setObjectName("TrainingGestureInput")
        self.input_gesture.setPlaceholderText("Назва жесту (напр. 'Серце')")
        left_layout.addWidget(self.input_gesture)

        btn_capture = GlowButton("📸 ЗАПИСАТИ 1 ПРИКЛАД", color="#4da6ff")
        btn_capture.clicked.connect(self.capture_sample)
        left_layout.addWidget(btn_capture)

        btn_capture_3s = GlowButton("⏱️ ЗАПИСАТИ 3 СЕКУНДИ", color="#8b5cf6")
        btn_capture_3s.clicked.connect(self.capture_3s)
        left_layout.addWidget(btn_capture_3s)

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

        btn_clear = GlowButton("🗑️ ОЧИСТИТИ БАЗУ", color="#f472b6")
        btn_clear.clicked.connect(self.clear_data)
        right_panel.addWidget(btn_clear)

        layout.addWidget(left_panel, 1)
        layout.addLayout(right_panel, 2)

    def set_current_features(self, features):
        """Викликається з головного вікна, коли є новий кадр"""
        self.current_features = features

    def update_preview(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, channels = rgb_frame.shape
        image = QImage(
            rgb_frame.data, w, h, channels * w, QImage.Format_RGB888
        ).copy()
        pixmap = QPixmap.fromImage(image).scaled(
            self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.preview_label.setPixmap(pixmap)

    def capture_sample(self):
        name = self.input_gesture.text().strip()
        if not name:
            QMessageBox.warning(self, "Помилка", "Введіть назву жесту!")
            return
        
        if self.current_features is None:
            QMessageBox.warning(self, "Помилка", "Руку не знайдено в кадрі!")
            return

        self.training_service.add_sample(name, self.current_features)
        self.update_table()
        QMessageBox.information(self, "Успіх", f"Приклад для '{name}' додано!")

    def capture_3s(self):
        # У майбутньому тут буде таймер, поки що просто заглушка
        QMessageBox.information(self, "Інфо", "Функція в розробці. Використовуйте 'Записати 1 приклад'.")

    def train_model(self):
        success, msg = self.training_service.train_model()
        if success:
            QMessageBox.information(self, "Успіх", msg)
        else:
            QMessageBox.warning(self, "Помилка", msg)

    def clear_data(self):
        reply = QMessageBox.question(self, "Очистити", "Ви впевнені, що хочете видалити всі дані?", 
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.training_service.clear_data()
            self.update_table()

    def update_table(self):
        stats = self.training_service.get_stats()
        self.table.setRowCount(len(stats))
        for row, (gesture, count) in enumerate(stats.items()):
            self.table.setItem(row, 0, QTableWidgetItem(gesture))
            self.table.setItem(row, 1, QTableWidgetItem(str(count)))