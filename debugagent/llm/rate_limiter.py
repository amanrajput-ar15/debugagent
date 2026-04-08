from __future__ import annotations

import threading
import time


class RateLimiter:
    """Simple fixed-interval limiter for RPM caps."""

    def __init__(self, requests_per_minute: int):
        if requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be > 0")
        self.interval = 60.0 / requests_per_minute
        self._last_request_time = 0.0
        self._lock = threading.Lock()

    def acquire(self, verbose: bool = False) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self.interval:
                sleep_for = self.interval - elapsed
                if verbose:
                    print(f"Waiting for rate limit... {sleep_for:.1f}s")
                time.sleep(sleep_for)
            self._last_request_time = time.monotonic()
