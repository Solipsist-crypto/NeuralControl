import os
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
import cv2
import time
import numpy as np

from core.hand_tracker import HandTracker
from core.slots import HandSlots

def interpolate_points(p1, p2, num=2):
    pts = []
    for i in range(1, num + 1):
        t = i / (num + 1)
        x = p1[0] + (p2[0] - p1[0]) * t
        y = p1[1] + (p2[1] - p1[1]) * t
        pts.append((x, y))
    return pts

def main():
    print("Запуск тесту камери...")
    tracker = HandTracker()
    slots = HandSlots(n=2)
    
    cap = cv2.VideoCapture(0, cv2.CAP_MSMF)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    # --- ПОВЕРТАЄМО НОРМАЛЬНУ ЕКСПОЗИЦІЮ ---
    # Не чіпаємо Auto Exposure, але виставляємо середній Gain
    cap.set(cv2.CAP_PROP_GAIN, 60) 

    p_time = 0
    mode = 2 # Голограма

    while True:
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)
        
        # --- ШТУЧНЕ ОСВІТЛЕННЯ (Щоб MediaPipe бачив руку в темряві) ---
        # 1. Переводимо в LAB
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # 2. Сильно підсилюємо світло (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        cl = clahe.apply(l)
        
        # 3. Збираємо назад
        frame_enhanced = cv2.cvtColor(cv2.merge((cl, a, b)), cv2.COLOR_LAB2BGR)

        # Передаємо ОСВІТЛЕНЕ зображення в MediaPipe
        result = tracker.process(frame_enhanced)
        
        # Для відображення
        display_frame = np.zeros_like(frame) if mode == 2 else frame_enhanced.copy()

        if result.has_hands and mode != 3:
            hands_arrays = [h.points for h in result.hands]
            tracked_hands = slots.update(hands_arrays, time.monotonic())

            for slot_id, pts in tracked_hands.items():
                connections = [
                    (0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),
                    (5,9),(9,10),(10,11),(11,12),(9,13),(13,14),(14,15),(15,16),
                    (13,17),(17,18),(18,19),(19,20),(0,17)
                ]
                
                line_color = (255, 255, 0) if mode == 2 else (124, 58, 237)
                dot_color = (255, 0, 255) if mode == 2 else (0, 212, 255)
                thick = 3
                radius = 5

                for connection in connections:
                    pt1, pt2 = pts[connection[0]], pts[connection[1]]
                    
                    cx1, cy1 = int(pt1[0] * frame.shape[1]), int(pt1[1] * frame.shape[0])
                    cx2, cy2 = int(pt2[0] * frame.shape[1]), int(pt2[1] * frame.shape[0])
                    cv2.line(display_frame, (cx1, cy1), (cx2, cy2), line_color, thick, cv2.LINE_AA)

                    # Проміжні точки
                    inter_pts = interpolate_points((pt1[0], pt1[1]), (pt2[0], pt2[1]), num=2)
                    for ix, iy in inter_pts:
                        cx, cy = int(ix * frame.shape[1]), int(iy * frame.shape[0])
                        cv2.circle(display_frame, (cx, cy), 3, dot_color, -1, cv2.LINE_AA)

                for pt in pts:
                    cx, cy = int(pt[0] * frame.shape[1]), int(pt[1] * frame.shape[0])
                    cv2.circle(display_frame, (cx, cy), radius, dot_color, -1, cv2.LINE_AA)
                
        c_time = time.time()
        fps = 1 / (c_time - p_time) if p_time > 0 else 0
        p_time = c_time
        
        cv2.putText(display_frame, f"FPS: {int(fps)} | Mode: {mode}", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 136), 2)

        cv2.imshow("NeuralControl - Core Test", display_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'): break
        elif key == ord('1'): mode = 1
        elif key == ord('2'): mode = 2
        elif key == ord('3'): mode = 3

    cap.release()
    cv2.destroyAllWindows()
    tracker.close()

if __name__ == "__main__":
    main()