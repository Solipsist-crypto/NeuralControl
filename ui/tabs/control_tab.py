from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame
from PySide6.QtGui import QPainter, QColor, QPen, QLinearGradient, QBrush, QPainterPath, QFont

from ui.widgets.video_view import VideoView
from ui.widgets.glow_button import GlowButton, ArcReactor, Sparkline, Console
from services.camera_service import CameraThread
from services.gesture_controller import GestureController

# Нові кольори
CYAN, VIOLET = QColor("#4da6ff"), QColor("#8b5cf6")
GREEN = QColor("#4ade80")

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

class HudPanel(QWidget):
    def __init__(self, title):
        super().__init__()
        self.title = title
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(14, 38, 14, 12)
        self.lay.setSpacing(8)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        c = 12.0
        path = QPainterPath()
        path.moveTo(r.left() + c, r.top())
        path.lineTo(r.right(), r.top())
        path.lineTo(r.right(), r.bottom() - c)
        path.lineTo(r.right() - c, r.bottom())
        path.lineTo(r.left(), r.bottom())
        path.lineTo(r.left(), r.top() + c)
        path.closeSubpath()
        
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, QColor(255, 255, 255, 15)) # Менш яскраве скло
        g.setColorAt(1, a(CYAN, 5))
        p.fillPath(path, QBrush(g))
        
        bg = QLinearGradient(r.topLeft(), r.bottomRight())
        bg.setColorAt(0, a(CYAN, 100))
        bg.setColorAt(1, a(VIOLET, 60))
        p.setPen(QPen(QBrush(bg), 1))
        p.drawPath(path)
        
        p.setPen(Qt.NoPen)
        p.setBrush(CYAN)
        p.drawRect(QRectF(12, 13, 3, 14))
        p.setFont(mkfont(11, QFont.Bold, 2.5))
        p.setPen(CYAN)
        p.drawText(QPointF(22, 25), self.title)
        p.setPen(QPen(a(CYAN, 40), 1))
        p.drawLine(QPointF(12, 33), QPointF(r.right() - 12, 33))
        p.setPen(QPen(a(CYAN, 220), 2))
        p.drawLine(QPointF(r.right() - 26, r.bottom()), QPointF(r.right() - 12, r.bottom()))

class ControlTab(QWidget):
    def __init__(self):
        super().__init__()
        body = QHBoxLayout(self)
        body.setContentsMargins(14, 12, 14, 16)
        body.setSpacing(14)

        self.video = VideoView()
        body.addWidget(self.video, 1)

        col = QVBoxLayout()
        col.setSpacing(10)
        right = QWidget()
        right.setFixedWidth(320) # Трохи вужче
        right.setLayout(col)
        body.addWidget(right)

        # SYSTEM
        pn = HudPanel("СИСТЕМА")
        self.reactor = ArcReactor()
        pn.lay.addWidget(self.reactor)
        self.l_mode, self.l_hands = QLabel(), QLabel()
        for lb in (self.l_mode, self.l_hands):
            lb.setFont(mkfont(12, QFont.Normal, 1, True))
            pn.lay.addWidget(lb)
        col.addWidget(pn)

        # GESTURE - ВИДАЛЕНО

        # FPS TRACE
        pf = HudPanel("ГРАФІК FPS")
        self.spark = Sparkline()
        pf.lay.addWidget(self.spark)
        col.addWidget(pf)

        # LOG
        pl = HudPanel("ЖУРНАЛ ПОДІЙ")
        self.console = Console()
        pl.lay.addWidget(self.console)
        col.addWidget(pl, 1)

        # CONTROL
        pc = HudPanel("КЕРУВАННЯ")
        grid = QGridLayout()
        grid.setSpacing(4)
        self.b_holo = GlowButton("ГОЛОГРАМА", CYAN, True)
        self.b_skel = GlowButton("СКЕЛЕТ", CYAN, True)
        self.b_scan = GlowButton("СКАНЛАЙНИ", VIOLET, True)
        self.b_gest = GlowButton("ЖЕСТИ", GREEN, True)
        self.b_skel.setChecked(True)
        self.b_scan.setChecked(True)
        for i, b in enumerate((self.b_holo, self.b_skel, self.b_scan, self.b_gest)):
            grid.addWidget(b, i // 2, i % 2)
        pc.lay.addLayout(grid)
        col.addWidget(pc)

        self.b_holo.toggled.connect(lambda x: (setattr(self.video, "holo", x), self.console.say(f"ГОЛОГРАМА: {'УВІМК' if x else 'ВИКЛ'}")))
        self.b_skel.toggled.connect(lambda x: setattr(self.video, "skeleton", x))
        self.b_scan.toggled.connect(lambda x: setattr(self.video, "scan", x))
        self.b_gest.toggled.connect(self._gestures_toggled)

        self._prev_n, self._prev_gesture = 0, None
        self._set_status("ОЧІКУВАННЯ", 0)

        self.animated = [self.video, self.reactor, self.spark]
        self.anim = QTimer(self)
        self.anim.timeout.connect(lambda: [w.advance(0.033) for w in self.animated])
        self.anim.start(33)

        for m in ("ІНІЦІАЛІЗАЦІЯ НЕЙРОЯДРА...", "ЗАВАНТАЖЕННЯ МОДЕЛІ РУК... УСПІШНО", "ЗВ'ЯЗОК З КАМЕРОЮ: 640x480 MJPG", "ВСІ СИСТЕМИ В НОРМІ"):
            self.console.say(m)

        self.controller = GestureController()
        self.controller.processed_frame.connect(self.on_frame_processed)
        
        self.camera = CameraThread(camera_index=0)
        self.camera.frame_ready.connect(self.controller.process_frame)
        self.camera.start()

        self.frame_count = 0
        self.fps_timer = QTimer(self)
        self.fps_timer.timeout.connect(self.calc_fps)
        self.fps_timer.start(1000)

    def calc_fps(self):
        self.reactor.fps = self.frame_count
        self.spark.push(self.frame_count)
        self.frame_count = 0

    def _set_status(self, mode, n):
        col = "#4ade80" if n else "#64748b"
        self.l_mode.setText(f"<span style='color:#64748b'>РЕЖИМ: </span><span style='color:#4da6ff'>{mode}</span>")
        self.l_hands.setText(f"<span style='color:#64748b'>РУК: </span><span style='color:{col}'>{n}</span>")

    def _gestures_toggled(self, on):
        self.console.say(f"КЕРУВАННЯ ЖЕСТАМИ: {'АКТИВНО' if on else 'ВИМКНЕНО'}")
        self._set_status("КЕРУВАННЯ" if on else ("ТРЕКІНГ" if self._prev_n else "ОЧІКУВАННЯ"), self._prev_n)

    def on_frame_processed(self, frame, tracked_hands):
        self.frame_count += 1
        self.video.set_frame(frame, tracked_hands, self.reactor.fps)
        
        n = len(tracked_hands)
        if n != self._prev_n:
            self.console.say("ЦІЛЬ ЗНАЙДЕНО" if n > self._prev_n else "ЦІЛЬ ВТРАЧЕНО")
            mode = "КЕРУВАННЯ" if self.b_gest.isChecked() else ("ТРЕКІНГ" if n else "ОЧІКУВАННЯ")
            self._set_status(mode, n)
            self._prev_n = n
            
        # (Тут ми більше не малюємо GESTURE, але логи жестів залишаємо)
        if self.video.hands:
            _, _, name, st = self.video.hands[0]
            if name != self._prev_gesture and self.b_gest.isChecked():
                self.console.say(f"ЖЕСТ: {name}")
            self._prev_gesture = name
        else:
            self._prev_gesture = None

    def stop(self):
        self.camera.stop()
        self.controller.stop()