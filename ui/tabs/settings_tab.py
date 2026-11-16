import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIntValidator, QDoubleValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.types import GESTURE_TRANSLATIONS
from ui.widgets.glow_button import GlowButton
from services.action_catalog import (
    ACTION_GROUPS,
    ALL_ACTIONS,
    PARAMETER_FIELDS,
    WAIT_ACTION,
)
from services.rule_engine import RuleStore, RuleValidationError


class RuleDialog(QDialog):
    def __init__(self, poses, rule=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Конструктор правила")
        self.setMinimumWidth(560)
        self.setStyleSheet(
            """
            QDialog {
                background-color: #0a0e1a;
                color: #e2e8f0;
            }
            QLabel {
                color: #e2e8f0;
            }
            QLineEdit, QComboBox, QSpinBox, QListWidget {
                background-color: #131826;
                color: #e2e8f0;
                border: 1px solid #4da6ff;
                border-radius: 6px;
                padding: 7px;
                selection-background-color: #4da6ff;
                selection-color: #0a0e1a;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid #8b5cf6;
            }
            QComboBox QAbstractItemView {
                background-color: #131826;
                color: #e2e8f0;
                selection-background-color: #4da6ff;
                border: 1px solid #2a3350;
            }
            QComboBox::drop-down {
                background-color: #131826;
                border-left: 1px solid #2a3350;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #131826;
                border: none;
                width: 18px;
            }
            QCheckBox {
                color: #e2e8f0;
            }
            QListWidget::item:selected {
                background-color: #4da6ff;
                color: #0a0e1a;
            }
            QPushButton#RuleSaveButton {
                background-color: #123528;
                color: #4ade80;
                border: 1px solid #4ade80;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: bold;
            }
            QPushButton#RuleSaveButton:hover {
                background-color: #1b4b38;
            }
            QPushButton#RuleCancelButton {
                background-color: #351c2a;
                color: #f472b6;
                border: 1px solid #f472b6;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: bold;
            }
            QPushButton#RuleCancelButton:hover {
                background-color: #51243a;
            }
            """
        )
        self.poses = sorted(set(poses), key=str.casefold)
        self.rule = rule or {}
        self._parameter_inputs = {}
        self._build_ui()
        if self.rule:
            self._load_rule(self.rule)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 18)
        layout.setSpacing(12)

        title = QLabel(
            "РЕДАГУВАННЯ ПРАВИЛА" if self.rule else "НОВЕ ПРАВИЛО"
        )
        title.setStyleSheet("color:#4da6ff; font-size:17px; font-weight:700;")
        layout.addWidget(title)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Назва правила (необов'язково)")
        layout.addWidget(self.name_input)

        self.combination_check = QCheckBox("Комбінація: одночасно дві руки")
        self.combination_check.toggled.connect(self._set_combination)
        layout.addWidget(self.combination_check)

        self.trigger_rows = []
        for _ in ("LEFT", "RIGHT"):
            row_widget = QWidget()
            row = QHBoxLayout(row_widget)
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(QLabel("Рука:"))
            hand_combo = QComboBox()
            for label, value in (
                ("Ліва", "LEFT"),
                ("Права", "RIGHT"),
                ("Будь-яка", "ANY"),
                ("Обидві", "BOTH"),
            ):
                hand_combo.addItem(label, value)
            row.addWidget(hand_combo)

            pose_combo = QComboBox()
            for pose in self.poses:
                pose_combo.addItem(
                    GESTURE_TRANSLATIONS.get(pose, pose.replace("_", " ")),
                    pose,
                )
            row.addWidget(pose_combo, 1)
            layout.addWidget(row_widget)
            self.trigger_rows.append((row_widget, hand_combo, pose_combo))

        self.hold_spin = QSpinBox()
        self.hold_spin.setRange(0, 60000)
        self.hold_spin.setSingleStep(100)
        self.hold_spin.setSuffix(" мс утримання")
        layout.addWidget(self.hold_spin)

        action_header = QLabel("ПОСЛІДОВНІСТЬ ДІЙ")
        action_header.setStyleSheet("color:#4da6ff; font-weight:700;")
        layout.addWidget(action_header)
        self.action_combo = QComboBox()
        self.action_combo.addItem("Оберіть дію…", None)
        for category, actions in ACTION_GROUPS.items():
            self.action_combo.addItem(f"── {category} ──", None)
            for action in actions:
                self.action_combo.addItem(action, action)
        self.action_combo.addItem(WAIT_ACTION, WAIT_ACTION)
        self.action_combo.currentIndexChanged.connect(self._build_parameters)
        layout.addWidget(self.action_combo)

        self.parameters_widget = QWidget()
        self.parameters_layout = QVBoxLayout(self.parameters_widget)
        self.parameters_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.parameters_widget)

        action_controls = QHBoxLayout()
        self.add_action_button = GlowButton("ДОДАТИ КРОК", "#4da6ff")
        self.add_action_button.clicked.connect(self._append_action)
        self.remove_action_button = GlowButton("ВИДАЛИТИ КРОК", "#f472b6")
        self.remove_action_button.clicked.connect(self._remove_action)
        self.move_up_button = GlowButton("ВГОРУ", "#8b5cf6")
        self.move_up_button.clicked.connect(lambda: self._move_action(-1))
        self.move_down_button = GlowButton("ВНИЗ", "#8b5cf6")
        self.move_down_button.clicked.connect(lambda: self._move_action(1))
        for button in (
            self.add_action_button,
            self.remove_action_button,
            self.move_up_button,
            self.move_down_button,
        ):
            action_controls.addWidget(button)
        layout.addLayout(action_controls)

        self.actions_list = QListWidget()
        self.actions_list.setMinimumHeight(110)
        layout.addWidget(self.actions_list)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        save_button = buttons.button(QDialogButtonBox.Save)
        save_button.setText("ЗБЕРЕГТИ")
        save_button.setObjectName("RuleSaveButton")
        cancel_button = buttons.button(QDialogButtonBox.Cancel)
        cancel_button.setText("СКАСУВАТИ")
        cancel_button.setObjectName("RuleCancelButton")
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._set_combination(False)

    def _set_combination(self, enabled):
        self.trigger_rows[1][0].setVisible(enabled)
        if enabled:
            self.trigger_rows[0][1].setCurrentIndex(
                self.trigger_rows[0][1].findData("LEFT")
            )
            self.trigger_rows[1][1].setCurrentIndex(
                self.trigger_rows[1][1].findData("RIGHT")
            )
        else:
            self.trigger_rows[1][1].setCurrentIndex(
                self.trigger_rows[1][1].findData("RIGHT")
            )

    def _build_parameters(self):
        while self.parameters_layout.count():
            item = self.parameters_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._parameter_inputs.clear()
        action = self.action_combo.currentData()
        for key, label, default in PARAMETER_FIELDS.get(action, ()):
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            edit = QLineEdit(str(default))
            if key in {"percent", "x", "y", "width", "height", "minutes"}:
                edit.setValidator(QIntValidator(0, 100000, edit))
            elif key == "seconds":
                edit.setValidator(QDoubleValidator(0.0, 3600.0, 2, edit))
            row.addWidget(edit, 1)
            self.parameters_layout.addLayout(row)
            self._parameter_inputs[key] = edit

    def _append_action(self):
        action = self.action_combo.currentData()
        if action not in ALL_ACTIONS:
            QMessageBox.warning(self, "Дія не обрана", "Оберіть дію зі списку.")
            return
        params = {}
        for key, edit in self._parameter_inputs.items():
            value = edit.text().strip()
            optional_path = action == "Скріншот області" and key == "path"
            if not value and not optional_path:
                QMessageBox.warning(
                    self,
                    "Потрібен параметр",
                    f"Заповніть поле «{key}» для дії «{action}».",
                )
                return
            if key in {"percent", "x", "y", "width", "height", "minutes"}:
                params[key] = int(value) if value else 0
            elif key == "seconds":
                params[key] = float(value) if value else 0.0
            else:
                params[key] = value
        item = self._action_item(action, params)
        self.actions_list.addItem(item)

    @staticmethod
    def _action_item(action, params):
        item = QListWidgetItem(
            f"{action}  {json.dumps(params, ensure_ascii=False)}"
            if params
            else action
        )
        item.setData(Qt.UserRole, {"action": action, "params": params})
        return item

    def _remove_action(self):
        row = self.actions_list.currentRow()
        if row >= 0:
            self.actions_list.takeItem(row)

    def _move_action(self, offset):
        row = self.actions_list.currentRow()
        target = row + offset
        if row < 0 or target < 0 or target >= self.actions_list.count():
            return
        item = self.actions_list.takeItem(row)
        self.actions_list.insertItem(target, item)
        self.actions_list.setCurrentRow(target)

    def _load_rule(self, rule):
        self.name_input.setText(rule.get("name", ""))
        self.combination_check.setChecked(bool(rule.get("combination")))
        for index, trigger in enumerate(rule.get("triggers", [])):
            if index >= len(self.trigger_rows):
                break
            _, hand_combo, pose_combo = self.trigger_rows[index]
            hand_index = hand_combo.findData(trigger.get("hand", "ANY"))
            pose_index = pose_combo.findData(trigger.get("pose"))
            if hand_index >= 0:
                hand_combo.setCurrentIndex(hand_index)
            if pose_index >= 0:
                pose_combo.setCurrentIndex(pose_index)
        self.hold_spin.setValue(int(rule.get("hold_ms", 500)))
        for step in rule.get("actions", []):
            self.actions_list.addItem(
                self._action_item(step["action"], step.get("params", {}))
            )

    def _accept_if_valid(self):
        if not self.poses:
            QMessageBox.warning(
                self,
                "Немає жестів",
                "Спершу запишіть хоча б один жест у вкладці «Навчання».",
            )
            return
        if self.actions_list.count() == 0:
            QMessageBox.warning(
                self, "Немає дій", "Додайте щонайменше одну дію до правила."
            )
            return
        if self.combination_check.isChecked():
            left = self.trigger_rows[0][1].currentData()
            right = self.trigger_rows[1][1].currentData()
            if left == right or "ANY" in (left, right) or "BOTH" in (left, right):
                QMessageBox.warning(
                    self,
                    "Некоректна комбінація",
                    "Для комбінації оберіть ліву та праву руку.",
                )
                return
        self.accept()

    def get_rule(self):
        combination = self.combination_check.isChecked()
        count = 2 if combination else 1
        triggers = []
        for _, hand_combo, pose_combo in self.trigger_rows[:count]:
            pose = pose_combo.currentData()
            if pose is None:
                continue
            triggers.append(
                {"pose": pose, "hand": hand_combo.currentData()}
            )
        actions = [
            item.data(Qt.UserRole)
            for index in range(self.actions_list.count())
            if (item := self.actions_list.item(index)) is not None
        ]
        return {
            "id": self.rule.get("id"),
            "name": self.name_input.text().strip(),
            "triggers": triggers,
            "combination": combination,
            "hold_ms": self.hold_spin.value(),
            "enabled": self.rule.get("enabled", True),
            "actions": actions,
        }


class SettingsTab(QWidget):
    rules_changed = Signal()

    def __init__(self, training_service, rules_path=None):
        super().__init__()
        self.training_service = training_service
        self.store = RuleStore(rules_path)
        self._build_ui()
        self.refresh_rules()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(14)

        header = QFrame()
        header.setObjectName("SidePanel")
        header_layout = QHBoxLayout(header)
        title_layout = QVBoxLayout()
        title = QLabel("КОНСТРУКТОР ДІЙ")
        title.setStyleSheet(
            "color:#4da6ff; font-size:18px; font-weight:700; letter-spacing:1px;"
        )
        subtitle = QLabel(
            "Створюйте правила для жесту або одночасної комбінації; "
            "кожне правило може запускати послідовність."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#94a3b8;")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout, 1)
        self.add_rule_button = QPushButton("➕ ДОДАТИ ПРАВИЛО")
        self.add_rule_button.clicked.connect(self.add_rule)
        header_layout.addWidget(self.add_rule_button)
        layout.addWidget(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("border:none; background:transparent;")
        self.cards_container = QWidget()
        self.cards_layout = QGridLayout(self.cards_container)
        self.cards_layout.setContentsMargins(4, 4, 4, 4)
        self.cards_layout.setSpacing(12)
        self.scroll.setWidget(self.cards_container)
        layout.addWidget(self.scroll, 1)

    def _available_poses(self):
        stats = self.training_service.get_stats()
        return tuple(sorted(stats, key=str.casefold))

    def refresh_rules(self):
        try:
            self.store.load()
        except RuleValidationError as error:
            QMessageBox.warning(self, "Помилка правил", str(error))
            return
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for index, rule in enumerate(self.store.rules):
            self.cards_layout.addWidget(self._build_card(rule), index // 3, index % 3)
        self.cards_layout.setRowStretch((len(self.store.rules) + 2) // 3, 1)

    def _build_card(self, rule):
        card = QFrame()
        card.setObjectName("RuleCard")
        card.setStyleSheet(
            """
            QFrame#RuleCard {
                background-color: #131826;
                border: 1px solid #4da6ff;
                border-radius: 10px;
            }
            """
        )
        card.setMinimumHeight(220)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)

        trigger_labels = []
        for trigger in rule["triggers"]:
            pose = trigger["pose"]
            hand = trigger["hand"]
            translated = GESTURE_TRANSLATIONS.get(pose, pose.replace("_", " "))
            hand_label = {
                "LEFT": "Ліва",
                "RIGHT": "Права",
                "ANY": "Будь-яка",
                "BOTH": "Обидві",
            }[hand]
            trigger_labels.append(f"{hand_label}: {translated}")
        title = QLabel(" + ".join(trigger_labels) or rule.get("name", ""))
        title.setWordWrap(True)
        title.setStyleSheet("color:#4da6ff; font-size:14px; font-weight:700;")
        layout.addWidget(title)
        if rule.get("name"):
            rule_name = QLabel(rule["name"])
            rule_name.setWordWrap(True)
            rule_name.setStyleSheet("color:#94a3b8;")
            layout.addWidget(rule_name)
        hold_label = QLabel(f"Утримання: {rule['hold_ms']} мс")
        hold_label.setStyleSheet("color:#64748b;")
        layout.addWidget(hold_label)
        action_names = " → ".join(step["action"] for step in rule["actions"])
        actions = QLabel(action_names)
        actions.setWordWrap(True)
        actions.setStyleSheet("color:#e2e8f0;")
        layout.addWidget(actions, 1)

        controls = QHBoxLayout()
        edit_button = GlowButton("✏️ Редагувати", "#4da6ff")
        edit_button.setFixedHeight(34)
        edit_button.clicked.connect(
            lambda _checked=False, rule_id=rule["id"]: self.edit_rule(rule_id)
        )
        delete_button = GlowButton("🗑️ Видалити", "#f472b6")
        delete_button.setFixedHeight(34)
        delete_button.clicked.connect(
            lambda _checked=False, rule_id=rule["id"]: self.delete_rule(rule_id)
        )
        controls.addWidget(edit_button)
        controls.addWidget(delete_button)
        layout.addLayout(controls)
        return card

    def add_rule(self):
        dialog = RuleDialog(self._available_poses(), parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.store.add(dialog.get_rule())
        except (OSError, RuleValidationError) as error:
            QMessageBox.warning(self, "Не вдалося додати правило", str(error))
            return
        self.refresh_rules()
        self.rules_changed.emit()

    def edit_rule(self, rule_id):
        rule = next((item for item in self.store.rules if item["id"] == rule_id), None)
        if rule is None:
            QMessageBox.warning(self, "Правило не знайдено", rule_id)
            return
        dialog = RuleDialog(self._available_poses(), rule=rule, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self.store.update(rule_id, dialog.get_rule())
        except (OSError, KeyError, RuleValidationError) as error:
            QMessageBox.warning(self, "Не вдалося змінити правило", str(error))
            return
        self.refresh_rules()
        self.rules_changed.emit()

    def delete_rule(self, rule_id):
        answer = QMessageBox.question(
            self,
            "Видалити правило",
            "Видалити вибране правило безповоротно?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            self.store.delete(rule_id)
        except (OSError, KeyError) as error:
            QMessageBox.warning(self, "Не вдалося видалити правило", str(error))
            return
        self.refresh_rules()
        self.rules_changed.emit()
