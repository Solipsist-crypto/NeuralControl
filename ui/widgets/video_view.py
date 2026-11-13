import cv2
import numpy as np
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QFont
from PySide6.QtWidgets import QWidget

class VideoView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(640, 480)
        self.image = None
        self.hands = {}
        self.mode = 1 # 1 - Normal, 2 - Hologram
        self.fps = 0

    def update_frame(self, frame, hands, fps):
        self.image = frame
        self.hands = hands
        self.fps = fps
        self.update() # Викликає paintEvent

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. Малюємо фон (або чорний, або камеру)
        if self.mode == 2 or self.image is None:
            painter.fillRect(self.rect(), QColor("#0a0e1a")) # Темний фон
        else:
            # Конвертуємо OpenCV BGR у QImage RGB
            rgb_image = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            painter.drawImage(self.rect(), q_img)

        # 2. Малюємо неоновий скелет
        if self.hands:
            connections = [
                (0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),
                (5,9),(9,10),(10,11),(11,12),(9,13),(13,14),(14,15),(15,16),
                (13,17),(17,18),(18,19),(19,20),(0,17)
            ]
            
            # Кольори залежно від режиму
            if self.mode == 2:
                line_color = QColor(0, 255, 255) # Cyan
                dot_color = QColor(255, 0, 255)  # Magenta
                glow_color = QColor(255, 0, 255, 100)
            else:
                line_color = QColor(124, 58, 237)
                dot_color = QColor(0, 212, 255)
                glow_color = QColor(0, 212, 255, 100)

            w, h = self.width(), self.height()

            for slot_id, pts in self.hands.items():
                # Малюємо лінії
                pen = QPen(line_color, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                painter.setPen(pen)
                for c in connections:
                    p1, p2 = pts[c[0]], pts[c[1]]
                    painter.drawLine(int(p1[0]*w), int(p1[1]*h), int(p2[0]*w), int(p2[1]*h))

                # Малюємо точки з ефектом світіння
                painter.setPen(Qt.NoPen)
                for pt in pts:
                    cx, cy = int(pt[0]*w), int(pt[1]*h)
                    # Світіння
                    painter.setBrush(glow_color)
                    painter.drawEllipse(cx - 10, cy - 10, 20, 20)
                    # Ядро
                    painter.setBrush(dot_color)
                    painter.drawEllipse(cx - 4, cy - 4, 8, 8)

        # 3. HUD (Інтерфейс поверх відео)
        painter.setPen(QColor("#00ff88"))
        font = QFont("Segoe UI", 12, QFont.Bold)
        painter.setFont(font)
        painter.drawText(20, 30, f"FPS: {self.fps} | Mode: {'HOLOGRAM' if self.mode==2 else 'CAMERA'}")