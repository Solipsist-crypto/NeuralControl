import numpy as np
from core.filters import OneEuroFilter

class HandSlots:
    """Associate detected hands with stable slots and smooth their landmarks."""

    def __init__(self, n=2, max_dist=0.3, ttl=0.25):
        """Configure slot count, wrist matching distance, and expiration time.

        Args:
            n: Maximum number of tracked hands.
            max_dist: Maximum normalized wrist distance for retaining a slot.
            ttl: Seconds a missing hand remains assigned to its slot.
        """
        self.n, self.max_dist, self.ttl = n, max_dist, ttl
        self.wrist = [None] * n
        self.seen = [0.0] * n
        self.filters = [OneEuroFilter(mincutoff=1.0, beta=0.05) for _ in range(n)]

    def update(self, hands, t):
        """Match current landmark arrays to slots and smooth each assignment.

        Args:
            hands: Iterable of landmark arrays shaped ``(21, 2)`` or ``(21, 3)``.
            t: Monotonic timestamp in seconds.

        Returns:
            A mapping from slot index to filtered landmark array.
        """
        for s in range(self.n):
            if self.wrist[s] is not None and t - self.seen[s] > self.ttl:
                self.wrist[s] = None
                self.filters[s] = OneEuroFilter(mincutoff=1.0, beta=0.05)

        assigned, used = {}, set()
        
        cands = sorted(
            (float(np.linalg.norm(h[0, :2] - self.wrist[s])), hi, s)
            for hi, h in enumerate(hands)
            for s in range(self.n)
            if self.wrist[s] is not None
        )
        
        for d, hi, s in cands:
            if d < self.max_dist and hi not in assigned and s not in used:
                assigned[hi] = s
                used.add(s)

        for hi in range(len(hands)):
            if hi in assigned: continue
            free = next((s for s in range(self.n) if s not in used), None)
            if free is None: continue
            if self.wrist[free] is not None:
                self.filters[free] = OneEuroFilter(mincutoff=1.0, beta=0.05)
            assigned[hi] = free
            used.add(free)

        out = {}
        for hi, s in assigned.items():
            # Filtering the full landmark array preserves independent XYZ smoothing.
            pts = self.filters[s].filter(hands[hi], t)
                
            self.wrist[s] = pts[0, :2].copy()
            self.seen[s] = t
            out[s] = pts
        return out