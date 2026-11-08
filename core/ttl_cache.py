"""Small in-memory dict with expiry + size cap (replaces the unbounded temp.* dicts)."""
import time
from collections import OrderedDict
from collections.abc import MutableMapping


class TTLDict(MutableMapping):
    """Dict-like cache: entries expire after `ttl` seconds and the oldest entries
    are dropped once `maxsize` is exceeded. Reads refresh nothing (plain TTL)."""

    def __init__(self, ttl=3600, maxsize=5000, clock=time.monotonic):
        self.ttl = ttl
        self.maxsize = maxsize
        self._clock = clock
        self._data = OrderedDict()  # key -> (expires_at, value)

    def _purge(self):
        now = self._clock()
        # entries are inserted in time order, so expired ones are at the front
        while self._data:
            key, (exp, _) = next(iter(self._data.items()))
            if exp > now:
                break
            del self._data[key]

    def __setitem__(self, key, value):
        self._data.pop(key, None)
        self._data[key] = (self._clock() + self.ttl, value)
        self._purge()
        while len(self._data) > self.maxsize:
            self._data.popitem(last=False)

    def __getitem__(self, key):
        item = self._data.get(key)
        if item is None:
            raise KeyError(key)
        if item[0] <= self._clock():
            del self._data[key]
            raise KeyError(key)
        return item[1]

    def __delitem__(self, key):
        if key not in self._data:
            raise KeyError(key)
        del self._data[key]

    def __iter__(self):
        self._purge()
        return iter(list(self._data.keys()))

    def __len__(self):
        self._purge()
        return len(self._data)

    def __contains__(self, key):
        try:
            self[key]
            return True
        except KeyError:
            return False
