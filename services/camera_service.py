import cv2
import time
from PySide6.QtCore import QThread, Signal

class CameraThread(QThread):
    """Capture camera frames on a worker thread and publish them to the UI."""

    frame_ready = Signal(object)

    def __init__(self, camera_index=0):
        """Initialize capture state for the requested camera.

        Args:
            camera_index: OpenCV camera device index.
        """
        super().__init__()
        self.camera_index = camera_index
        self.running = False
        self.cap = None

    def run(self):
        """Open the camera, emit mirrored frames, and release it on exit.

        Returns:
            ``None``; frames are delivered through ``frame_ready``.
        """
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
                frame = cv2.flip(frame, 1)  # Mirror the preview for a natural user-facing view.
                self.frame_ready.emit(frame)
            else:
                time.sleep(0.01)

        if self.cap:
            self.cap.release()

    def stop(self):
        """Request capture shutdown and wait for the worker thread to finish."""
        self.running = False
        self.wait()