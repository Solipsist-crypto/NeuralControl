import numpy as np
from core.types import HandSide

def extract_126_features(hands) -> np.ndarray | None:
    """
    Бере список рук, повертає масив 126 ознак (63 на ліву + 63 на праву).
    Якщо руки немає - заповнює нулями.
    """
    left_pts = np.zeros(63, dtype=np.float32)
    right_pts = np.zeros(63, dtype=np.float32)

    wrists = []
    for hand in hands:
        if hand.side == HandSide.LEFT:
            wrists.append(hand.points[0])
            left_pts = hand.points.flatten()
        elif hand.side == HandSide.RIGHT:
            wrists.append(hand.points[0])
            right_pts = hand.points.flatten()

    if not wrists:
        return None

    # Центруємо відносно зап'ясть (щоб рух по екрану не ламав модель)
    origin = np.mean(wrists, axis=0)
    
    if np.any(left_pts):
        left_pts = (left_pts.reshape(21, 3) - origin).flatten()
    if np.any(right_pts):
        right_pts = (right_pts.reshape(21, 3) - origin).flatten()

    # Нормалізація масштабу (щоб відстань до камери не ламала модель)
    all_pts = np.concatenate([left_pts, right_pts]).reshape(-1, 3)
    max_dist = np.max(np.linalg.norm(all_pts, axis=1)) if np.any(all_pts) else 1.0
    scale = max(max_dist, 1e-6)

    return np.concatenate([left_pts / scale, right_pts / scale])