"""A small in-memory sliding-window rate limiter (login, registration, AI features).

Demo-grade only: counts live in this process, so they reset on restart and are
not shared between workers. A production deployment should rate-limit at the
reverse proxy / gateway (or use a shared store) instead.
"""

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        hits = self._hits[key]
        while hits and hits[0] <= now - self.window_seconds:
            hits.popleft()
        return hits

    def retry_after(self, key: str) -> int | None:
        """Seconds to wait if the key is over its limit, otherwise None."""
        with self._lock:
            now = time.monotonic()
            hits = self._prune(key, now)
            if len(hits) < self.max_attempts:
                return None
            return max(1, int(hits[0] + self.window_seconds - now))

    def hit(self, key: str) -> None:
        with self._lock:
            now = time.monotonic()
            self._prune(key, now).append(now)

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)


# Failed logins per email, failed logins per client IP, registrations per client IP.
login_failures_by_email = RateLimiter(max_attempts=5, window_seconds=15 * 60)
login_failures_by_ip = RateLimiter(max_attempts=30, window_seconds=15 * 60)
registrations_by_ip = RateLimiter(max_attempts=10, window_seconds=60 * 60)
# Visual searches run a neural network: 12 per minute per client IP.
visual_searches_by_ip = RateLimiter(max_attempts=12, window_seconds=60)
# Smart Fit photo estimates run a pose model on up to two photos: 10 per 10 minutes per user.
fit_estimates_by_user = RateLimiter(max_attempts=10, window_seconds=10 * 60)


def reset_all() -> None:
    for limiter in (
        login_failures_by_email,
        login_failures_by_ip,
        registrations_by_ip,
        visual_searches_by_ip,
        fit_estimates_by_user,
    ):
        limiter.reset()
