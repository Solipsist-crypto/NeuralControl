import time
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtWidgets import QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizeGrip
from PySide6.QtGui import QPainter, QColor, QPen, QLinearGradient, QBrush, QPainterPath, QRadialGradient, QPixmap, QFont

from ui.tabs.control_tab import ControlTab
from ui.widgets.glow_button import mkfont

CYAN, VIOLET = QColor("#4da6ff"), QColor("#8b5cf6")
MUTED = QColor("#64748b")

def a(color, alpha):
    c = QColor(color)
    c.setAlpha(max(0, min(255, int(alpha))))
    return c

class HudRoot(QWidget):
    def __init__(self):
        super().__init__()
        self.tile = QPixmap(28, 28)
        self.tile.fill(Qt.transparent)
        q = QPainter(self.tile)
        q.setRenderHint(QPainter.Antialiasing)
        q.setPen(Qt.NoPen)
        q.setBrush(a(CYAN, 20))
        q.drawEllipse(QPointF(14, 14), 1, 1)
        q.end()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, 14, 14)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, QColor("#0a0e1a"))
        g.setColorAt(1, QColor("#0d1226"))
        p.fillPath(path, QBrush(g))
        
        p.save()
        p.setClipPath(path)
        p.drawTiledPixmap(self.rect(), self.tile)
        for pos, col, rad in ((r.topRight(), VIOLET, 520), (r.bottomLeft(), CYAN, 420)):
            rg = QRadialGradient(pos, rad)
            rg.setColorAt(0, a(col, 20))
            rg.setColorAt(1, a(col, 0))
            p.fillRect(self.rect(), QBrush(rg))
        vg = QRadialGradient(r.center(), max(r.width(), r.height()) * 0.75)
        vg.setColorAt(0.55, QColor(0, 0, 0, 0))
        vg.setColorAt(1, QColor(0, 0, 0, 150))
        p.fillRect(self.rect(), QBrush(vg))
        p.restore()
        
        p.setPen(QPen(a(CYAN, 60), 1))
        p.drawPath(path)

class TitleBar(QWidget):
    def __init__(self, win):
        super().__init__(win)
        self.setFixedHeight(44)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 0, 10, 0)
        logo = QLabel("◈")
        logo.setStyleSheet("color:#4da6ff; font-size:18px;")
        title = QLabel("NEURAL // CONTROL")
        title.setObjectName("AppTitle")
        title.setFont(mkfont(13, QFont.Bold, 3))
        self.clock = QLabel()
        self.clock.setObjectName("Clock")
        self.clock.setFont(mkfont(11, QFont.Normal, 1, True))
        lay.addWidget(logo)
        lay.addWidget(title)
        lay.addStretch()
        lay.addWidget(self.clock)
        lay.addSpacing(14)
        for txt, slot in (("—", win.showMinimized), ("▢", self._max), ("✕", win.close)):
            b = QPushButton(txt)
            b.setObjectName("WinBtn")
            b.setFixedSize(38, 28)
            b.clicked.connect(slot)
            if txt == "✕":
                b.setProperty("danger", True)
            lay.addWidget(b)
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(1000)
        self._tick()

    def _tick(self):
        self.clock.setText(time.strftime("%H:%M:%S"))

    def _max(self):
        w = self.window()
        w.showNormal() if w.isMaximized() else w.showMaximized()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.window().windowHandle():
            self.window().windowHandle().startSystemMove()

    def mouseDoubleClickEvent(self, e):
        self._max()

    def paintEvent(self, _):
        p = QPainter(self)
        g = QLinearGradient(0, 0, self.width(), 0)
        g.setColorAt(0, a(CYAN, 0))
        g.setColorAt(0.2, a(CYAN, 100))
        g.setColorAt(0.8, a(VIOLET, 100))
        g.setColorAt(1, a(VIOLET, 0))
        p.fillRect(QRectF(0, self.height() - 1, self.width(), 1), QBrush(g))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(1000, 650)
        self.resize(1200, 750) # ЗМЕНШЕНО РОЗМІР

        root = HudRoot()
        self.setCentralWidget(root)
        v = QVBoxLayout(root)
        v.setContentsMargins(1, 1, 1, 1)
        v.setSpacing(0)
        
        v.addWidget(TitleBar(self))
        
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tab_control = ControlTab()
        self.tabs.addTab(self.tab_control, "УПРАВЛІННЯ")
        v.addWidget(self.tabs)

        self.grip = QSizeGrip(root)
        self.grip.setFixedSize(16, 16)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.grip.move(self.width() - 22, self.height() - 22)

    def closeEvent(self, e):
        if hasattr(self, 'tab_control'):
            self.tab_control.stop()
        super().closeEvent(e)