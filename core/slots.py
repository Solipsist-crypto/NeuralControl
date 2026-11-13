import numpy as np
from core.filters import OneEuroFilter

class HandSlots:
    def __init__(self, n=2, max_dist=0.3, ttl=0.25):
        self.n, self.max_dist, self.ttl = n, max_dist, ttl
        self.wrist = [None] * n
        self.seen = [0.0] * n
        self.filters = [OneEuroFilter(mincutoff=1.0, beta=0.05) for _ in range(n)]

    def update(self, hands, t):
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
            # --- ГОЛОВНЕ ВИПРАВЛЕННЯ ---
            # Передаємо одразу весь масив (21, 3) у фільтр.
            # Фільтр тепер розуміє, що це масив і фільтрує кожну координату окремо.
            pts = self.filters[s].filter(hands[hi], t)
                
            self.wrist[s] = pts[0, :2].copy()
            self.seen[s] = t
            out[s] = pts
        return out