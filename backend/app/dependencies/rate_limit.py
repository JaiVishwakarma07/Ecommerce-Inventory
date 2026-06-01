from collections import deque
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    def __init__(
        self,
        max_requests: int,
        window_seconds: int,
        detail: str = "Too many registration attempts",
    ) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._detail = detail
        self._requests_by_key: dict[str, deque[datetime]] = {}

    def check(self, key: str) -> None:
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=self._window_seconds)
        timestamps = self._requests_by_key.setdefault(key, deque())

        while timestamps and timestamps[0] < window_start:
            timestamps.popleft()

        if len(timestamps) >= self._max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=self._detail,
            )
        timestamps.append(now)

    def reset(self) -> None:
        self._requests_by_key.clear()


register_rate_limiter = InMemoryRateLimiter(max_requests=5, window_seconds=60)
login_rate_limiter = InMemoryRateLimiter(
    max_requests=5,
    window_seconds=60,
    detail="Too many login attempts",
)
assistant_rate_limiter = InMemoryRateLimiter(
    max_requests=10,
    window_seconds=60,
    detail="Rate limit exceeded",
)


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def enforce_register_rate_limit(request: Request) -> None:
    client_host = _get_client_ip(request)
    register_rate_limiter.check(client_host)


def enforce_login_rate_limit(request: Request) -> None:
    client_host = _get_client_ip(request)
    login_rate_limiter.check(client_host)


def enforce_assistant_rate_limit(user_id: int) -> None:
    assistant_rate_limiter.check(str(user_id))
