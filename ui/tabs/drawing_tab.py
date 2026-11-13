import math
import random
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QLinearGradient,
    QPainter,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core.filters import OneEuroFilter
from core.types import DRAWINGS_DIR


HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15),
    (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17),
)


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    size: float
    color: QColor
    age: float
    lifetime: float


class DrawingCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(480, 360)
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)

        self.color = QColor("#4da6ff")
        self.brush_size = 8
        self.background_mode = "Камера"
        self.hand_drawing_enabled = False
        self._frame = None
        self._hands = []
        self._finger_point = None
        self._last_finger_point = None
        self._finger_x_filter = OneEuroFilter(mincutoff=1.0, beta=0.05)
        self._finger_y_filter = OneEuroFilter(mincutoff=1.0, beta=0.05)

        self._mouse_down = False
        self._mouse_last_point = None
        self._strokes = QImage(self.size(), QImage.Format_ARGB32_Premultiplied)
        self._strokes.fill(Qt.transparent)
        self._particles = []
        self._scan_y = 0.0
        self._last_tick = time.monotonic()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def set_color(self, color):
        self.color = QColor(color)

    def set_background_mode(self, mode):
        if self.background_mode != mode:
            self._last_finger_point = None
            self._reset_finger_filters()
        self.background_mode = mode
        self.update()

    def set_hand_drawing_enabled(self, enabled):
        self.hand_drawing_enabled = bool(enabled)
        self._finger_point = None
        self._last_finger_point = None
        self._reset_finger_filters()
        self.update()

    def set_frame(self, frame, tracked_hands):
        if frame is None:
            self._frame = None
        else:
            height, width = frame.shape[:2]
            self._frame = QImage(
                frame.data,
                width,
                height,
                int(frame.strides[0]),
                QImage.Format_BGR888,
            ).copy()

        self._hands = [
            [(float(point[0]), float(point[1])) for point in points]
            for points in (tracked_hands or {}).values()
            if len(points) >= 21
        ]

        if self._hands and self.hand_drawing_enabled:
            target = self._frame_rect() if self.background_mode == "Камера" else QRectF(self.rect())
            x, y = self._hands[0][8]
            now = time.monotonic()
            finger = QPointF(
                self._finger_x_filter.filter(target.left() + x * target.width(), now),
                self._finger_y_filter.filter(target.top() + y * target.height(), now),
            )
            if self._last_finger_point is not None and not self._mouse_down:
                if self._last_finger_point != finger:
                    self._draw_glowing_line(self._last_finger_point, finger)
                    self._spawn_particles(finger)
            self._finger_point = finger
            self._last_finger_point = finger
        else:
            self._finger_point = None
            self._last_finger_point = None
            self._reset_finger_filters()

        self.update()

    def clear(self):
        self._strokes.fill(Qt.transparent)
        self._particles.clear()
        self._last_finger_point = None
        self.update()

    def save(self, path):
        return self.grab().save(str(path), "PNG")

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        rect = QRectF(self.rect())
        self._draw_scene_background(painter, rect)

        if self.background_mode == "Голограма":
            self._draw_hand_skeletons(painter, rect)

        painter.setCompositionMode(QPainter.CompositionMode_Plus)
        painter.drawImage(self.rect(), self._strokes)
        self._draw_particles(painter)
        self._draw_finger_cursor(painter)
        if not self.hand_drawing_enabled and not self._mouse_down:
            self._draw_scan_beam(painter, rect)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._mouse_down = True
            self._mouse_last_point = event.position()
            self._draw_glowing_line(self._mouse_last_point, self._mouse_last_point)
            self._spawn_particles(self._mouse_last_point)
            self.update()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._mouse_down and self._mouse_last_point is not None:
            current = event.position()
            self._draw_glowing_line(self._mouse_last_point, current)
            self._spawn_particles(current)
            self._mouse_last_point = current
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._mouse_down = False
            self._mouse_last_point = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        new_strokes = QImage(event.size(), QImage.Format_ARGB32_Premultiplied)
        new_strokes.fill(Qt.transparent)
        painter = QPainter(new_strokes)
        painter.drawImage(0, 0, self._strokes)
        painter.end()
        self._strokes = new_strokes
        self._last_finger_point = None
        self._reset_finger_filters()
        super().resizeEvent(event)

    def showEvent(self, event):
        self._last_tick = time.monotonic()
        self._timer.start(16)
        super().showEvent(event)

    def hideEvent(self, event):
        self._timer.stop()
        self._particles.clear()
        self._finger_point = None
        self._last_finger_point = None
        self._reset_finger_filters()
        super().hideEvent(event)

    def _reset_finger_filters(self):
        self._finger_x_filter = OneEuroFilter(mincutoff=1.0, beta=0.05)
        self._finger_y_filter = OneEuroFilter(mincutoff=1.0, beta=0.05)

    def _frame_rect(self):
        return QRectF(self.rect())

    def _draw_scene_background(self, painter, rect):
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, QColor("#050916"))
        gradient.setColorAt(1, QColor("#0b1730"))
        painter.fillRect(rect, QBrush(gradient))

        if self.background_mode == "Камера" and self._frame is not None:
            painter.drawImage(self.rect(), self._frame)
        else:
            if self.background_mode == "Чорний":
                painter.fillRect(rect, QColor("#03050b"))
            self._draw_grid(painter, rect)

        vignette = QRadialGradient(rect.center(), max(rect.width(), rect.height()) * 0.8)
        vignette.setColorAt(0.52, QColor(0, 0, 0, 0))
        vignette.setColorAt(1, QColor(0, 0, 0, 135))
        painter.fillRect(rect, QBrush(vignette))

    def _draw_grid(self, painter, rect):
        alpha = 45 if self.background_mode == "Голограма" else 24
        painter.setPen(QPen(QColor(77, 166, 255, alpha), 1))
        step = 48
        x = rect.left()
        while x <= rect.right():
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            x += step
        y = rect.top()
        while y <= rect.bottom():
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            y += step

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(77, 166, 255, alpha + 12))
        for x in range(12, self.width(), 24):
            for y in range(12, self.height(), 24):
                painter.drawEllipse(QPointF(x, y), 1, 1)

    def _draw_hand_skeletons(self, painter, rect):
        painter.save()
        painter.setCompositionMode(QPainter.CompositionMode_Plus)
        for points in self._hands:
            pixels = [QPointF(x * rect.width(), y * rect.height()) for x, y in points]
            for width, alpha in ((10, 32), (5, 90), (2, 230)):
                painter.setPen(
                    QPen(QColor(77, 166, 255, alpha), width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                )
                for start, end in HAND_CONNECTIONS:
                    painter.drawLine(pixels[start], pixels[end])
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(220, 250, 255, 220))
            for index in (4, 8, 12, 16, 20):
                painter.drawEllipse(pixels[index], 3, 3)
        painter.restore()

    def _draw_glowing_line(self, start, end):
        painter = QPainter(self._strokes)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode_Plus)
        scale = self.brush_size / 8
        for base_width, alpha in ((10, 30), (5, 80), (2, 255)):
            color = QColor(self.color)
            color.setAlpha(alpha)
            painter.setPen(
                QPen(color, base_width * scale, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            )
            if start == end:
                painter.drawPoint(start)
            else:
                painter.drawLine(start, end)
        painter.end()

    def _spawn_particles(self, point):
        for _ in range(random.randint(2, 4)):
            angle = random.uniform(0, 2 * 3.141592653589793)
            speed = random.uniform(24, 96)
            self._particles.append(
                Particle(
                    x=point.x(),
                    y=point.y(),
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    size=random.uniform(1.2, 3.2),
                    color=QColor(self.color),
                    age=0.0,
                    lifetime=random.uniform(0.5, 1.0),
                )
            )
        if len(self._particles) > 400:
            self._particles = self._particles[-400:]

    def _draw_particles(self, painter):
        painter.save()
        painter.setCompositionMode(QPainter.CompositionMode_Plus)
        painter.setPen(Qt.NoPen)
        for particle in self._particles:
            opacity = max(0.0, 1.0 - particle.age / particle.lifetime)
            color = QColor(particle.color)
            color.setAlphaF(opacity)
            painter.setBrush(color)
            painter.drawEllipse(QPointF(particle.x, particle.y), particle.size, particle.size)
        painter.restore()

    def _draw_finger_cursor(self, painter):
        point = self._finger_point
        if point is None:
            return
        painter.save()
        painter.setCompositionMode(QPainter.CompositionMode_Plus)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(77, 166, 255, 100), 7))
        painter.drawEllipse(point, 11, 11)
        painter.setPen(QPen(QColor(220, 250, 255, 240), 1.5))
        painter.drawEllipse(point, 7, 7)
        painter.setPen(QPen(QColor(139, 92, 246, 220), 1))
        painter.drawLine(point + QPointF(-15, 0), point + QPointF(-9, 0))
        painter.drawLine(point + QPointF(9, 0), point + QPointF(15, 0))
        painter.drawLine(point + QPointF(0, -15), point + QPointF(0, -9))
        painter.drawLine(point + QPointF(0, 9), point + QPointF(0, 15))
        painter.restore()

    def _draw_scan_beam(self, painter, rect):
        y = rect.top() + self._scan_y
        beam = QLinearGradient(0, y - 22, 0, y + 22)
        beam.setColorAt(0, QColor(77, 166, 255, 0))
        beam.setColorAt(0.5, QColor(77, 166, 255, 32))
        beam.setColorAt(1, QColor(77, 166, 255, 0))
        painter.fillRect(QRectF(rect.left(), y - 22, rect.width(), 44), QBrush(beam))
        painter.setPen(QPen(QColor(77, 166, 255, 165), 1.3))
        painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))

    def _tick(self):
        now = time.monotonic()
        dt = min(now - self._last_tick, 0.05)
        self._last_tick = now
        self._scan_y = (self._scan_y + max(1, self.height()) * dt * 0.16) % max(1, self.height())

        for particle in self._particles:
            particle.age += dt
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
        self._particles = [
            particle for particle in self._particles if particle.age < particle.lifetime
        ]
        self.update()


class DrawingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("DrawingTab")
        self.setStyleSheet(
            "QWidget#DrawingTab { background-color: #0a0e1a; }"
        )
        self.canvas = DrawingCanvas()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QFrame(self.canvas)
        toolbar.setObjectName("SidePanel")
        toolbar_layout = QVBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(12, 8, 12, 8)
        toolbar_layout.setSpacing(6)

        top_tools = QHBoxLayout()
        top_tools.setSpacing(7)
        top_tools.addWidget(QLabel("ФОН"))
        self.background_combo = QComboBox()
        self.background_combo.addItems(("Камера", "Голограма", "Чорний"))
        self.background_combo.setCurrentText("Камера")
        self.background_combo.currentTextChanged.connect(self.canvas.set_background_mode)
        top_tools.addWidget(self.background_combo)

        top_tools.addWidget(QLabel("ПАЛІТРА"))
        self.palette_group = QButtonGroup(self)
        palette = (
            ("Блакитний", "#00d4ff"),
            ("Фіолетовий", "#8b5cf6"),
            ("Зелений", "#4ade80"),
            ("Рожевий", "#f472b6"),
            ("Білий", "#ffffff"),
            ("Жовтий", "#facc15"),
        )
        self.palette_buttons = []
        for index, (name, color) in enumerate(palette):
            button = QPushButton()
            button.setObjectName("PaletteSwatch")
            button.setAccessibleName(name)
            button.setToolTip(name)
            button.setFixedSize(28, 28)
            button.setCheckable(True)
            button.setStyleSheet(
                f"QPushButton {{ background-color: {color}; border: 1px solid "
                f"rgba(226,232,240,0.65); border-radius: 14px; padding: 0; }}"
                "QPushButton:checked { border: 3px solid #e2e8f0; }"
            )
            self.palette_group.addButton(button)
            button.clicked.connect(
                lambda _checked=False, selected=color: self.canvas.set_color(selected)
            )
            if index == 0:
                button.setChecked(True)
                self.canvas.set_color(color)
            self.palette_buttons.append(button)
            top_tools.addWidget(button)

        self.hand_draw_button = QPushButton("✋ МАЛЮВАННЯ РУКОЮ")
        self.hand_draw_button.setObjectName("HandDrawToggle")
        self.hand_draw_button.setCheckable(True)
        self.hand_draw_button.setChecked(False)
        self.hand_draw_button.toggled.connect(self.canvas.set_hand_drawing_enabled)
        top_tools.addWidget(self.hand_draw_button)
        top_tools.addStretch()
        toolbar_layout.addLayout(top_tools)

        bottom_tools = QHBoxLayout()
        bottom_tools.setSpacing(7)
        bottom_tools.addWidget(QLabel("ТОВЩИНА"))
        self.brush_slider = QSlider(Qt.Horizontal)
        self.brush_slider.setRange(2, 24)
        self.brush_slider.setValue(self.canvas.brush_size)
        self.brush_slider.setMaximumWidth(180)
        self.brush_slider.valueChanged.connect(self._set_brush_size)
        bottom_tools.addWidget(self.brush_slider)
        self.brush_value = QLabel(str(self.canvas.brush_size))
        self.brush_value.setMinimumWidth(22)
        bottom_tools.addWidget(self.brush_value)
        bottom_tools.addStretch()

        clear_button = QPushButton("🧹 Очистити")
        clear_button.clicked.connect(self.canvas.clear)
        bottom_tools.addWidget(clear_button)

        save_button = QPushButton("💾 Зберегти PNG")
        save_button.clicked.connect(self._save_png)
        bottom_tools.addWidget(save_button)
        toolbar_layout.addLayout(bottom_tools)

        canvas_layout = QVBoxLayout(self.canvas)
        canvas_layout.setContentsMargins(16, 16, 16, 16)
        canvas_layout.setSpacing(0)
        canvas_layout.addWidget(toolbar, 0, Qt.AlignTop)
        canvas_layout.addStretch(1)
        layout.addWidget(self.canvas, 1)

    def set_frame(self, frame, tracked_hands):
        self.canvas.set_frame(frame, tracked_hands)

    def _set_brush_size(self, size):
        self.canvas.brush_size = size
        self.brush_value.setText(str(size))

    def _save_png(self):
        try:
            DRAWINGS_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            QMessageBox.critical(
                self, "Помилка", f"Не вдалося створити папку для малюнків:\n{error}"
            )
            return

        default_path = DRAWINGS_DIR / (
            f"drawing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Зберегти малюнок",
            str(default_path),
            "PNG зображення (*.png)",
        )
        if not path:
            return

        if Path(path).suffix.lower() != ".png":
            path = f"{path}.png"
        if not self.canvas.save(path):
            QMessageBox.critical(self, "Помилка", "Не вдалося зберегти PNG-файл.")
            return

        QMessageBox.information(self, "Збережено", f"Малюнок збережено:\n{path}")
