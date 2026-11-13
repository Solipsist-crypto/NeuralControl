from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget


CYAN = QColor("#4da6ff")
VIOLET = QColor("#8b5cf6")


class HudBackground(QWidget):
    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)

        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, QColor("#0a0e1a"))
        gradient.setColorAt(1, QColor("#0d1226"))
        painter.fillPath(path, QBrush(gradient))

        painter.save()
        painter.setClipPath(path)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(77, 166, 255, 24))
        for x in range(14, self.width(), 28):
            for y in range(14, self.height(), 28):
                painter.drawEllipse(QPointF(x, y), 1.1, 1.1)

        for position, color, radius in (
            (rect.topRight(), VIOLET, 520),
            (rect.bottomLeft(), CYAN, 420),
        ):
            glow = QRadialGradient(position, radius)
            glow.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 22))
            glow.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
            painter.fillRect(rect, QBrush(glow))

        vignette = QRadialGradient(rect.center(), max(rect.width(), rect.height()) * 0.75)
        vignette.setColorAt(0.55, QColor(0, 0, 0, 0))
        vignette.setColorAt(1, QColor(0, 0, 0, 145))
        painter.fillRect(rect, QBrush(vignette))
        painter.restore()

        border = QLinearGradient(rect.topLeft(), rect.bottomRight())
        border.setColorAt(0, QColor(77, 166, 255, 105))
        border.setColorAt(0.5, QColor(139, 92, 246, 85))
        border.setColorAt(1, QColor(77, 166, 255, 105))
        painter.setPen(QPen(QBrush(border), 1))
        painter.drawPath(path)

        painter.setPen(QPen(QColor(77, 166, 255, 170), 1.5))
        painter.drawLine(rect.left() + 16, rect.top() + 36, rect.left() + 16, rect.top() + 72)
        painter.drawLine(rect.left() + 16, rect.top() + 36, rect.left() + 64, rect.top() + 36)
        painter.setPen(QPen(QColor(139, 92, 246, 150), 1.5))
        painter.drawLine(rect.right() - 16, rect.bottom() - 36, rect.right() - 16, rect.bottom() - 72)
        painter.drawLine(rect.right() - 16, rect.bottom() - 36, rect.right() - 64, rect.bottom() - 36)
        painter.end()
