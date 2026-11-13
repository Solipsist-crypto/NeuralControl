"""
Типи даних (dataclass'и) для всієї системи NeuralControl.

Правило: жоден модуль не передає "сирі" dict'и між шарами.
Тільки ці типи.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal

import numpy as np


# =========================================================
# ШЛЯХИ
# =========================================================

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
MODELS_DIR = DATA_DIR / "models"
SAMPLES_DIR = DATA_DIR / "samples"
ARCHIVES_DIR = DATA_DIR / "archives"
DRAWINGS_DIR = DATA_DIR / "drawings"
ASSETS_DIR = ROOT / "assets"

GESTURES_JSON = DATA_DIR / "gestures.json"
RADIAL_MENU_JSON = DATA_DIR / "radial_menu.json"
SETTINGS_JSON = DATA_DIR / "settings.json"
HAND_MODEL_PATH = ASSETS_DIR / "hand_landmarker.task"

# Автоматично створюємо папки
for _d in (MODELS_DIR, SAMPLES_DIR, ARCHIVES_DIR, DRAWINGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# =========================================================
# КОНСТАНТИ
# =========================================================

FEATURES_PER_HAND = 21 * 3
TOTAL_FEATURES = FEATURES_PER_HAND * 2

DEFAULT_CONFIDENCE_THRESHOLD = 0.7
MIN_SAMPLES_PER_CLASS = 15

# Тривалості утримання
HOLD_TOGGLE_MODE = 3.0      # перемикання режиму
HOLD_RADIAL_MENU = 0.5      # кругове меню
HOLD_CLICK = 0.2            # клік
HOLD_ACTION = 1.0           # звичайна дія


# =========================================================
# РЕЖИМИ
# =========================================================

class AppMode(Enum):
    """Поточний режим роботи."""
    IDLE = "idle"
    GESTURES = "gestures"
    MOUSE = "mouse"
    DRAWING = "drawing"


class HandSide(Enum):
    LEFT = "left"
    RIGHT = "right"
    BOTH = "both"


# =========================================================
# РУКА ТА КАДР
# =========================================================

@dataclass
class HandLandmarks:
    """Одна розпізнана рука: 21 точка."""
    side: HandSide
    points: np.ndarray          # (21, 3), float32
    confidence: float = 1.0


@dataclass
class FrameResult:
    """Результат обробки одного кадру."""
    hands: list[HandLandmarks] = field(default_factory=list)
    timestamp: float = 0.0

    @property
    def has_hands(self) -> bool:
        return len(self.hands) > 0

    def get_hand(self, side: HandSide) -> HandLandmarks | None:
        for h in self.hands:
            if h.side == side:
                return h
        return None


# =========================================================
# РОЗПІЗНАВАННЯ
# =========================================================

@dataclass
class Prediction:
    """Результат розпізнавання жесту."""
    gesture_id: str
    gesture_name: str
    confidence: float
    timestamp: float = 0.0

    def is_confident(self, threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> bool:
        return self.confidence >= threshold


# =========================================================
# ОПИС ЖЕСТУ
# =========================================================

ActionType = Literal["media", "key", "system", "mouse", "custom"]
GestureType = Literal["static", "dynamic"]


@dataclass
class GestureAction:
    """Що робити при активації жесту."""
    type: ActionType
    payload: dict


@dataclass
class GestureDefinition:
    """Повний опис жесту з gestures.json."""
    id: str
    name: str
    emoji: str
    type: GestureType
    hand: HandSide
    action: GestureAction
    hold_seconds: float
    description: str = ""
    enabled: bool = True


# =========================================================
# НАВЧАННЯ
# =========================================================

@dataclass
class TrainingSample:
    """Один приклад для навчання."""
    gesture_id: str
    features: np.ndarray        # (126,), float32
    timestamp: float = 0.0


@dataclass
class ModelMetrics:
    """Метрики моделі — для порівняння MLP/SVC/RF."""
    model_name: str
    accuracy: float
    train_time_sec: float
    n_samples: int
    n_classes: int


# =========================================================
# КРУГОВЕ МЕНЮ
# =========================================================

@dataclass
class RadialSector:
    """Один сектор кругового меню."""
    index: int
    icon: str = "empty"
    label: str = ""
    action: GestureAction | None = None
    enabled: bool = False


# =========================================================
# НАЛАШТУВАННЯ
# =========================================================

@dataclass
class AppSettings:
    """Налаштування програми (з settings.json)."""
    version: int = 1
    mode: str = "gestures"
    overlay_enabled: bool = True
    overlay_position: str = "top-right"
    tray_on_close: bool = True
    hotkey_pause: str = "Ctrl+Alt+G"
    camera_index: int = 0
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
    drawing_colors: list[str] = field(default_factory=lambda: [
        "#00d4ff", "#7c3aed", "#00ff88", "#ff3366", "#ffaa00"
    ])
    drawing_brush_size: int = 8
    model_type: str = "mlp"     # "mlp" | "svc" | "rf"