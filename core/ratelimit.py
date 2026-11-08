"""Sliding-window rate limiter (per key, in memory)."""
import time
from collections import deque


class RateLimiter:
    def __init__(self, max_events, per_seconds, clock=time.monotonic, max_keys=20000):
        self.max_events = max_events
        self.per = per_seconds
        self._clock = clock
        self._hits = {}
        self._max_keys = max_keys
        self._blocked_until = {}

    def allow(self, key):
        """True if the event is allowed. Users who exceed the limit are blocked for `per` seconds."""
        now = self._clock()
        until = self._blocked_until.get(key)
        if until:
            if now < until:
                return False
            del self._blocked_until[key]
            self._hits.pop(key, None)
        q = self._hits.setdefault(key, deque())
        while q and now - q[0] > self.per:
            q.popleft()
        if len(q) >= self.max_events:
            self._blocked_until[key] = now + self.per
            return False
        q.append(now)
        if len(self._hits) > self._max_keys:
            self._gc(now)
        return True

    def _gc(self, now):
        for k in [k for k, q in self._hits.items() if not q or now - q[-1] > self.per]:
            self._hits.pop(k, None)
            self._blocked_until.pop(k, None)
