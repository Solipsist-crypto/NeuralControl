import json
from core.types import GESTURES_JSON, GestureDefinition, GestureAction, HandSide

class GestureRegistry:
    def __init__(self):
        self.gestures: dict[str, GestureDefinition] = {}
        self.reload()

    def reload(self):
        self.gestures.clear()
        try:
            with open(GESTURES_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            for g in data.get("gestures", []):
                if not g.get("enabled", True):
                    continue
                    
                action = GestureAction(type=g["action"]["type"], payload=g["action"]["payload"])
                gesture = GestureDefinition(
                    id=g["id"],
                    name=g["name"],
                    emoji=g["emoji"],
                    type=g["type"],
                    hand=HandSide(g["hand"]),
                    action=action,
                    hold_seconds=g.get("hold_seconds", 1.0),
                    description=g.get("description", ""),
                    enabled=g["enabled"]
                )
                self.gestures[gesture.id] = gesture
        except Exception as e:
            print(f"Помилка завантаження жестів: {e}")

    def get(self, gesture_id: str) -> GestureDefinition | None:
        return self.gestures.get(gesture_id)