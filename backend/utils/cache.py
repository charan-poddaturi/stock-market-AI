"""Lightweight in-memory TTL cache for speeding up repeated computations.

This is a simple, thread-safe cache for API endpoints that are expensive or
rely on external APIs. It is not a replacement for Redis, but it helps reduce
latency under repeated loads (e.g., UI button clicks).

Usage:
    from utils.cache import TTLCache

    cache = TTLCache(ttl_seconds=60, maxsize=256)
    key = ("ticker_info", ticker)
    value = cache.get(key)
    if value is None:
        value = compute_value()
        cache.set(key, value)

"""

import threading
import time
from collections import OrderedDict
from typing import Any, Optional, Tuple


class TTLCache:
    def __init__(self, ttl_seconds: int = 60, maxsize: int = 256):
        self.ttl_seconds = ttl_seconds
        self.maxsize = maxsize
        self._lock = threading.Lock()
        self._cache: "OrderedDict[Tuple, Tuple[float, Any]]" = OrderedDict()

    def get(self, key: Tuple) -> Optional[Any]:
        now = time.time()
        with self._lock:
            if key not in self._cache:
                return None
            ts, value = self._cache.pop(key)
            if now - ts > self.ttl_seconds:
                return None
            # Renew LRU position
            self._cache[key] = (ts, value)
            return value

    def set(self, key: Tuple, value: Any):
        now = time.time()
        with self._lock:
            if key in self._cache:
                self._cache.pop(key)
            self._cache[key] = (now, value)
            # Trim
            while len(self._cache) > self.maxsize:
                self._cache.popitem(last=False)

    def clear(self):
        with self._lock:
            self._cache.clear()
