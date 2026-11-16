import numpy as np

from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel
from PySide6.QtGui import QPainter, QColor, QPen, QLinearGradient, QBrush, QPainterPath, QFont

from ui.widgets.video_view import VideoView
from ui.widgets.glow_button import GlowButton, ArcReactor, Sparkline, Console
from services.camera_service import CameraThread
from services.gesture_engine import GestureEngine
from services.rule_engine import RuleEngine, RuleValidationError
from services.action_runner import (
    ActionCancelledError,
    ActionExecutionError,
    ActionRunner,
)
from services.action_catalog import WAIT_ACTION
from core.types import GESTURE_TRANSLATIONS

# Нові кольори
CYAN, VIOLET = QColor("#4da6ff"), QColor("#8b5cf6")

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
        self.b_gest = GlowButton("🧠 НЕЙРОМЕРЕЖА", VIOLET, True)
        self.b_skel.setChecked(True)
        self.b_scan.setChecked(True)
        self.b_gest.setChecked(True)
        buttons = (
            self.b_holo,
            self.b_skel,
            self.b_scan,
            self.b_gest,
        )
        for i, b in enumerate(buttons):
            grid.addWidget(b, i // 2, i % 2)
        pc.lay.addLayout(grid)
        col.addWidget(pc)

        self._prev_n = 0
        self._set_status("ОЧІКУВАННЯ", 0)

        self.animated = [self.video, self.reactor, self.spark]
        self.anim = QTimer(self)
        self.anim.timeout.connect(lambda: [w.advance(0.033) for w in self.animated])
        self.anim.start(33)

        for m in (
            "ІНІЦІАЛІЗАЦІЯ НЕЙРОЯДРА...",
            "ЗВ'ЯЗОК З КАМЕРОЮ: 640x480 MJPG",
            "ВСІ СИСТЕМИ В НОРМІ",
        ):
            self.console.say(m)

        self.engine = GestureEngine()
        self.engine.processed_frame.connect(self.on_frame_processed)
        self.engine.state_changed.connect(self._on_engine_state_changed)
        self.engine.gesture_detected.connect(self._on_gesture_detected)
        self.engine.error_occurred.connect(
            lambda message: self.console.say(message)
        )
        self.rule_engine = RuleEngine()
        self.action_runner = ActionRunner(self, self.reload_rules)
        self._pending_actions = []
        self._sequence_running = False
        self._skip_rules_once = False
        self.action_timer = QTimer(self)
        self.action_timer.setSingleShot(True)
        self.action_timer.timeout.connect(self._run_next_action)
        self.engine.set_enabled(self.b_gest.isChecked())
        self._log_neural_status()

        self.b_holo.toggled.connect(
            lambda x: (
                setattr(self.video, "holo", x),
                self.console.say(f"ГОЛОГРАМА: {'УВІМК' if x else 'ВИКЛ'}"),
            )
        )
        self.b_skel.toggled.connect(lambda x: setattr(self.video, "skeleton", x))
        self.b_scan.toggled.connect(lambda x: setattr(self.video, "scan", x))
        self.b_gest.toggled.connect(self._gestures_toggled)
        self._mouse_position = None
        self._mouse_pinches = {"middle": False, "ring": False}
        self._pyautogui = None
        self._mouse_error_logged = False
        
        self.camera = CameraThread(camera_index=0)
        self.camera.frame_ready.connect(self.engine.process_frame)
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
        self.engine.set_enabled(on)
        if not on:
            self._mouse_position = None
            self._mouse_pinches = {"middle": False, "ring": False}
            self._release_mouse_button()
            self.rule_engine.reset()
            self.action_timer.stop()
            self._pending_actions.clear()
            self._sequence_running = False
        self._set_status(self._state_label(), self._prev_n)

    def reload_neural_model(self):
        self.engine.reload_model()
        self._log_neural_status()

    def _log_neural_status(self):
        neural_pose = self.engine.neural_pose
        if neural_pose.registry_error:
            self.console.say(f"ПОМИЛКА РЕЄСТРУ ЖЕСТІВ: {neural_pose.registry_error}")
        if not neural_pose.enabled:
            self.console.say("НЕЙРОМЕРЕЖА ВИМКНЕНА")
        elif neural_pose.model is not None:
            self.console.say(
                f"МОДЕЛЬ ЗАВАНТАЖЕНО: {neural_pose.model_path} "
                f"({neural_pose.feature_count} ознак)"
            )
        else:
            self.console.say(f"ПОМИЛКА МОДЕЛІ: {neural_pose.load_error}")

    def on_frame_processed(self, frame, tracked_hands, predictions):
        self.frame_count += 1
        main_win = self.window()

        if self.engine.state.value == "MOUSE":
            self._update_mouse_controls(tracked_hands)
            self.rule_engine.reset()
        elif self._mouse_position is not None:
            self._mouse_position = None
            self._mouse_pinches = {"middle": False, "ring": False}

        if hasattr(main_win, 'tab_training'):
            training_active = (
                getattr(main_win, "tabs", None) is not None
                and main_win.tabs.currentWidget() is main_win.tab_training
            )
            if training_active:
                if tracked_hands:
                    features = self.engine.neural_pose.features_from_hands(
                        tracked_hands
                    )
                    main_win.tab_training.set_current_features(features)
                else:
                    main_win.tab_training.current_features = None
                main_win.tab_training.update_preview(
                    frame, tracked_hands, predictions, self.reactor.fps
                )
            else:
                main_win.tab_training.current_features = None

        if (
            getattr(main_win, 'tab_drawing', None) is not None
            and getattr(main_win, 'tabs', None) is not None
            and main_win.tabs.currentWidget() is main_win.tab_drawing
        ):
            main_win.tab_drawing.set_frame(frame, tracked_hands)

        n = len(tracked_hands)
        if self._skip_rules_once:
            self._skip_rules_once = False
            self.rule_engine.reset()
        elif self.engine.state.value != "MOUSE":
            triggered_rules = self.rule_engine.update(predictions)
            self.engine.hold_progress = self.rule_engine.hold_progress
            for rule in triggered_rules:
                self._enqueue_rule(rule)
        if n != self._prev_n:
            self.console.say("ЦІЛЬ ЗНАЙДЕНО" if n > self._prev_n else "ЦІЛЬ ВТРАЧЕНО")
            self._set_status(self._state_label(), n)
            self._prev_n = n
        self.video.set_frame(
            frame,
            tracked_hands,
            self.reactor.fps,
            predictions,
            self.engine.hold_progress,
        )

    def _state_label(self):
        if not self.engine.enabled or self.engine.state.value == "SLEEP":
            return "ОЧІКУВАННЯ"
        if self.engine.state.value == "MOUSE":
            return "МИШКА"
        if self.engine.neural_pose.model is None:
            return "МОДЕЛЬ НЕ ГОТОВА"
        return "НЕЙРОМЕРЕЖА"

    def _on_engine_state_changed(self, state):
        state_labels = {
            "SLEEP": "ОЧІКУВАННЯ",
            "ARMED": "НЕЙРОМЕРЕЖА",
            "MOUSE": "МИШКА",
        }
        self.console.say(f"СТАН: {state_labels.get(state, state)}")
        self._set_status(self._state_label(), self._prev_n)

    def _on_gesture_detected(self, source, pose, hand):
        translated_pose = GESTURE_TRANSLATIONS.get(pose, pose)
        self.console.say(f"{source}: {translated_pose} ({hand})")

        if self.engine.state.value == "MOUSE":
            if pose in self.engine.mouse_exit_gestures:
                self.engine.set_mouse_mode(False)
                self.console.say("РЕЖИМ МИШКИ: ВИМКНЕНО")
                self._mouse_position = None
                self._mouse_pinches = {"middle": False, "ring": False}
                self._release_mouse_button()
                self._skip_rules_once = True
            return

    def reload_rules(self):
        try:
            self.rule_engine.reload()
        except (OSError, RuleValidationError) as error:
            self.console.say(f"ПОМИЛКА ЗАВАНТАЖЕННЯ ПРАВИЛ: {error}")
            return
        self.console.say(f"ПРАВИЛА ЗАВАНТАЖЕНО: {len(self.rule_engine.rules)}")

    def _enqueue_rule(self, rule):
        self.console.say(
            f"ПРАВИЛО АКТИВОВАНО: {rule['name'] or rule['id']}"
        )
        self._pending_actions.extend(
            (rule, step) for step in rule["actions"]
        )
        if not self._sequence_running:
            self._sequence_running = True
            self.action_timer.start(0)

    def _run_next_action(self):
        if not self._pending_actions:
            self._sequence_running = False
            return
        rule, step = self._pending_actions.pop(0)
        action = step["action"]
        params = step.get("params", {})

        if action == WAIT_ACTION:
            try:
                delay_ms = max(0, round(float(params["seconds"]) * 1000))
            except (KeyError, TypeError, ValueError) as error:
                self.console.say(f"ПОМИЛКА ПАРАМЕТРІВ ЗАТРИМКИ: {error}")
                self.action_timer.start(0)
                return
            self.action_timer.start(delay_ms)
            return

        if action == "Режим Мишки":
            triggers = rule["triggers"]
            exit_gestures = tuple(dict.fromkeys(t["pose"] for t in triggers))
            first_trigger = triggers[0]
            self._release_mouse_button()
            self.engine.set_mouse_mode(
                True,
                exit_gestures=exit_gestures,
                entry_pose=first_trigger["pose"],
                entry_hand=(
                    first_trigger["hand"]
                    if first_trigger["hand"] in {"LEFT", "RIGHT", "BOTH"}
                    else None
                ),
            )
            self._pending_actions.clear()
            self._sequence_running = False
            self.console.say("РЕЖИМ МИШКИ: УВІМКНЕНО")
            return

        try:
            self.action_runner.execute(action, params)
        except ActionCancelledError:
            self.console.say(f"ДІЮ СКАСОВАНО: {action}")
        except ActionExecutionError as error:
            self.console.say(f"ПОМИЛКА ДІЇ: {error}")
        else:
            self.console.say(f"ДІЮ ВИКОНАНО: {action}")
        self.action_timer.start(0)

    def _get_pyautogui(self):
        try:
            return ActionRunner._get_pyautogui()
        except ActionExecutionError as error:
            if not self._mouse_error_logged:
                self.console.say(f"ПОМИЛКА: {error}")
                self._mouse_error_logged = True
            return None

    def _release_mouse_button(self):
        try:
            self.action_runner.release_mouse_button()
        except ActionExecutionError as error:
            self.console.say(f"ПОМИЛКА МИШІ: {error}")

    def _update_mouse_controls(self, tracked_hands):
        if not tracked_hands:
            self._mouse_position = None
            self._mouse_pinches = {"middle": False, "ring": False}
            return

        side = "RIGHT" if "RIGHT" in tracked_hands else next(iter(tracked_hands))
        points = np.asarray(tracked_hands[side], dtype=np.float32)
        if points.shape[0] != 21 or points.shape[1] < 2:
            return

        pyautogui = self._get_pyautogui()
        if pyautogui is None:
            return
        try:
            screen_width, screen_height = pyautogui.size()
            target_x = int(np.clip(points[8, 0], 0.0, 1.0) * (screen_width - 1))
            target_y = int(np.clip(points[8, 1], 0.0, 1.0) * (screen_height - 1))
            if self._mouse_position is None:
                self._mouse_position = (target_x, target_y)
            else:
                previous_x, previous_y = self._mouse_position
                self._mouse_position = (
                    int(previous_x * 0.65 + target_x * 0.35),
                    int(previous_y * 0.65 + target_y * 0.35),
                )
            pyautogui.moveTo(*self._mouse_position, duration=0, _pause=False)

            palm_width = float(np.linalg.norm(points[5, :2] - points[17, :2]))
            if palm_width <= 1e-4:
                return
            middle_pressed = (
                np.linalg.norm(points[4, :2] - points[12, :2])
                <= palm_width * 0.32
            )
            ring_pressed = (
                np.linalg.norm(points[4, :2] - points[16, :2])
                <= palm_width * 0.32
            )
            if middle_pressed and not self._mouse_pinches["middle"]:
                pyautogui.click(button="left", _pause=False)
            elif ring_pressed and not self._mouse_pinches["ring"]:
                pyautogui.click(button="right", _pause=False)
            self._mouse_pinches["middle"] = bool(middle_pressed)
            self._mouse_pinches["ring"] = bool(ring_pressed)
        except (OSError, pyautogui.FailSafeException) as error:
            if not self._mouse_error_logged:
                self.console.say(f"ПОМИЛКА КЕРУВАННЯ МИШКОЮ: {error}")
                self._mouse_error_logged = True

    def stop(self):
        self.camera.stop()
        self._release_mouse_button()
        self.engine.stop()