import hashlib
import time
from collections import OrderedDict, deque
from threading import Lock

from fastapi import HTTPException, Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import error_response


class RateLimiter:
    """Bounded process-local protection for the single-instance deployment profile."""

    def __init__(self, max_keys: int = 10000) -> None:
        self.buckets: OrderedDict[str, deque[float]] = OrderedDict()
        self.max_keys = max_keys
        self.lock = Lock()

    def allow(self, identity: str, limit: int) -> bool:
        key = hashlib.sha256(identity.encode()).hexdigest()
        now = time.monotonic()
        with self.lock:
            attempts = self.buckets.pop(key, deque())
            while attempts and now - attempts[0] >= 60:
                attempts.popleft()
            allowed = len(attempts) < limit
            if allowed:
                attempts.append(now)
            self.buckets[key] = attempts
            while len(self.buckets) > self.max_keys:
                self.buckets.popitem(last=False)
            return allowed


def limit_identity(request: Request, identity: str) -> None:
    if not request.app.state.auth_limiter.allow(
        "identity:" + identity, request.app.state.settings.auth_identity_rate_limit
    ):
        raise HTTPException(
            429, "Too many attempts. Please wait one minute.", headers={"Retry-After": "60"}
        )


class BodyLimitMiddleware:
    """Limit actual streamed bytes as well as the declared content length."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        limit = 16 * 1024 if path.startswith("/api/v1/auth/") else 12 * 1024 * 1024
        headers = dict(scope.get("headers", []))
        if b"content-length" in headers:
            try:
                length = int(headers[b"content-length"])
            except ValueError:
                length = -1
            if length < 0:
                await error_response(400, "INVALID_REQUEST", "Invalid request size.")(
                    scope, receive, send
                )
                return
            if length > limit:
                await error_response(413, "REQUEST_TOO_LARGE", "The request is too large.")(
                    scope, receive, send
                )
                return
        consumed = 0

        async def bounded_receive() -> Message:
            nonlocal consumed
            message = await receive()
            if message["type"] == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > limit:
                    raise HTTPException(413, "The request is too large.")
            return message

        await self.app(scope, bounded_receive, send)
