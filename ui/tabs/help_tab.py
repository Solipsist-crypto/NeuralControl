import json

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.types import GESTURE_TRANSLATIONS, GESTURES_JSON


class HelpTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("HelpTab")
        self.setStyleSheet("QWidget#HelpTab { background-color: #0a0e1a; }")
        self._gestures = []
        self._load_error = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(12)

        toolbar = QFrame()
        toolbar.setObjectName("SidePanel")
        tools = QHBoxLayout(toolbar)
        tools.setContentsMargins(12, 8, 12, 8)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Пошук за назвою або описом жесту…")
        self.search_edit.textChanged.connect(self._render_cards)
        tools.addWidget(self.search_edit, 1)

        tools.addWidget(QLabel("РУКА"))
        self.hand_filter = QComboBox()
        self.hand_filter.addItem("Всі", "")
        self.hand_filter.addItem("Ліва", "left")
        self.hand_filter.addItem("Права", "right")
        self.hand_filter.currentIndexChanged.connect(self._render_cards)
        tools.addWidget(self.hand_filter)
        layout.addWidget(toolbar)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setLineWidth(0)
        self.scroll_area.setFocusPolicy(Qt.NoFocus)
        self.scroll_area.setAutoFillBackground(False)
        self.scroll_area.setStyleSheet("border: none; background: transparent;")
        self.scroll_area.viewport().setFocusPolicy(Qt.NoFocus)
        self.scroll_area.viewport().setAutoFillBackground(False)
        self.scroll_area.viewport().setStyleSheet(
            "border: none; background: transparent;"
        )
        self.content = QWidget()
        self.content.setAttribute(Qt.WA_TranslucentBackground)
        self.content.setFocusPolicy(Qt.NoFocus)
        self.content.setAutoFillBackground(False)
        self.content.setStyleSheet("border: none; background: transparent;")
        self.cards_layout = QGridLayout(self.content)
        self.cards_layout.setContentsMargins(4, 4, 12, 4)
        self.cards_layout.setHorizontalSpacing(12)
        self.cards_layout.setVerticalSpacing(12)
        self.cards_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.content)
        layout.addWidget(self.scroll_area, 1)

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(80)
        self._resize_timer.timeout.connect(self._render_cards)

        self._load_gestures()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_resize_timer"):
            self._resize_timer.start()

    def _load_gestures(self):
        try:
            data = json.loads(GESTURES_JSON.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            self._load_error = f"Не вдалося завантажити довідку:\n{error}"
            self._render_cards()
            return

        gestures = data.get("gestures") if isinstance(data, dict) else None
        if not isinstance(gestures, list):
            self._load_error = "Файл gestures.json має некоректний формат."
            self._render_cards()
            return

        self._gestures = [gesture for gesture in gestures if isinstance(gesture, dict)]
        self._render_cards()

    def _render_cards(self, *_):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if self._load_error:
            self._add_message(self._load_error)
            return

        query = self.search_edit.text().strip().casefold()
        hand = self.hand_filter.currentData()
        matching = []
        for gesture in self._gestures:
            gesture_hand = gesture.get("hand", "")
            if hand and gesture_hand not in (hand, "both"):
                continue
            searchable = " ".join(
                (
                    self._gesture_name(gesture),
                    str(gesture.get("id", "")),
                    str(gesture.get("name", "")),
                    str(gesture.get("description", "")),
                    str(gesture.get("emoji", "")),
                )
            ).casefold()
            if query and query not in searchable:
                continue
            matching.append(gesture)

        if not matching:
            self._add_message("За цими умовами жестів не знайдено.")
            return

        columns = 3 if self.scroll_area.viewport().width() >= 1050 else 2
        for column in range(3):
            self.cards_layout.setColumnStretch(column, 0)
        for column in range(columns):
            self.cards_layout.setColumnStretch(column, 1)
        for index, gesture in enumerate(matching):
            self.cards_layout.addWidget(
                self._create_gesture_card(gesture),
                index // columns,
                index % columns,
            )

    def _create_gesture_card(self, gesture):
        card = QFrame()
        card.setObjectName("GestureHelpCard")
        card.setStyleSheet(
            "QFrame#GestureHelpCard { background-color: rgba(10,14,26,225); "
            "border: 1px solid rgba(77,166,255,90); "
            "border-left: 3px solid #4da6ff; border-radius: 10px; }"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        emoji = QLabel(str(gesture.get("emoji", "🖐️")))
        emoji.setAlignment(Qt.AlignCenter)
        emoji.setFixedWidth(42)
        emoji.setStyleSheet("font-size: 30px; border: none; background: transparent;")
        header.addWidget(emoji)

        name = self._gesture_name(gesture)
        title = QLabel(name)
        title.setWordWrap(True)
        title.setStyleSheet(
            "color: #4da6ff; font-size: 15px; font-weight: bold; "
            "border: none; background: transparent;"
        )
        header.addWidget(title, 1)

        hand_names = {
            "left": "ЛІВА",
            "right": "ПРАВА",
            "both": "ОБИДВІ",
        }
        hand_badge = QLabel(hand_names.get(gesture.get("hand"), "РУКА"))
        hand_badge.setStyleSheet(
            "color: #8b5cf6; font-size: 10px; font-weight: bold; "
            "border: none; background: transparent;"
        )
        header.addWidget(hand_badge)
        layout.addLayout(header)

        description = QLabel(
            str(gesture.get("description", "Опис для цього жесту відсутній."))
        )
        description.setWordWrap(True)
        description.setStyleSheet(
            "color: #e2e8f0; font-size: 12px; border: none; "
            "background: transparent;"
        )
        layout.addWidget(description)

        footer = QHBoxLayout()
        hold_seconds = float(gesture.get("hold_seconds", 0) or 0)
        if hold_seconds > 0:
            hold_label = QLabel(f"⏱ Утримувати {hold_seconds:g} сек")
            hold_label.setStyleSheet(
                "color: #8b5cf6; font-size: 11px; font-weight: bold; "
                "border: none; background: transparent;"
            )
            footer.addWidget(hold_label)
        if not gesture.get("enabled", True):
            disabled_label = QLabel("ВИМКНЕНО")
            disabled_label.setStyleSheet(
                "color: #64748b; font-size: 10px; border: none; "
                "background: transparent;"
            )
            footer.addWidget(disabled_label)
        footer.addStretch()
        layout.addLayout(footer)
        return card

    @staticmethod
    def _gesture_name(gesture):
        gesture_id = str(gesture.get("id", "")).upper()
        return GESTURE_TRANSLATIONS.get(
            gesture_id, str(gesture.get("name", "Невідомий жест"))
        )

    def _add_message(self, message):
        label = QLabel(message)
        label.setWordWrap(True)
        label.setStyleSheet("color: #e2e8f0; padding: 12px;")
        self.cards_layout.addWidget(label, 0, 0, 1, 3)
