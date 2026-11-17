import json
import os
import re
import time
from pathlib import Path
import numpy as np
import joblib
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from core.types import (
    GESTURE_REGISTRY_JSON,
    MODELS_DIR,
    SAMPLES_DIR,
    TOTAL_FEATURES,
)

FEATURE_MIGRATIONS = {
    42: (1, 21, 2),
    63: (1, 21, 3),
    84: (2, 21, 2),
}

HAND_LANDMARK_NAMES = (
    "зап'ястя",
    "основа великого пальця",
    "суглоб великого пальця",
    "міжфаланговий суглоб великого пальця",
    "кінчик великого пальця",
    "основа вказівного пальця",
    "проксимальний суглоб вказівного пальця",
    "дистальний суглоб вказівного пальця",
    "кінчик вказівного пальця",
    "основа середнього пальця",
    "проксимальний суглоб середнього пальця",
    "дистальний суглоб середнього пальця",
    "кінчик середнього пальця",
    "основа безіменного пальця",
    "проксимальний суглоб безіменного пальця",
    "дистальний суглоб безіменного пальця",
    "кінчик безіменного пальця",
    "основа мізинця",
    "проксимальний суглоб мізинця",
    "дистальний суглоб мізинця",
    "кінчик мізинця",
)


class TrainingService:
    """Manage gesture examples, classifier training, evaluation, and persistence."""

    def __init__(self, data_path=None, model_path=None, registry_path=None):
        """Load persisted training data and an optional trained classifier.

        Args:
            data_path: Optional path to the compressed training dataset.
            model_path: Optional path to the serialized classifier.
            registry_path: Optional path to the gesture registry JSON file.
        """
        self.model_path = Path(model_path) if model_path else MODELS_DIR / "gesture_model.joblib"
        self.data_path = Path(data_path) if data_path else SAMPLES_DIR / "gesture_samples.npz"
        self.registry_path = (
            Path(registry_path) if registry_path else GESTURE_REGISTRY_JSON
        )
        self.model = None
        self.model_error = None
        self.data_error = None
        self.migration_notice = None
        self.model_stale = False
        self.accuracy = None
        self.accuracy_ids = None
        self.classes = []
        
        # Load the existing dataset when one has already been saved.
        self.X_data = np.array([])
        self.y_data = np.array([])
        self.ids_data = np.array([], dtype=float)
        try:
            self.load_data()
        except (OSError, KeyError, ValueError) as error:
            self.data_error = f"Не вдалося завантажити навчальні дані: {error}"
            self.X_data = np.empty((0, TOTAL_FEATURES), dtype=np.float32)
            self.y_data = np.array([], dtype=str)
            self.ids_data = np.array([], dtype=float)
            self.classes = []
        self.load_model()

    def load_model(self):
        """Load a compatible model and restore its valid evaluation metadata."""
        if not self.model_path.exists():
            return

        try:
            saved_model = joblib.load(self.model_path)
            model = (
                saved_model["model"]
                if isinstance(saved_model, dict)
                else saved_model
            )
        except (
            OSError,
            EOFError,
            ImportError,
            AttributeError,
            KeyError,
            ValueError,
        ) as error:
            self.model_error = f"Не вдалося завантажити модель: {error}"
            return

        feature_count = getattr(model, "n_features_in_", None)
        if feature_count is not None and int(feature_count) != TOTAL_FEATURES:
            self.model_error = (
                f"Модель має {feature_count} ознак; потрібно {TOTAL_FEATURES}. "
                "Перенавчіть її на оновлених даних."
            )
            return

        self.model = model
        self.model_error = None
        if isinstance(saved_model, dict):
            saved_ids = saved_model.get("accuracy_ids")
            if (
                saved_model.get("accuracy") is not None
                and saved_ids is not None
                and np.array_equal(saved_ids, self.ids_data)
            ):
                self.accuracy = float(saved_model["accuracy"])
                self.accuracy_ids = self.ids_data.copy()
            elif saved_ids is not None:
                self.model_stale = True

    def load_data(self):
        """Load, validate, and migrate persisted samples and their labels."""
        if self.data_path.exists():
            with np.load(self.data_path, allow_pickle=True) as data:
                self.X_data = np.asarray(data["X"], dtype=np.float32)
                raw_labels = np.asarray(data["y"], dtype=str)
                self.y_data = np.asarray(
                    [self.normalize_gesture_name(label) for label in raw_labels],
                    dtype=str,
                )
                self.ids_data = (
                    np.asarray(data["ids"], dtype=float)
                    if "ids" in data.files
                    else np.array([], dtype=float)
                )
            if self.X_data.ndim != 2:
                raise ValueError("Файл прикладів має містити двовимірний масив X.")
            if self.X_data.shape[1] in FEATURE_MIGRATIONS:
                old_feature_count = self.X_data.shape[1]
                # Legacy rows are reshaped, zero-padded, and stored in the current two-hand XYZ layout.
                self.X_data = self._migrate_features(self.X_data)
                self.save_data()
                self.migration_notice = (
                    f"Старі приклади ({old_feature_count} ознаки) доповнено до "
                    f"{TOTAL_FEATURES}. Для точнішого результату перезапишіть "
                    "двуручні жести та приклади з глибиною."
                )
            elif not np.array_equal(raw_labels, self.y_data):
                self.model_stale = True
                self.save_data()
            elif self.X_data.shape[1] != TOTAL_FEATURES:
                raise ValueError(
                    f"Знайдено {self.X_data.shape[1]} ознак; очікується "
                    f"{TOTAL_FEATURES}."
                )
            self.classes = list(np.unique(self.y_data))
            if len(self.ids_data) != len(self.y_data):
                count = len(self.y_data)
                self.ids_data = time.time() - np.arange(count, 0, -1) * 1e-6
                self.save_data()
            self.ensure_registry_entries(self.classes)

    @staticmethod
    def _migrate_features(features):
        old_count = features.shape[1]
        hand_count, landmark_count, coordinate_count = FEATURE_MIGRATIONS[old_count]
        legacy = features.reshape(-1, hand_count, landmark_count, coordinate_count)
        migrated = np.zeros(
            (len(features), 2, 21, 3),
            dtype=np.float32,
        )
        migrated[:, :hand_count, :, :coordinate_count] = legacy
        return migrated.reshape(-1, TOTAL_FEATURES)

    def save_data(self):
        """Persist feature rows, labels, and stable sample IDs to disk."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(self.data_path, X=self.X_data, y=self.y_data, ids=self.ids_data)

    def add_sample(self, gesture_name: str, features: np.ndarray):
        """Append one labeled feature vector to the training dataset.

        Args:
            gesture_name: Human-provided label, normalized to an uppercase ID.
            features: Feature vector containing exactly ``TOTAL_FEATURES`` values.

        Returns:
            The normalized gesture identifier.
        """
        return self.add_samples(gesture_name, np.asarray(features).reshape(1, -1))

    def add_samples(self, gesture_name: str, samples: np.ndarray):
        """Append a batch of labeled vectors and register the gesture if needed.

        Args:
            gesture_name: Label shared by all rows in ``samples``.
            samples: One vector or a matrix with ``TOTAL_FEATURES`` columns.

        Returns:
            The normalized gesture identifier.
        """
        if self.data_error:
            raise ValueError(self.data_error)
        gesture_name = self.normalize_gesture_name(gesture_name)
        samples = np.asarray(samples, dtype=np.float32)
        if samples.ndim == 1:
            samples = samples.reshape(1, -1)
        if samples.ndim != 2 or samples.shape[1] != TOTAL_FEATURES:
            raise ValueError(
                f"Кожен приклад має містити {TOTAL_FEATURES} ознак."
            )
        if len(samples) == 0:
            raise ValueError("Потрібен хоча б один приклад жесту.")
        if not np.isfinite(samples).all():
            raise ValueError("Ознаки жесту містять нескінченні або некоректні значення.")
        self.accuracy = None
        self.accuracy_ids = None
        self.model_stale = True
        if len(self.X_data) == 0:
            self.X_data = samples.copy()
            self.y_data = np.full(len(samples), gesture_name)
        else:
            self.X_data = np.vstack([self.X_data, samples])
            self.y_data = np.append(
                self.y_data, np.full(len(samples), gesture_name)
            )
        
        if gesture_name not in self.classes:
            self.classes.append(gesture_name)

        sample_id = time.time()
        if len(self.ids_data):
            sample_id = max(sample_id, float(np.max(self.ids_data)) + 1e-6)
        sample_ids = sample_id + np.arange(len(samples), dtype=np.float64) * 1e-6
        self.ids_data = np.append(self.ids_data, sample_ids)
        self.save_data()
        self.ensure_registry_entries([gesture_name])
        return gesture_name

    @staticmethod
    def normalize_gesture_name(gesture_name):
        """Normalize a user-entered gesture label to an uppercase ID.

        Args:
            gesture_name: Name to trim and convert to underscore-separated form.

        Returns:
            The normalized identifier.

        Raises:
            ValueError: If the normalized name is empty.
        """
        normalized = re.sub(r"\s+", "_", str(gesture_name).strip()).upper()
        if not normalized:
            raise ValueError("Назва жесту не може бути порожньою.")
        return normalized

    def ensure_registry_entries(self, poses):
        """Add missing gesture IDs to the registry without overwriting existing entries.

        Args:
            poses: Iterable of gesture labels to ensure are registered.
        """
        try:
            registry = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            registry = []
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                f"Не вдалося прочитати реєстр жестів {self.registry_path}: {error}"
            ) from error
        if not isinstance(registry, list):
            raise ValueError("Реєстр жестів має містити JSON-масив.")

        existing = {
            entry.get("pose"): entry
            for entry in registry
            if isinstance(entry, dict) and isinstance(entry.get("pose"), str)
        }
        added = False
        for pose in poses:
            normalized = self.normalize_gesture_name(pose)
            if normalized not in existing:
                registry.append({
                    "pose": normalized,
                    "hand": "ANY",
                    "action": "",
                    "hold_ms": 500,
                    "enabled": True,
                })
                added = True
        if not added:
            return

        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.registry_path.write_text(
                json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as error:
            raise OSError(
                f"Не вдалося зберегти реєстр жестів {self.registry_path}: {error}"
            ) from error

    def delete_sample(self, index: int):
        """Delete a sample row and invalidate cached evaluation metadata.

        Args:
            index: Zero-based row index in the dataset.

        Raises:
            IndexError: If the index is outside the dataset.
        """
        if index < 0 or index >= len(self.y_data):
            raise IndexError("Індекс прикладу поза межами набору даних.")

        self.X_data = np.delete(self.X_data, index, axis=0)
        self.y_data = np.delete(self.y_data, index)
        self.ids_data = np.delete(self.ids_data, index)
        self.classes = list(np.unique(self.y_data))
        self.accuracy = None
        self.accuracy_ids = None
        self.model_stale = True
        self.save_data()

    def train_model(self):
        """Train, evaluate, and persist the MLP classifier.

        Returns:
            ``(success, message)`` describing the outcome of model training.
        """
        if self.data_error:
            return False, self.data_error
        if len(self.X_data) < 10:
            return False, "Потрібно більше прикладів (мін. 10)"
        if len(np.unique(self.y_data)) < 2:
            return False, "Для навчання потрібні приклади щонайменше двох жестів."
        if self.X_data.ndim != 2 or self.X_data.shape[1] != TOTAL_FEATURES:
            return False, f"Дані мають містити {TOTAL_FEATURES} ознак на приклад."
            
        # Scale coordinates before fitting the MLP so features with larger ranges do not dominate.
        self.model = make_pipeline(
            StandardScaler(),
            MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=500, random_state=42)
        )
        
        X_train, X_test, y_train, y_test = train_test_split(
            self.X_data,
            self.y_data,
            test_size=0.2,
            random_state=42,
        )
        self.model.fit(X_train, y_train)
        self.accuracy = float(
            accuracy_score(y_test, self.model.predict(X_test))
        )
        self.accuracy_ids = self.ids_data.copy()
        self.model_error = None
        self.model_stale = False
        
        # Persist the trained model and its evaluation metadata.
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            "model": self.model,
            "classes": self.classes,
            "accuracy": self.accuracy,
            "accuracy_ids": self.accuracy_ids,
        }, self.model_path)
        
        return True, "Модель успішно навчена!"

    def get_stats(self):
        """Return the number of stored samples for each gesture identifier.

        Returns:
            Mapping from gesture ID to sample count.
        """
        stats = {}
        for cls in np.unique(self.y_data):
            stats[cls] = int(np.sum(self.y_data == cls))
        return stats

    def get_raw_data(self) -> tuple[np.ndarray, np.ndarray]:
        """Return copies of the feature matrix and corresponding labels."""
        return self.X_data.copy(), self.y_data.copy()

    def get_sample_ids(self) -> np.ndarray:
        """Return a copy of the stable sample identifiers."""
        return self.ids_data.copy()

    def get_feature_importance(self) -> np.ndarray:
        """Fit a random forest and return feature importance scores.

        Returns:
            A copy of the score for each input feature.

        Raises:
            ValueError: If the dataset is too small to compute importances.
        """
        X, y = self.get_raw_data()
        if X.ndim != 2 or X.shape[0] < 2 or X.shape[1] == 0:
            raise ValueError("Недостатньо даних для обчислення важливості ознак.")

        model = RandomForestClassifier(n_estimators=200, random_state=42)
        model.fit(X, y)
        return model.feature_importances_.copy()

    def get_feature_names(self, feature_count: int | None = None) -> list[str]:
        """Describe feature columns for reports and visualizations.

        Args:
            feature_count: Number of input columns; defaults to the current dataset.

        Returns:
            Human-readable labels in column order.
        """
        if feature_count is None:
            feature_count = self.X_data.shape[1] if self.X_data.ndim == 2 else 0
        if feature_count == TOTAL_FEATURES:
            axes = ("X", "Y", "Z")
            return [
                f"{side} — {axis} — {landmark}"
                for side in ("Ліва рука", "Права рука")
                for landmark in HAND_LANDMARK_NAMES
                for axis in axes
            ]
        coordinate_count = feature_count // len(HAND_LANDMARK_NAMES)
        if feature_count % len(HAND_LANDMARK_NAMES) or coordinate_count not in (2, 3):
            return [f"Ознака {i + 1}" for i in range(feature_count)]

        axes = ("X", "Y", "Z")
        return [
            f"Координата {axes[coordinate]} — {landmark}"
            for landmark in HAND_LANDMARK_NAMES
            for coordinate in range(coordinate_count)
        ]

    def get_confusion_matrix(self):
        """Evaluate the current model against stored samples.

        Returns:
            A ``(matrix, class_labels)`` pair, or an empty result if unavailable.
        """
        if self.model is None or self.X_data.ndim != 2 or not len(self.y_data):
            return None, []

        predictions = self.model.predict(self.X_data)
        classes = np.unique(np.concatenate((self.y_data, predictions)))
        matrix = confusion_matrix(self.y_data, predictions, labels=classes)
        return matrix, [str(label) for label in classes]

    def get_accuracy(self):
        """Return the most recently computed held-out accuracy, if available."""
        return self.accuracy

    def clear_data(self):
        """Remove saved examples and the trained model, then reset service state."""
        self.X_data = np.array([])
        self.y_data = np.array([])
        self.ids_data = np.array([], dtype=float)
        self.classes = []
        self.accuracy = None
        self.accuracy_ids = None
        self.data_error = None
        self.migration_notice = None
        self.model_error = None
        self.model_stale = False
        if self.data_path.exists():
            os.remove(self.data_path)
        if self.model_path.exists():
            os.remove(self.model_path)
        self.model = None