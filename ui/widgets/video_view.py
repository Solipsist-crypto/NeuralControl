import time
import math
import numpy as np
from collections import deque
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (QPainter, QPainterPath, QColor, QPen, QBrush, 
                           QLinearGradient, QImage, QFont, QPixmap)
from PySide6.QtWidgets import QWidget, QSizePolicy
from core.types import GESTURE_TRANSLATIONS

CYAN, VIOLET = QColor("#4da6ff"), QColor("#8b5cf6") # Трохи м'якші
GREEN, PINK = QColor("#4ade80"), QColor("#f472b6")
TEXT, MUTED = QColor("#e2e8f0"), QColor("#64748b")

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

CONN = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11), (11, 12),
        (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)]

def draw_hand(p, px):
    p.setBrush(Qt.NoBrush)
    p.setCompositionMode(QPainter.CompositionMode_Plus)
    for w, al in ((16, 16), (9, 42)):
        p.setPen(QPen(a(CYAN, al), w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        for i, j in CONN: p.drawLine(px[i], px[j])
    p.setCompositionMode(QPainter.CompositionMode_SourceOver)
    p.setPen(QPen(QColor(200, 250, 255), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    for i, j in CONN: p.drawLine(px[i], px[j])
    p.setPen(Qt.NoPen)
    for i, pt in enumerate(px):
        tip = i in (4, 8, 12, 16, 20)
        p.setBrush(a(VIOLET, 120))
        p.drawEllipse(pt, 8 if tip else 5, 8 if tip else 5)
        p.setBrush(QColor("white"))
        p.drawEllipse(pt, 3 if tip else 2, 3 if tip else 2)

def draw_reticle(p, c, rad, ph, hold_progress=0.0):
    p.setBrush(Qt.NoBrush)
    r1 = QRectF(c.x() - rad, c.y() - rad, 2 * rad, 2 * rad)
    p.setPen(QPen(a(CYAN, 210), 2))
    for k in range(3): p.drawArc(r1, int((ph * 90 + k * 120) * 16), 60 * 16)
    r2 = r1.adjusted(12, 12, -12, -12)
    p.setPen(QPen(a(VIOLET, 230), 1.5))
    for k in range(4): p.drawArc(r2, int((-ph * 140 + k * 90) * 16), 30 * 16)
    p.setPen(QPen(a(CYAN, 150), 1))
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        p.drawLine(QPointF(c.x() + dx * (rad + 4), c.y() + dy * (rad + 4)),
                   QPointF(c.x() + dx * (rad + 12), c.y() + dy * (rad + 12)))
    if hold_progress > 0:
        hold_ring = r1.adjusted(-8, -8, 8, 8)
        p.setPen(QPen(a(CYAN, 70), 4))
        p.drawEllipse(hold_ring)
        p.setPen(QPen(a(CYAN, 240), 4, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(hold_ring, 90 * 16, -int(360 * hold_progress * 16))

class VideoView(QWidget):
    BG = QColor("#070a14")

    def __init__(self):
        super().__init__()
        self.setMinimumSize(480, 360)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._frame = None
        self._qimg = None
        self._aspect = 4 / 3
        self.hands, self.fps = [], 0.0
        self.hold_progress = 0.0
        self.trails = {}
        self.phase = 0.0
        self.holo, self.skeleton, self.scan = False, True, True
        
        self.scan_tile = QPixmap(2, 4)
        self.scan_tile.fill(Qt.transparent)
        q = QPainter(self.scan_tile)
        q.fillRect(0, 0, 2, 1, QColor(0, 0, 0, 55))
        q.end()

    def set_frame(self, bgr, tracked_hands, fps, predictions=None, hold_progress=0.0):
        h, w = bgr.shape[:2]
        self._frame = bgr
        self._qimg = QImage(bgr.data, w, h, 3 * w, QImage.Format_BGR888).copy()
        self._aspect = w / h
        self.fps = fps
        
        self.hands = []
        for slot, pts in tracked_hands.items():
            pts_np = np.array(pts)
            prediction, confidence = (
                predictions.get(slot, (None, None)) if predictions else (None, None)
            )
            label = (
                GESTURE_TRANSLATIONS.get(prediction, prediction)
                if prediction else "МОДЕЛЬ НЕ ЗАВАНТАЖЕНО"
            )
            if confidence is not None:
                label += f" ({confidence:.0%})"
            self.hands.append((slot, pts_np, label, confidence))

        self.hold_progress = max(0.0, min(1.0, float(hold_progress)))
        seen = set()
        for slot, pts, _, _ in self.hands:
            self.trails.setdefault(slot, deque(maxlen=20)).append((float(pts[8][0]), float(pts[8][1])))
            seen.add(slot)
        for s in self.trails:
            if s not in seen: self.trails[s].clear()
        self.update()

    def advance(self, dt):
        self.phase += dt
        self.update()

    def video_rect(self):
        W, H = self.width(), self.height()
        w = min(W, H * self._aspect)
        h = w / self._aspect
        return QRectF((W - w) / 2, (H - h) / 2, w, h)

    @staticmethod
    def to_px(x, y, r):
        return QPointF(r.x() + x * r.width(), r.y() + y * r.height())

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        r = self.video_rect()
        p.fillRect(r, self.BG)
        p.save()
        p.setClipRect(r)
        
        if self._qimg is not None and not self.holo:
            p.drawImage(r, self._qimg)
            p.fillRect(r, QColor(0, 24, 48, 60))
        elif self.holo:
            self._draw_holo_grid(p, r)
        elif self._qimg is None:
            p.setPen(a(PINK, 200))
            p.setFont(mkfont(18, QFont.Bold, 4))
            p.drawText(r, Qt.AlignCenter, "NO SIGNAL")
            
        if self.skeleton:
            for slot, pts, name, _ in self.hands:
                px = [self.to_px(x, y, r) for x, y in pts]
                self._draw_trail(p, slot, r)
                draw_hand(p, px)
                self._draw_hand_hud(p, r, slot, name, pts, px, self.hold_progress)
                
        if self.scan:
            p.drawTiledPixmap(r.toRect(), self.scan_tile)
            y = r.top() + ((self.phase * 0.25) % 1.0) * r.height()
            g = QLinearGradient(0, y - 40, 0, y)
            g.setColorAt(0, a(CYAN, 0))
            g.setColorAt(1, a(CYAN, 38))
            p.fillRect(QRectF(r.left(), y - 40, r.width(), 40), QBrush(g))
            p.fillRect(QRectF(r.left(), y, r.width(), 1.5), a(CYAN, 110))
        p.restore()
        
        self._draw_frame(p, r)

    def _draw_holo_grid(self, p, r):
        g = QLinearGradient(r.topLeft(), r.bottomLeft())
        g.setColorAt(0, QColor("#060a18"))
        g.setColorAt(1, QColor("#0a1430"))
        p.fillRect(r, QBrush(g))
        p.setPen(QPen(a(CYAN, 28), 1))
        step = 40
        off = (self.phase * 20) % step
        x = r.left()
        while x <= r.right():
            p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
            x += step
        y = r.top() + off
        while y <= r.bottom():
            p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
            y += step

    def _draw_trail(self, p, slot, r):
        tr = list(self.trails.get(slot, []))
        n = len(tr)
        for i in range(1, n):
            k = i / n
            p.setPen(QPen(a(PINK, 230 * k), 1 + 5 * k, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(self.to_px(*tr[i - 1], r), self.to_px(*tr[i], r))

    def _draw_hand_hud(self, p, r, slot, name, pts, px, hold_progress):
        palm = np.mean(pts[[0, 5, 9, 13, 17]], axis=0)
        c = self.to_px(float(palm[0]), float(palm[1]), r)
        xs, ys = [q.x() for q in px], [q.y() for q in px]
        rad = max(max(xs) - min(xs), max(ys) - min(ys)) * 0.62
        draw_reticle(p, c, rad, self.phase, hold_progress)
        x = min(r.right() - 150, max(xs) + 18)
        y = max(r.top() + 56, min(ys))
        p.setPen(QPen(a(CYAN, 150), 1))
        p.drawLine(QPointF(max(xs), min(ys)), QPointF(x - 4, y + 6))
        p.drawLine(QPointF(x - 4, y + 6), QPointF(x + 140, y + 6))
        p.setPen(CYAN)
        p.setFont(mkfont(12, QFont.Bold, 1, True))
        p.drawText(QPointF(x, y), f"H{slot} // {name}")
        p.setPen(MUTED)
        p.setFont(mkfont(10, QFont.Normal, 0, True))
        p.drawText(QPointF(x, y + 20), f"X {palm[0]:.2f}  Y {palm[1]:.2f}")

    def _draw_frame(self, p, r, L=30, m=8):
        w = r.width()
        h = r.height()
        x1, y1, x2, y2 = r.left() + m, r.top() + m, r.right() - m, r.bottom() - m
        corners = ((x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1))
        for ww, al in ((7, 36), (2, 230)):
            p.setPen(QPen(a(CYAN, al), ww, Qt.SolidLine, Qt.SquareCap))
            for cx, cy, dx, dy in corners:
                p.drawLine(QPointF(cx, cy), QPointF(cx + dx * L, cy))
                p.drawLine(QPointF(cx, cy), QPointF(cx, cy + dy * L))
        
        p.setPen(QPen(a(CYAN, 90), 1))
        x = x1 + L + 10
        i = 0
        while x < x2 - L - 10:
            p.drawLine(QPointF(x, y1), QPointF(x, y1 + (9 if i % 5 == 0 else 4)))
            x += 14
            i += 1
        
        n = len(self.hands)
        p.setFont(mkfont(12, QFont.Normal, 1.2, True))
        p.setPen(a(CYAN, 230))
        p.drawText(QPointF(x1 + 8, y1 + 30), f"TRACKING // FPS {int(self.fps):02d} // HANDS {n}")
        blink = int(self.phase * 1.6) % 2 == 0
        p.setPen(a(PINK, 255 if blink else 60))
        p.drawText(QPointF(x2 - 64, y1 + 30), "● REC")
        p.setFont(mkfont(10, QFont.Normal, 1, True))
        p.setPen(a(MUTED, 230))
        p.drawText(QPointF(x1 + 8, y2 - 8), time.strftime("%Y-%m-%d  %H:%M:%S"))
        p.drawText(QRectF(x2 - 200, y2 - 22, 192, 16), Qt.AlignRight, "640x480 // MJPG // MEDIAPIPE")
        if n == 0 and self._qimg is not None:
            al = 110 + 110 * (0.5 + 0.5 * math.sin(self.phase * 3))
            p.setPen(a(CYAN, al))
            p.setFont(mkfont(13, QFont.Bold, 4))
            p.drawText(QRectF(r.left(), y2 - 60, r.width(), 22), Qt.AlignCenter, "AWAITING HAND INPUT")