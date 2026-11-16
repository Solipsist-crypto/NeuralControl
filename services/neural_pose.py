from collections import defaultdict, deque
import json
import pickle
from pathlib import Path

import joblib
import numpy as np

from core.types import GESTURE_REGISTRY_JSON, ROOT, TOTAL_FEATURES


DEFAULT_MODEL_PATH = ROOT / "data" / "models" / "gesture_model.joblib"


class NeuralPose:
    CONFIDENCE_THRESHOLD = 0.9
    VOTE_WINDOW = 10
    REQUIRED_VOTES = 8
    FEATURE_COUNT = TOTAL_FEATURES
    HAND_SIDES = ("LEFT", "RIGHT")

    def __init__(self, model_path=None, model=None, enabled=True, registry_path=None):
        self.model_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        self.registry_path = (
            Path(registry_path) if registry_path else GESTURE_REGISTRY_JSON
        )
        self.enabled = bool(enabled)
        self.configuration_error = None
        self.model = model if self.enabled else None
        self.load_error = None
        self.feature_count = None
        self._votes = defaultdict(lambda: deque(maxlen=self.VOTE_WINDOW))
        self.registry_entries = {}
        self.registry_gestures = frozenset()
        self.registry_error = None
        self._registry_mtime_ns = None
        self._refresh_gesture_registry(force=True)

        if self.enabled:
            if self.model is None:
                self._load_model()
            else:
                self.feature_count = self._get_feature_count()
                if self.feature_count != self.FEATURE_COUNT:
                    self.model = None
                    self.load_error = (
                        f"Модель має {self.feature_count} ознак; потрібно "
                        f"{self.FEATURE_COUNT}. Перенавчіть її."
                    )

    def _load_model(self):
        self.load_error = None
        self.model = None
        self.feature_count = None
        if not self.model_path.is_file():
            self.load_error = f"Файл моделі не знайдено: {self.model_path}"
            return

        try:
            saved_model = joblib.load(self.model_path)
            self.model = (
                saved_model["model"]
                if isinstance(saved_model, dict)
                else saved_model
            )
            self.feature_count = self._get_feature_count()
            if self.feature_count != self.FEATURE_COUNT:
                raise ValueError(
                    f"Модель має {self.feature_count} ознак; потрібно "
                    f"{self.FEATURE_COUNT}. Перенавчіть її."
                )
            if not hasattr(self.model, "predict_proba"):
                raise ValueError("Модель не підтримує оцінку впевненості.")
        except (
            OSError,
            EOFError,
            ImportError,
            AttributeError,
            KeyError,
            TypeError,
            ValueError,
            pickle.UnpicklingError,
        ) as error:
            self.model = None
            self.feature_count = None
            self.load_error = f"Не вдалося завантажити модель {self.model_path}: {error}"

    def set_enabled(self, enabled):
        enabled = bool(enabled)
        if self.enabled == enabled:
            return

        self.enabled = enabled
        self.reset()
        if enabled:
            self._load_model()
        else:
            self.model = None
            self.feature_count = None
            self.load_error = None

    def reload_model(self):
        self.reset()
        self._refresh_gesture_registry(force=True)
        if self.enabled:
            self._load_model()
        else:
            self.model = None
            self.feature_count = None
            self.load_error = None

    def _refresh_gesture_registry(self, force=False):
        try:
            modified_at = self.registry_path.stat().st_mtime_ns
        except OSError as error:
            self.registry_entries = {}
            self.registry_gestures = frozenset()
            self.registry_error = f"Не вдалося прочитати {self.registry_path}: {error}"
            self._registry_mtime_ns = None
            return

        if not force and modified_at == self._registry_mtime_ns:
            return

        try:
            registry = json.loads(self.registry_path.read_text(encoding="utf-8"))
            if not isinstance(registry, list):
                raise ValueError("Реєстр жестів має містити JSON-масив.")
            entries = {}
            for index, entry in enumerate(registry):
                if (
                    not isinstance(entry, dict)
                    or not isinstance(entry.get("pose"), str)
                    or not entry["pose"].strip()
                    or not isinstance(entry.get("enabled", True), bool)
                    or not isinstance(entry.get("hand", "ANY"), str)
                    or not isinstance(entry.get("action", ""), str)
                    or not isinstance(entry.get("hold_ms", 500), int)
                    or isinstance(entry.get("hold_ms", 500), bool)
                    or entry.get("hold_ms", 500) < 0
                ):
                    raise ValueError(f"Некоректний запис жесту з індексом {index}.")
                if entry.get("hand", "ANY") not in {"LEFT", "RIGHT", "ANY", "BOTH"}:
                    raise ValueError(f"Некоректна рука у записі з індексом {index}.")
                if entry.get("enabled", True):
                    entries[entry["pose"]] = {
                        **entry,
                        "hand": entry.get("hand", "ANY"),
                        "action": entry.get("action", ""),
                        "hold_ms": entry.get("hold_ms", 500),
                    }
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            self.registry_entries = {}
            self.registry_gestures = frozenset()
            self.registry_error = f"Не вдалося прочитати {self.registry_path}: {error}"
        else:
            self.registry_entries = entries
            self.registry_gestures = frozenset(entries)
            self.registry_error = None
        self._registry_mtime_ns = modified_at

    def _get_feature_count(self):
        if self.model is None:
            return None

        feature_count = getattr(self.model, "n_features_in_", None)
        if feature_count is None and hasattr(self.model, "steps"):
            feature_count = getattr(self.model.steps[-1][1], "n_features_in_", None)
        return int(feature_count) if feature_count is not None else None

    def get_gesture_config(self, pose):
        self._refresh_gesture_registry()
        return self.registry_entries.get(
            pose,
            {"pose": pose, "hand": "ANY", "action": "", "hold_ms": 500},
        )

    def reset(self, slot=None):
        if slot is None:
            self._votes.clear()
        else:
            self._votes.pop(str(slot).upper(), None)

    def vote_window_full(self, slot):
        return len(self._votes[str(slot).upper()]) >= self.VOTE_WINDOW

    @classmethod
    def features_from_hands(cls, hands):
        packed = np.zeros((2, 21, 3), dtype=np.float32)
        hand_indexes = {"LEFT": 0, "RIGHT": 1}
        for side, raw_points in hands.items():
            side = str(side).upper()
            if side not in hand_indexes:
                continue
            points = np.asarray(raw_points, dtype=np.float32)
            if (
                points.ndim != 2
                or points.shape[0] != 21
                or points.shape[1] not in (2, 3)
            ):
                raise ValueError(
                    f"Координати руки {side} мають мати форму (21, 2) або (21, 3)."
                )
            if not np.isfinite(points).all():
                raise ValueError(f"Координати руки {side} містять некоректні значення.")
            packed[hand_indexes[side], :, :points.shape[1]] = points
        return packed.reshape(cls.FEATURE_COUNT)

    def predict(
        self,
        hands,
        excluded_sides=(),
        allowed_gestures=None,
        include_both=False,
        sides=None,
    ):
        if not self.enabled or self.model is None:
            self.reset()
            return {}

        self._refresh_gesture_registry()
        excluded = {str(side).upper() for side in excluded_sides}
        normalized_hands = {
            str(side).upper(): np.asarray(points, dtype=np.float32)
            for side, points in hands.items()
            if str(side).upper() in self.HAND_SIDES
        }
        selected_sides = (
            set(normalized_hands)
            if sides is None
            else {str(side).upper() for side in sides}
        )
        feature_rows = {}
        for side in self.HAND_SIDES:
            if side not in selected_sides:
                continue
            points = normalized_hands.get(side)
            if points is None or side in excluded:
                self.reset(side)
                continue
            feature_rows[side] = (
                self.features_from_hands({side: points}),
                self._allowed_for_hand(side, allowed_gestures),
            )
        if include_both:
            if {"LEFT", "RIGHT"}.issubset(normalized_hands):
                feature_rows["BOTH"] = (
                    self.features_from_hands(normalized_hands),
                    self._allowed_for_both(allowed_gestures),
                )
            else:
                self.reset("BOTH")
        return self._predict_feature_batch(feature_rows)

    def predict_both(self, hands, allowed_gestures=None):
        return self.predict(
            hands,
            allowed_gestures=allowed_gestures,
            include_both=True,
            sides=(),
        ).get("BOTH")

    def _allowed_for_both(self, allowed_gestures):
        allowed = {
            pose
            for pose, entry in self.registry_entries.items()
            if entry.get("hand", "ANY") == "BOTH"
        }
        allowed.intersection_update(str(label) for label in self.model.classes_)
        if allowed_gestures is not None:
            allowed.intersection_update(allowed_gestures)
        return frozenset(allowed)

    def _allowed_for_hand(self, side, allowed_gestures):
        allowed = {
            pose
            for pose, entry in self.registry_entries.items()
            if entry.get("hand", "ANY") in {"ANY", side}
        }
        allowed.intersection_update(str(label) for label in self.model.classes_)
        if allowed_gestures is not None:
            allowed.intersection_update(allowed_gestures)
        return frozenset(allowed)

    def _predict_feature_batch(self, feature_rows):
        candidates = {}
        inference_slots = []
        inference_features = []
        classes = [str(label) for label in self.model.classes_]
        allowed_indexes_by_slot = {}
        for slot, (features, allowed_gestures) in feature_rows.items():
            row = np.asarray(features, dtype=np.float32).reshape(-1)
            if row.size != self.FEATURE_COUNT:
                raise ValueError(
                    f"Нейромережа очікує {self.FEATURE_COUNT} ознак, отримано "
                    f"{row.size}."
                )
            allowed_indexes = [
                index
                for index, label in enumerate(classes)
                if label in allowed_gestures
            ]
            allowed_indexes_by_slot[slot] = allowed_indexes
            if allowed_indexes:
                inference_slots.append(slot)
                inference_features.append(row)

        probabilities = None
        if inference_features:
            probabilities = np.asarray(
                self.model.predict_proba(np.stack(inference_features))[...],
                dtype=np.float32,
            )
            if (
                probabilities.ndim != 2
                or probabilities.shape != (len(inference_slots), len(classes))
            ):
                raise ValueError("Модель повернула некоректну кількість оцінок.")
        inference_index = {
            slot: index for index, slot in enumerate(inference_slots)
        }

        for slot in feature_rows:
            candidate = None
            confidence = 0.0
            allowed_indexes = allowed_indexes_by_slot[slot]
            if allowed_indexes:
                score_row = probabilities[inference_index[slot]]
                best_index = allowed_indexes[
                    int(np.argmax(score_row[allowed_indexes]))
                ]
                confidence = float(score_row[best_index])
                if confidence >= self.CONFIDENCE_THRESHOLD:
                    candidate = classes[best_index]
            stable = self._record_vote(slot, candidate, confidence)
            if stable is not None:
                candidates[slot] = stable
        return candidates

    def _record_vote(self, slot, candidate, confidence):
        votes = self._votes[str(slot).upper()]
        votes.append((candidate, confidence))
        counts = {}
        for gesture, _ in votes:
            if gesture is not None:
                counts[gesture] = counts.get(gesture, 0) + 1

        stable = max(counts, key=counts.get, default=None)
        if stable is None or counts[stable] < self.REQUIRED_VOTES:
            return None
        matching_confidences = [
            score for gesture, score in votes if gesture == stable
        ]
        return stable, float(np.mean(matching_confidences))
