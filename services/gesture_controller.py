import time
import joblib
import numpy as np
from PySide6.QtCore import QObject, Signal, Slot
from core.hand_tracker import HandTracker
from core.slots import HandSlots
from core.types import MODELS_DIR

class GestureController(QObject):
    """Legacy frame processor that emits detected hands and model predictions."""

    processed_frame = Signal(object, object, object)

    def __init__(self):
        """Initialize the hand tracker, slot manager, and optional trained model."""
        super().__init__()
        self.tracker = HandTracker()
        self.slots = HandSlots(n=2)
        model_path = MODELS_DIR / "gesture_model.joblib"
        self.model = None
        if model_path.exists():
            saved_model = joblib.load(model_path)
            self.model = (
                saved_model["model"] if isinstance(saved_model, dict) else saved_model
            )

    @Slot(object)
    def process_frame(self, frame):
        """Detect hands and emit frame data with optional model predictions.

        Args:
            frame: Camera image in BGR format.

        Returns:
            ``None``; results are emitted through ``processed_frame``.
        """
        result = self.tracker.process(frame)
        
        tracked_hands = {}
        predictions = {} if self.model is not None else None
        if result.has_hands:
            # Collect raw landmark arrays before assigning stable hand slots.
            hands_arrays = [h.points for h in result.hands]
            # Assign slots and smooth each hand's landmarks.
            tracked_dict = self.slots.update(hands_arrays, time.monotonic())
            
            # Convert arrays to Python values before crossing the Qt signal boundary.
            for slot, pts in tracked_dict.items():
                hand_points = [(float(p[0]), float(p[1])) for p in pts]
                tracked_hands[slot] = hand_points
                if self.model is not None:
                    features = np.asarray(hand_points, dtype=np.float32).reshape(1, -1)
                    prediction = str(self.model.predict(features)[0])
                    probabilities = self.model.predict_proba(features)[0]
                    confidence = float(np.max(probabilities))
                    predictions[slot] = (prediction, confidence)
            
        self.processed_frame.emit(frame, tracked_hands, predictions)

    def stop(self):
        """Release the hand-tracking model."""
        self.tracker.close()