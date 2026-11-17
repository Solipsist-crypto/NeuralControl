"""Shared data types, constants, and runtime paths for NeuralControl."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import sys
from typing import Literal

import numpy as np


# =========================================================
# PATHS
# =========================================================

if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).resolve().parent
else:
    ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
MODELS_DIR = DATA_DIR / "models"
SAMPLES_DIR = DATA_DIR / "samples"
ARCHIVES_DIR = DATA_DIR / "archives"
DRAWINGS_DIR = DATA_DIR / "drawings"
ASSETS_DIR = ROOT / "assets"

GESTURE_REGISTRY_JSON = DATA_DIR / "gesture_registry.json"
RADIAL_MENU_JSON = DATA_DIR / "radial_menu.json"
SETTINGS_JSON = DATA_DIR / "settings.json"
HAND_MODEL_PATH = ASSETS_DIR / "hand_landmarker.task"
if getattr(sys, "frozen", False) and not HAND_MODEL_PATH.is_file():
    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root is not None:
        bundled_model = Path(bundled_root) / "assets" / "hand_landmarker.task"
        if bundled_model.is_file():
            HAND_MODEL_PATH = bundled_model

# Create data folders when the application starts.
for _d in (MODELS_DIR, SAMPLES_DIR, ARCHIVES_DIR, DRAWINGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# =========================================================
# CONSTANTS
# =========================================================

FEATURES_PER_HAND = 21 * 3
TOTAL_FEATURES = FEATURES_PER_HAND * 2

DEFAULT_CONFIDENCE_THRESHOLD = 0.7
MIN_SAMPLES_PER_CLASS = 15

GESTURE_TRANSLATIONS = {
    "LEFT_FIST": "ЛІВИЙ КУЛАК",
    "RIGHT_FIST": "ПРАВИЙ КУЛАК",
    "LEFT_OPEN": "ЛІВА ДОЛОНЯ",
    "RIGHT_OPEN": "ПРАВА ДОЛОНЯ",
    "LEFT_POINT": "ЛІВИЙ ВКАЗІВНИЙ",
    "FIST": "КУЛАК",
    "OPEN": "ДОЛОНЯ",
    "POINT": "ВКАЗІВНИЙ ПАЛЕЦЬ",
    "POINT_DOWN": "ПАЛЕЦЬ ВНИЗ",
    "PINCH": "ЩИПОК",
    "ROCK": "РОК",
    "PEACE": "V-ПОЗА",
    "THUMB_UP": "ПАЛЕЦЬ ВГОРУ",
    "THUMB_DOWN": "ПАЛЕЦЬ ВНИЗ",
    "OK": "ЖЕСТ «ОК»",
    "THREE": "ТРИ ПАЛЬЦІ",
    "FOUR": "ЧОТИРИ ПАЛЬЦІ",
    "PINKY_UP": "МІЗИНЕЦЬ ВГОРУ",
    "MIDDLE_UP": "СЕРЕДНІЙ ПАЛЕЦЬ ВГОРУ",
    "CALL_ME": "ПОДЗВОНИ МЕНІ",
    "GUN": "ПІСТОЛЕТ",
    "CLAW": "КІГТІ",
    "C_SHAPE": "ФОРМА C",
    "PINCH_MIDDLE": "ЩИПОК СЕРЕДНІМ ПАЛЬЦЕМ",
    "PINCH_RING": "ЩИПОК БЕЗІМЕННИМ ПАЛЬЦЕМ",
    "PINCH_PINKY": "ЩИПОК МІЗИНЦЕМ",
    "COUNT_1": "ОДИН",
    "COUNT_2": "ДВА",
    "COUNT_3": "ТРИ",
    "COUNT_4": "ЧОТИРИ",
    "COUNT_5": "П'ЯТЬ",
    "BOTH_PINCH": "ЩИПОК ОБОМА РУКАМИ",
    "BOTH_POINT": "ДВА ВКАЗІВНІ ПАЛЬЦІ",
    "BOTH_PEACE": "ДВІ V-ПОЗИ",
    "BOTH_THUMB_UP": "ОБИДВА ПАЛЬЦІ ВГОРУ",
    "CLAP_POSE": "ПОЗА ДЛЯ АПЛОДИСМЕНТІВ",
    "T_SHAPE": "ФОРМА T",
    "FRAME": "РАМКА",
    "X_CROSS": "ПЕРЕХРЕСТЯ",
    "VULCAN": "ВУЛКАН",
    "I_LOVE_YOU": "ЛЮБЛЮ",
    "BOTH_HEART": "СЕРЦЕ ОБОМА РУКАМИ",
    "CROSSED_FINGERS": "ПЕРЕХРЕЩЕНІ ПАЛЬЦІ",
    "WAVE": "ПОМАХ",
    "SWIPE_LEFT": "СВАЙП ЛІВОРУЧ",
    "SWIPE_RIGHT": "СВАЙП ПРАВОРУЧ",
    "SWIPE_UP": "СВАЙП ВГОРУ",
    "SWIPE_DOWN": "СВАЙП ВНИЗ",
    "CIRCLE_CW": "КОЛО ЗА ГОДИННИКОВОЮ СТРІЛКОЮ",
    "CIRCLE_CCW": "КОЛО ПРОТИ ГОДИННИКОВОЇ СТРІЛКИ",
    "ZOOM_IN": "ЗБІЛЬШЕННЯ",
    "ZOOM_OUT": "ЗМЕНШЕННЯ",
    "DRAW_CHECK": "ГАЛОЧКА В ПОВІТРІ",
    "DRAW_X": "ХРЕСТИК У ПОВІТРІ",
}

# Hold durations in seconds.
HOLD_TOGGLE_MODE = 3.0      # Mode toggle
HOLD_RADIAL_MENU = 0.5      # Radial menu
HOLD_CLICK = 0.2            # Click
HOLD_ACTION = 1.0           # Standard action


# =========================================================
# MODES
# =========================================================

class AppMode(Enum):
    """Available application operating modes."""
    IDLE = "idle"
    GESTURES = "gestures"
    MOUSE = "mouse"
    DRAWING = "drawing"


class HandSide(Enum):
    """Recognized hand-side labels used throughout the application."""

    LEFT = "left"
    RIGHT = "right"
    BOTH = "both"
    ANY = "any"


# =========================================================
# HAND AND FRAME
# =========================================================

@dataclass
class HandLandmarks:
    """One detected hand represented by 21 normalized landmarks."""
    side: HandSide
    points: np.ndarray          # (21, 3), float32
    confidence: float = 1.0


@dataclass
class FrameResult:
    """Detected hands and timestamp for one processed frame."""
    hands: list[HandLandmarks] = field(default_factory=list)
    timestamp: float = 0.0

    @property
    def has_hands(self) -> bool:
        """Return whether this frame contains at least one detected hand."""
        return len(self.hands) > 0

    def get_hand(self, side: HandSide) -> HandLandmarks | None:
        """Find the detected hand with the requested side.

        Args:
            side: Hand side to search for.

        Returns:
            The matching hand, or ``None`` when it is absent.
        """
        for h in self.hands:
            if h.side == side:
                return h
        return None


# =========================================================
# RECOGNITION
# =========================================================

@dataclass
class Prediction:
    """Class label, confidence, and timestamp produced by gesture inference."""
    gesture_id: str
    gesture_name: str
    confidence: float
    timestamp: float = 0.0

    def is_confident(self, threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> bool:
        """Return whether the confidence meets the supplied threshold.

        Args:
            threshold: Minimum accepted confidence in the range from 0 to 1.

        Returns:
            ``True`` when this prediction meets or exceeds the threshold.
        """
        return self.confidence >= threshold


# =========================================================
# GESTURE DEFINITION
# =========================================================

ActionType = Literal["media", "key", "system", "mouse", "custom"]
GestureType = Literal["static", "dynamic"]


@dataclass
class GestureAction:
    """Action type and parameters associated with a gesture."""
    type: ActionType
    payload: dict


@dataclass
class GestureDefinition:
    """Normalized gesture metadata loaded from the gesture registry."""
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
# TRAINING
# =========================================================

@dataclass
class TrainingSample:
    """One labeled training example containing the flattened hand features."""
    gesture_id: str
    features: np.ndarray        # (126,), float32
    timestamp: float = 0.0


@dataclass
class ModelMetrics:
    """Training and evaluation metrics for a gesture-classification model."""
    model_name: str
    accuracy: float
    train_time_sec: float
    n_samples: int
    n_classes: int


# =========================================================
# RADIAL MENU
# =========================================================

@dataclass
class RadialSector:
    """Label, action, and enabled state for one radial-menu sector."""
    index: int
    icon: str = "empty"
    label: str = ""
    action: GestureAction | None = None
    enabled: bool = False


# =========================================================
# SETTINGS
# =========================================================

@dataclass
class AppSettings:
    """Application preferences persisted in ``settings.json``."""
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