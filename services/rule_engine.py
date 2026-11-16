import json
import time
import uuid
from copy import deepcopy
from pathlib import Path

from core.types import ROOT


RULES_PATH = ROOT / "data" / "rules.json"
VALID_HANDS = {"LEFT", "RIGHT", "ANY", "BOTH"}


class RuleValidationError(ValueError):
    pass


class RuleStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else RULES_PATH
        self.rules = []
        self.load()

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            self.rules = []
            self.save()
            return self.rules
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuleValidationError(
                f"Не вдалося прочитати файл правил {self.path}: {error}"
            ) from error

        if not isinstance(data, dict) or data.get("version") != 1:
            raise RuleValidationError("Непідтримуваний формат файлу правил.")
        rules = data.get("rules")
        if not isinstance(rules, list):
            raise RuleValidationError("Поле rules має бути масивом.")
        loaded_rules = [self._validate_rule(rule) for rule in rules]
        identifiers = [rule["id"] for rule in loaded_rules]
        if len(set(identifiers)) != len(identifiers):
            raise RuleValidationError("Ідентифікатори правил мають бути унікальними.")
        self.rules = loaded_rules
        return deepcopy(self.rules)

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        document = {"version": 1, "rules": self.rules}
        temporary_path = self.path.with_name(self.path.name + ".tmp")
        try:
            temporary_path.write_text(
                json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            temporary_path.replace(self.path)
        except OSError as error:
            raise OSError(f"Не вдалося зберегти правила у {self.path}: {error}") from error

    def add(self, rule):
        rule = self._validate_rule(rule)
        rule["id"] = rule.get("id") or uuid.uuid4().hex
        if any(existing["id"] == rule["id"] for existing in self.rules):
            raise RuleValidationError(f"Правило {rule['id']} вже існує.")
        self.rules.append(rule)
        try:
            self.save()
        except OSError:
            self.rules.pop()
            raise
        return deepcopy(rule)

    def update(self, rule_id, rule):
        updated = self._validate_rule(rule)
        for index, existing in enumerate(self.rules):
            if existing["id"] == rule_id:
                updated["id"] = rule_id
                self.rules[index] = updated
                try:
                    self.save()
                except OSError:
                    self.rules[index] = existing
                    raise
                return deepcopy(updated)
        raise KeyError(f"Правило {rule_id} не знайдено.")

    def delete(self, rule_id):
        updated = [rule for rule in self.rules if rule["id"] != rule_id]
        if len(updated) == len(self.rules):
            raise KeyError(f"Правило {rule_id} не знайдено.")
        previous = self.rules
        self.rules = updated
        try:
            self.save()
        except OSError:
            self.rules = previous
            raise

    @staticmethod
    def _validate_rule(rule):
        if not isinstance(rule, dict):
            raise RuleValidationError("Кожне правило має бути об'єктом.")
        triggers = rule.get("triggers")
        combination = rule.get("combination", False)
        hold_ms = rule.get("hold_ms", 500)
        actions = rule.get("actions")
        enabled = rule.get("enabled", True)
        if not isinstance(combination, bool):
            raise RuleValidationError("combination має бути логічним значенням.")
        if not isinstance(enabled, bool):
            raise RuleValidationError("enabled має бути логічним значенням.")
        if not isinstance(hold_ms, int) or isinstance(hold_ms, bool) or hold_ms < 0:
            raise RuleValidationError("hold_ms має бути невід'ємним цілим числом.")
        expected_count = 2 if combination else 1
        if not isinstance(triggers, list) or len(triggers) != expected_count:
            raise RuleValidationError(
                f"Правило має містити {expected_count} тригер(и)."
            )
        normalized_triggers = []
        seen_hands = set()
        for trigger in triggers:
            if (
                not isinstance(trigger, dict)
                or not isinstance(trigger.get("pose"), str)
                or not trigger["pose"].strip()
                or str(trigger.get("hand", "ANY")).upper() not in VALID_HANDS
            ):
                raise RuleValidationError("Тригер має містити коректні pose та hand.")
            hand = str(trigger.get("hand", "ANY")).upper()
            if combination and hand in {"ANY", "BOTH"}:
                raise RuleValidationError(
                    "Для комбінації оберіть окремо ліву та праву руку."
                )
            if combination and hand in seen_hands:
                raise RuleValidationError("Руки у комбінації мають відрізнятися.")
            seen_hands.add(hand)
            normalized_triggers.append(
                {"pose": trigger["pose"].strip().upper(), "hand": hand}
            )

        if not isinstance(actions, list) or not actions:
            raise RuleValidationError("Додайте щонайменше одну дію.")
        normalized_actions = []
        for step in actions:
            if (
                not isinstance(step, dict)
                or not isinstance(step.get("action"), str)
                or not step["action"].strip()
                or not isinstance(step.get("params", {}), dict)
            ):
                raise RuleValidationError("Крок дії має містити action та params.")
            normalized_actions.append(
                {
                    "action": step["action"].strip(),
                    "params": deepcopy(step.get("params", {})),
                }
            )

        return {
            "id": str(rule.get("id") or uuid.uuid4().hex),
            "name": str(rule.get("name") or ""),
            "triggers": normalized_triggers,
            "combination": combination,
            "hold_ms": hold_ms,
            "enabled": enabled,
            "actions": normalized_actions,
        }


class RuleEngine:
    def __init__(self, store=None):
        self.store = store or RuleStore()
        self._active = {}
        self._fired = set()
        self.hold_progress = 0.0

    @property
    def rules(self):
        return self.store.rules

    def reload(self):
        self.store.load()
        self.reset()

    def reset(self):
        self._active.clear()
        self._fired.clear()
        self.hold_progress = 0.0

    def update(self, predictions, now=None):
        now = time.monotonic() if now is None else float(now)
        current = {}
        for rule in self.store.rules:
            if not rule["enabled"]:
                continue
            matched = self._match_rule(rule, predictions)
            if matched is not None:
                current[rule["id"]] = matched

        for rule_id in tuple(self._active):
            if rule_id not in current:
                self._active.pop(rule_id, None)
                self._fired.discard(rule_id)

        triggered = []
        self.hold_progress = 0.0
        for rule in self.store.rules:
            rule_id = rule["id"]
            signature = current.get(rule_id)
            if signature is None:
                continue
            active = self._active.get(rule_id)
            if active is None or active[0] != signature:
                self._active[rule_id] = (signature, now)
                self._fired.discard(rule_id)
                started = now
            else:
                started = active[1]
            duration = rule["hold_ms"] / 1000.0
            elapsed = max(0.0, now - started)
            if duration > 0:
                self.hold_progress = max(
                    self.hold_progress,
                    min(1.0, elapsed / duration),
                )
            if elapsed >= duration and rule_id not in self._fired:
                self._fired.add(rule_id)
                triggered.append(deepcopy(rule))
        return triggered

    @staticmethod
    def _match_rule(rule, predictions):
        available = {
            str(hand).upper(): value[0]
            for hand, value in predictions.items()
            if isinstance(value, (tuple, list)) and len(value) >= 1
        }
        selected = []
        used_hands = set()
        for trigger in rule["triggers"]:
            requested_hand = trigger["hand"]
            pose = trigger["pose"]
            if requested_hand == "ANY":
                candidates = [
                    hand
                    for hand in ("LEFT", "RIGHT")
                    if hand not in used_hands and available.get(hand) == pose
                ]
            else:
                candidates = [
                    requested_hand
                ] if available.get(requested_hand) == pose else []
            if not candidates:
                return None
            selected_hand = candidates[0]
            if selected_hand in used_hands:
                return None
            selected.append((selected_hand, pose))
            used_hands.add(selected_hand)
        return tuple(sorted(selected))
