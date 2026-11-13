import time
from PySide6.QtCore import QObject, Signal, Slot
from core.hand_tracker import HandTracker
from core.slots import HandSlots

class GestureController(QObject):
    # Сигнал: (кадр, словник з точками рук {slot_id: pts})
    processed_frame = Signal(object, object)

    def __init__(self):
        super().__init__()
        self.tracker = HandTracker()
        self.slots = HandSlots(n=2)

    @Slot(object)
    def process_frame(self, frame):
        # Обробка кадру (відбувається в окремому потоці)
        result = self.tracker.process(frame)
        
        tracked_hands = {}
        if result.has_hands:
            hands_arrays = [h.points for h in result.hands]
            tracked_hands = self.slots.update(hands_arrays, time.monotonic())
            
        self.processed_frame.emit(frame, tracked_hands)

    def stop(self):
        self.tracker.close()