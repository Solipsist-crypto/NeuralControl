import os
import time
import numpy as np
import joblib
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from core.types import MODELS_DIR, SAMPLES_DIR

class TrainingService:
    def __init__(self):
        self.model_path = MODELS_DIR / "gesture_model.joblib"
        self.data_path = SAMPLES_DIR / "gesture_samples.npz"
        self.model = None
        self.classes = []
        
        # Завантажуємо старі дані, якщо є
        self.X_data = np.array([])
        self.y_data = np.array([])
        self.load_data()

    def load_data(self):
        if self.data_path.exists():
            data = np.load(self.data_path, allow_pickle=True)
            self.X_data = data["X"]
            self.y_data = data["y"]
            self.classes = list(np.unique(self.y_data))

    def save_data(self):
        np.savez(self.data_path, X=self.X_data, y=self.y_data)

    def add_sample(self, gesture_name: str, features: np.ndarray):
        # Додаємо новий приклад
        features = features.flatten()
        if len(self.X_data) == 0:
            self.X_data = np.array([features])
            self.y_data = np.array([gesture_name])
        else:
            self.X_data = np.vstack([self.X_data, features])
            self.y_data = np.append(self.y_data, gesture_name)
        
        if gesture_name not in self.classes:
            self.classes.append(gesture_name)
            
        self.save_data()

    def train_model(self):
        if len(self.X_data) < 10:
            return False, "Потрібно більше прикладів (мін. 10)"
            
        # Створюємо пайплайн: нормалізація + нейромережа (MLP)
        self.model = make_pipeline(
            StandardScaler(),
            MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=500, random_state=42)
        )
        
        # Навчаємо
        self.model.fit(self.X_data, self.y_data)
        
        # Зберігаємо модель на диск
        joblib.dump({
            "model": self.model,
            "classes": self.classes
        }, self.model_path)
        
        return True, "Модель успішно навчена!"

    def get_stats(self):
        """Повертає словник {жест: кількість прикладів}"""
        stats = {}
        for cls in np.unique(self.y_data):
            stats[cls] = int(np.sum(self.y_data == cls))
        return stats

    def clear_data(self):
        self.X_data = np.array([])
        self.y_data = np.array([])
        self.classes = []
        if self.data_path.exists():
            os.remove(self.data_path)
        if self.model_path.exists():
            os.remove(self.model_path)
        self.model = None