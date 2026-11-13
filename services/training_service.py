import os
import time
import numpy as np
import joblib
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from core.types import MODELS_DIR, SAMPLES_DIR

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
    def __init__(self):
        self.model_path = MODELS_DIR / "gesture_model.joblib"
        self.data_path = SAMPLES_DIR / "gesture_samples.npz"
        self.model = None
        self.accuracy = None
        self.accuracy_ids = None
        self.classes = []
        
        # Завантажуємо старі дані, якщо є
        self.X_data = np.array([])
        self.y_data = np.array([])
        self.ids_data = np.array([], dtype=float)
        self.load_data()
        self.load_model()

    def load_model(self):
        if not self.model_path.exists():
            return

        saved_model = joblib.load(self.model_path)
        if isinstance(saved_model, dict):
            self.model = saved_model["model"]
            saved_ids = saved_model.get("accuracy_ids")
            if (
                saved_model.get("accuracy") is not None
                and saved_ids is not None
                and np.array_equal(saved_ids, self.ids_data)
            ):
                self.accuracy = float(saved_model["accuracy"])
                self.accuracy_ids = self.ids_data.copy()
        else:
            self.model = saved_model

    def load_data(self):
        if self.data_path.exists():
            with np.load(self.data_path, allow_pickle=True) as data:
                self.X_data = data["X"]
                self.y_data = data["y"]
                self.ids_data = (
                    np.asarray(data["ids"], dtype=float)
                    if "ids" in data.files
                    else np.array([], dtype=float)
                )
            self.classes = list(np.unique(self.y_data))
            if len(self.ids_data) != len(self.y_data):
                count = len(self.y_data)
                self.ids_data = time.time() - np.arange(count, 0, -1) * 1e-6
                self.save_data()

    def save_data(self):
        np.savez(self.data_path, X=self.X_data, y=self.y_data, ids=self.ids_data)

    def add_sample(self, gesture_name: str, features: np.ndarray):
        # Додаємо новий приклад
        self.accuracy = None
        self.accuracy_ids = None
        features = features.flatten()
        if len(self.X_data) == 0:
            self.X_data = np.array([features])
            self.y_data = np.array([gesture_name])
        else:
            self.X_data = np.vstack([self.X_data, features])
            self.y_data = np.append(self.y_data, gesture_name)
        
        if gesture_name not in self.classes:
            self.classes.append(gesture_name)

        sample_id = time.time()
        if len(self.ids_data):
            sample_id = max(sample_id, float(np.max(self.ids_data)) + 1e-6)
            while np.any(self.ids_data == sample_id):
                sample_id += 1e-6
        self.ids_data = np.append(self.ids_data, sample_id)
        self.save_data()

    def delete_sample(self, index: int):
        if index < 0 or index >= len(self.y_data):
            raise IndexError("Індекс прикладу поза межами набору даних.")

        self.X_data = np.delete(self.X_data, index, axis=0)
        self.y_data = np.delete(self.y_data, index)
        self.ids_data = np.delete(self.ids_data, index)
        self.classes = list(np.unique(self.y_data))
        self.accuracy = None
        self.accuracy_ids = None
        self.save_data()

    def train_model(self):
        if len(self.X_data) < 10:
            return False, "Потрібно більше прикладів (мін. 10)"
            
        # Створюємо пайплайн: нормалізація + нейромережа (MLP)
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
        
        # Зберігаємо модель на диск
        joblib.dump({
            "model": self.model,
            "classes": self.classes,
            "accuracy": self.accuracy,
            "accuracy_ids": self.accuracy_ids,
        }, self.model_path)
        
        return True, "Модель успішно навчена!"

    def get_stats(self):
        """Повертає словник {жест: кількість прикладів}"""
        stats = {}
        for cls in np.unique(self.y_data):
            stats[cls] = int(np.sum(self.y_data == cls))
        return stats

    def get_raw_data(self) -> tuple[np.ndarray, np.ndarray]:
        return self.X_data.copy(), self.y_data.copy()

    def get_sample_ids(self) -> np.ndarray:
        return self.ids_data.copy()

    def get_feature_importance(self) -> np.ndarray:
        X, y = self.get_raw_data()
        if X.ndim != 2 or X.shape[0] < 2 or X.shape[1] == 0:
            raise ValueError("Недостатньо даних для обчислення важливості ознак.")

        model = RandomForestClassifier(n_estimators=200, random_state=42)
        model.fit(X, y)
        return model.feature_importances_.copy()

    def get_feature_names(self, feature_count: int | None = None) -> list[str]:
        if feature_count is None:
            feature_count = self.X_data.shape[1] if self.X_data.ndim == 2 else 0
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
        if self.model is None or self.X_data.ndim != 2 or not len(self.y_data):
            return None, []

        predictions = self.model.predict(self.X_data)
        classes = np.unique(np.concatenate((self.y_data, predictions)))
        matrix = confusion_matrix(self.y_data, predictions, labels=classes)
        return matrix, [str(label) for label in classes]

    def get_accuracy(self):
        return self.accuracy

    def clear_data(self):
        self.X_data = np.array([])
        self.y_data = np.array([])
        self.ids_data = np.array([], dtype=float)
        self.classes = []
        self.accuracy = None
        self.accuracy_ids = None
        if self.data_path.exists():
            os.remove(self.data_path)
        if self.model_path.exists():
            os.remove(self.model_path)
        self.model = None