from PySide6.QtCore import Qt, QRectF, QPointF, QVariantAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QRadialGradient, QFont, QTextCursor, QPainterPath
from PySide6.QtWidgets import QPushButton, QWidget, QPlainTextEdit, QFrame
from collections import deque
import time

CYAN, VIOLET = QColor("#00d4ff"), QColor("#7c3aed")
GREEN, PINK = QColor("#00ff88"), QColor("#ff2e97")
TEXT, MUTED = QColor("#e6f1ff"), QColor("#6b7a99")

def a(color, alpha):
    c = QColor(color)
    c.setAlpha(max(0, min(255, int(alpha))))
    return c

def mkfont(size, weight=QFont.Normal, spacing=0.0, mono=False):
    f = QFont()
    f.setFamilies(["JetBrains Mono", "Consolas"] if mono else ["Orbitron", "Rajdhani", "Segoe UI"])
    f.setPixelSize(size)
    f.setWeight(weight)
    if spacing:
        f.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
    return f

class GlowButton(QPushButton):
    def __init__(self, text, color=CYAN, checkable=False):
        super().__init__(text)
        self._c = QColor(color)
        self._g = 0.0
        self.setCheckable(checkable)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(38)
        self.setFont(mkfont(11, QFont.DemiBold, 1.2))
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._set_g)

    def _set_g(self, v):
        self._g = float(v)
        self.update()

    def _go(self, end):
        self._anim.stop()
        self._anim.setStartValue(float(self._g))
        self._anim.setEndValue(float(end))
        self._anim.start()

    def enterEvent(self, e):
        self._go(1.0)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._go(0.0)
        super().leaveEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        on = self.isCheckable() and self.isChecked()
        k = max(self._g, 0.7 if on else 0.0)
        r = QRectF(self.rect()).adjusted(5, 5, -5, -5)
        p.setBrush(Qt.NoBrush)
        for i, w in enumerate((10, 6, 3)):
            p.setPen(QPen(a(self._c, (6 + 12 * i) * (0.4 + k * 1.6)), w))
            p.drawRoundedRect(r, 7, 7)
        p.setPen(QPen(a(self._c, 120 + 135 * k), 1))
        p.setBrush(a(self._c, 18 + 55 * k + (35 if self.isDown() else 0)))
        p.drawRoundedRect(r, 7, 7)
        tx = r
        if self.isCheckable():
            p.setPen(Qt.NoPen)
            p.setBrush(a(self._c, 255) if on else a(self._c, 60))
            p.drawRect(QRectF(r.left() + 10, r.center().y() - 3, 6, 6))
            tx = r.adjusted(14, 0, 0, 0)
        p.setPen(self._c if self.isEnabled() else QColor("#3a4560"))
        p.setFont(self.font())
        p.drawText(tx, Qt.AlignCenter, self.text())

class ArcReactor(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(150)
        self.phase, self.fps, self.hands = 0.0, 0.0, 0

    def advance(self, dt):
        self.phase += dt
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2)
        R = min(self.width(), self.height()) / 2 - 8
        ph = self.phase
        rings = [(R, 3, 70, 40, 2.5, CYAN), (R * 0.82, 2, 140, -70, 2, VIOLET),
                 (R * 0.66, 12, 18, 90, 4, CYAN), (R * 0.5, 4, 60, -120, 2, GREEN)]
        p.setBrush(Qt.NoBrush)
        for rad, n, span, speed, width, col in rings:
            rect = QRectF(c.x() - rad, c.y() - rad, 2 * rad, 2 * rad)
            for k in range(n):
                start = ph * speed + k * 360 / n
                p.setPen(QPen(a(col, 28), width * 3.2, Qt.SolidLine, Qt.FlatCap))
                p.drawArc(rect, int(start * 16), int(span * 16))
                p.setPen(QPen(a(col, 230), width, Qt.SolidLine, Qt.FlatCap))
                p.drawArc(rect, int(start * 16), int(span * 16))
        rg = QRadialGradient(c, R * 0.45)
        rg.setColorAt(0, a(CYAN, 70))
        rg.setColorAt(1, a(CYAN, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(rg))
        p.drawEllipse(c, R * 0.45, R * 0.45)
        col = GREEN if self.fps >= 24 else CYAN if self.fps >= 15 else PINK
        p.setPen(col)
        p.setFont(mkfont(26, QFont.Bold, 0, True))
        p.drawText(QRectF(c.x() - 50, c.y() - 22, 100, 34), Qt.AlignCenter, f"{int(self.fps)}")
        p.setPen(MUTED)
        p.setFont(mkfont(10, QFont.Bold, 3))
        p.drawText(QRectF(c.x() - 50, c.y() + 10, 100, 16), Qt.AlignCenter, "FPS")

class Sparkline(QWidget):
    N = 90
    def __init__(self):
        super().__init__()
        self.setFixedHeight(84)
        self.v = deque(maxlen=self.N)

    def push(self, x):
        self.v.append(x)

    def advance(self, dt):
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(QPen(a(CYAN, 26), 1))
        for i in range(1, 4):
            p.drawLine(0, int(h * i / 4), w, int(h * i / 4))
        vals = list(self.v)
        if len(vals) < 2:
            return
        step = w / (self.N - 1)
        pts = [QPointF(w - (len(vals) - 1 - i) * step, h - 4 - min(v, 40) / 40 * (h - 8)) for i, v in enumerate(vals)]
        line = QPainterPath(pts[0])
        for pt in pts[1:]:
            line.lineTo(pt)
        area = QPainterPath(line)
        area.lineTo(pts[-1].x(), h)
        area.lineTo(pts[0].x(), h)
        area.closeSubpath()
        g = QLinearGradient(0, 0, 0, h)
        g.setColorAt(0, a(CYAN, 90))
        g.setColorAt(1, a(CYAN, 0))
        p.fillPath(area, QBrush(g))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(a(CYAN, 40), 6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(line)
        p.setPen(QPen(QColor(200, 250, 255), 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(line)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("white"))
        p.drawEllipse(pts[-1], 3, 3)

class FingerBar(QWidget):
    NAMES = "TIMRP"
    def __init__(self):
        super().__init__()
        self.setFixedHeight(76)
        self.st, self.name = [False] * 5, "—"

    def set(self, st, name):
        self.st, self.name = st, name
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        bw, gap, hh = 16, 8, 44
        for i in range(5):
            x = 4 + i * (bw + gap)
            r = QRectF(x, 4, bw, hh)
            on = self.st[i]
            if on:
                p.setPen(Qt.NoPen)
                p.setBrush(a(CYAN, 40))
                p.drawRoundedRect(r.adjusted(-3, -3, 3, 3), 5, 5)
                g = QLinearGradient(r.topLeft(), r.bottomLeft())
                g.setColorAt(0, CYAN)
                g.setColorAt(1, VIOLET)
                p.setBrush(QBrush(g))
                p.setPen(Qt.NoPen)
            else:
                p.setBrush(Qt.NoBrush)
                p.setPen(QPen(a(MUTED, 120), 1))
            p.drawRoundedRect(r, 3, 3)
            p.setPen(CYAN if on else MUTED)
            p.setFont(mkfont(10, QFont.Bold, 0, True))
            p.drawText(QRectF(x - 4, hh + 8, bw + 8, 16), Qt.AlignCenter, self.NAMES[i])
        p.setPen(GREEN if self.name != "—" else MUTED)
        p.setFont(mkfont(20, QFont.Bold, 2))
        p.drawText(QRectF(150, 0, self.width() - 150, self.height()), Qt.AlignVCenter | Qt.AlignRight, self.name)

class Console(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFont(mkfont(11, QFont.Normal, 0, True))
        self.setMaximumBlockCount(200)
        self.setStyleSheet("background: transparent; color: #7fe9ff; selection-background-color: #7c3aed;")
        self.setMinimumHeight(70)
        self.q, self.cur, self.i = [], "", 0
        t = QTimer(self)
        t.timeout.connect(self._step)
        t.start(20)

    def say(self, msg):
        self.q.append(f"[{time.strftime('%H:%M:%S')}] {msg}")

    def _step(self):
        if not self.cur:
            if not self.q: return
            self.cur, self.i = self.q.pop(0), 0
            self.moveCursor(QTextCursor.End)
            if self.document().characterCount() > 1:
                self.insertPlainText("\n")
        n = 2 + len(self.q) * 3
        self.moveCursor(QTextCursor.End)
        self.insertPlainText(self.cur[self.i:self.i + n])
        self.i += n
        if self.i >= len(self.cur): self.cur = ""
        self.ensureCursorVisible()