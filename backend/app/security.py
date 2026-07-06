import secrets
import threading
import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request

from app.config import get_settings


class SlidingWindowLimiter:
    def __init__(self):
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, now: float | None = None) -> bool:
        if limit <= 0:
            return True
        now = now if now is not None else time.monotonic()
        cutoff = now - 60
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                return False
            events.append(now)
            return True

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


report_limiter = SlidingWindowLimiter()


def require_officer(
    x_citymind_officer_key: str | None = Header(default=None),
) -> None:
    settings = get_settings()
    expected = settings.officer_api_key
    if not expected:
        if settings.app_env.lower() == "production":
            raise HTTPException(503, "Officer authentication is not configured")
        return
    if not x_citymind_officer_key or not secrets.compare_digest(
        x_citymind_officer_key, expected
    ):
        raise HTTPException(401, "Officer authentication required")


def enforce_report_rate_limit(request: Request) -> None:
    limit = get_settings().report_rate_limit_per_minute
    client = request.client.host if request.client else "unknown"
    if not report_limiter.allow(client, limit):
        raise HTTPException(
            429,
            "Report submission rate limit exceeded",
            headers={"Retry-After": "60"},
        )
