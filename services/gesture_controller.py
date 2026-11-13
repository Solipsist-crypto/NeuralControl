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
        result = self.tracker.process(frame)
        
        tracked_hands = {}
        if result.has_hands:
            # Отримуємо сирі точки
            hands_arrays = [h.points for h in result.hands]
            # Оновлюємо слоти (фільтруємо)
            tracked_dict = self.slots.update(hands_arrays, time.monotonic())
            
            # Перетворюємо numpy-масиви в звичайні списки, щоб уникнути проблем з пам'яттю в Qt
            for slot, pts in tracked_dict.items():
                tracked_hands[slot] = [(float(p[0]), float(p[1])) for p in pts]
            
        self.processed_frame.emit(frame, tracked_hands)

    def stop(self):
        self.tracker.close()