import cv2
import time
from PySide6.QtCore import QThread, Signal

class CameraThread(QThread):
    # Сигнал передає готовий кадр (numpy масив) в UI
    frame_ready = Signal(object)

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self.running = False
        self.cap = None

    def run(self):
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_MSMF)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)

        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_GAIN, 60)

        self.running = True
        while self.running:
            success, frame = self.cap.read()
            if success:
                frame = cv2.flip(frame, 1) # Дзеркалимо
                self.frame_ready.emit(frame)
            else:
                time.sleep(0.01)

        if self.cap:
            self.cap.release()

    def stop(self):
        self.running = False
        self.wait()