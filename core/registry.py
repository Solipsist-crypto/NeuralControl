import json

from core.types import (
    GESTURE_REGISTRY_JSON,
    GESTURE_TRANSLATIONS,
    GestureAction,
    GestureDefinition,
    HandSide,
)


DYNAMIC_POSES = frozenset(
    {
        "WAVE",
        "SWIPE_LEFT",
        "SWIPE_RIGHT",
        "SWIPE_UP",
        "SWIPE_DOWN",
        "CIRCLE_CW",
        "CIRCLE_CCW",
        "ZOOM_IN",
        "ZOOM_OUT",
        "DRAW_CHECK",
        "DRAW_X",
    }
)

class GestureRegistry:
    def __init__(self):
        self.gestures: dict[str, GestureDefinition] = {}
        self.reload()

    def reload(self):
        self.gestures.clear()
        try:
            entries = json.loads(
                GESTURE_REGISTRY_JSON.read_text(encoding="utf-8")
            )
            if not isinstance(entries, list):
                raise ValueError("Реєстр жестів має містити JSON-масив.")

            for g in entries:
                if not isinstance(g, dict):
                    raise ValueError("Запис жесту має бути JSON-об'єктом.")
                if not g.get("enabled", True):
                    continue

                pose = g["pose"]
                if not isinstance(pose, str) or not pose:
                    raise ValueError("Запис жесту має містити pose.")
                hand = HandSide(str(g.get("hand", "ANY")).lower())
                hold_ms = int(g.get("hold_ms", 500))
                gesture = GestureDefinition(
                    id=pose,
                    name=GESTURE_TRANSLATIONS.get(pose, pose),
                    emoji="🖐️",
                    type="dynamic" if pose in DYNAMIC_POSES else "static",
                    hand=hand,
                    action=GestureAction(type="custom", payload={}),
                    hold_seconds=hold_ms / 1000.0,
                    description="",
                    enabled=g.get("enabled", True),
                )
                self.gestures[gesture.id] = gesture
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
        ) as error:
            print(f"Помилка завантаження реєстру жестів: {error}")

    def get(self, gesture_id: str) -> GestureDefinition | None:
        return self.gestures.get(gesture_id)