from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QGroupBox, QFormLayout, QCheckBox
)
from ui.widgets.video_view import VideoView
from services.camera_service import CameraThread
from services.gesture_controller import GestureController

class ControlTab(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout(self)
        
        # --- ЛІВА ЧАСТИНА: ВІДЕО ---
        self.video_view = VideoView()
        self.layout.addWidget(self.video_view, stretch=3)

        # --- ПРАВА ЧАСТИНА: ПАНЕЛЬ КЕРУВАННЯ ---
        side_panel = QWidget()
        side_layout = QVBoxLayout(side_panel)
        side_panel.setFixedWidth(300)

        # Статус
        status_group = QGroupBox("Статус")
        status_layout = QFormLayout(status_group)
        self.lbl_mode = QLabel("Очікування")
        self.lbl_mode.setStyleSheet("color: #00d4ff; font-weight: bold;")
        self.lbl_hands = QLabel("0")
        status_layout.addRow("Режим:", self.lbl_mode)
        status_layout.addRow("Рук в кадрі:", self.lbl_hands)
        side_layout.addWidget(status_group)

        # Налаштування
        settings_group = QGroupBox("Налаштування")
        settings_layout = QVBoxLayout(settings_group)
        
        self.btn_toggle_mode = QPushButton("Увімкнути Голограму")
        self.btn_toggle_mode.clicked.connect(self.toggle_mode)
        settings_layout.addWidget(self.btn_toggle_mode)

        self.chk_actions = QCheckBox("Активувати жести (pyautogui)")
        self.chk_actions.setStyleSheet("color: #ff3366; font-weight: bold;")
        settings_layout.addWidget(self.chk_actions)
        
        side_layout.addWidget(settings_group)
        side_layout.addStretch()

        self.layout.addWidget(side_panel, stretch=1)

        # --- ЗАПУСК СЕРВІСІВ ---
        self.fps = 0
        self.frame_count = 0
        self.last_time = 0

        self.controller = GestureController()
        self.controller.processed_frame.connect(self.on_frame_processed)

        self.camera = CameraThread(camera_index=0)
        self.camera.frame_ready.connect(self.controller.process_frame)
        self.camera.start()

        # Таймер для FPS
        self.fps_timer = QTimer(self)
        self.fps_timer.timeout.connect(self.calc_fps)
        self.fps_timer.start(1000)

    def toggle_mode(self):
        if self.video_view.mode == 1:
            self.video_view.mode = 2
            self.btn_toggle_mode.setText("Увімкнути Камеру")
            self.lbl_mode.setText("Голограма")
        else:
            self.video_view.mode = 1
            self.btn_toggle_mode.setText("Увімкнути Голограму")
            self.lbl_mode.setText("Камера")

    def on_frame_processed(self, frame, hands):
        self.frame_count += 1
        self.lbl_hands.setText(str(len(hands)))
        # Оновлюємо відео
        self.video_view.update_frame(frame, hands, self.fps)

    def calc_fps(self):
        self.fps = self.frame_count
        self.frame_count = 0

    def stop(self):
        self.camera.stop()
        self.controller.stop()