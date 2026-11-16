import cv2
import mediapipe as mp
import numpy as np
import time
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from core.types import HandLandmarks, HandSide, FrameResult, HAND_MODEL_PATH

class HandTracker:
    def __init__(self):
        base_options = python.BaseOptions(model_asset_path=str(HAND_MODEL_PATH))
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=0.35, # <--- ЗНИЗИЛИ ДЛЯ ДВОХ РУК
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.detector = vision.HandLandmarker.create_from_options(options)
        self._t0 = time.monotonic()
        self._last_ts = -1

    def process(self, frame: np.ndarray) -> FrameResult:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        
        ts = max(int((time.monotonic() - self._t0) * 1000), self._last_ts + 1)
        self._last_ts = ts
        
        result = self.detector.detect_for_video(mp_image, ts)
        hands = []

        if result.hand_landmarks:
            for i, lm in enumerate(result.hand_landmarks):
                raw_side = result.handedness[i][0].category_name
                actual_side = self._actual_hand_side(raw_side)
                pts = np.array([[p.x, p.y, p.z] for p in lm], dtype=np.float32)
                conf = result.handedness[i][0].score
                hands.append(HandLandmarks(side=actual_side, points=pts, confidence=conf))

        return FrameResult(hands=hands)

    @staticmethod
    def _actual_hand_side(mirrored_side: str) -> HandSide:
        # CameraThread mirrors frames, so MediaPipe's handedness must be flipped back.
        if mirrored_side == "Left":
            return HandSide.RIGHT
        if mirrored_side == "Right":
            return HandSide.LEFT
        raise ValueError(f"Unknown MediaPipe handedness: {mirrored_side}")

    def close(self):
        self.detector.close()