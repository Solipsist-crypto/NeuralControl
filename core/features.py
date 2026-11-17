import numpy as np
from core.types import HandSide

def extract_126_features(hands) -> np.ndarray | None:
    """Pack detected hands into the model's 126-coordinate feature vector.

    Args:
        hands: Detected hand landmarks, each containing a side and 21 points.

    Returns:
        A 126-element vector ordered as left hand then right hand, or ``None``
        when no hands are present.
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

    # Center both hands on their wrist origin to reduce sensitivity to position.
    origin = np.mean(wrists, axis=0)
    
    if np.any(left_pts):
        left_pts = (left_pts.reshape(21, 3) - origin).flatten()
    if np.any(right_pts):
        right_pts = (right_pts.reshape(21, 3) - origin).flatten()

    # Normalize by the largest centered landmark distance to reduce scale variance.
    all_pts = np.concatenate([left_pts, right_pts]).reshape(-1, 3)
    max_dist = np.max(np.linalg.norm(all_pts, axis=1)) if np.any(all_pts) else 1.0
    scale = max(max_dist, 1e-6)

    return np.concatenate([left_pts / scale, right_pts / scale])