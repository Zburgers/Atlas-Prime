from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets
import time
from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Response
import redis.asyncio as redis

from app.core import config

logger = logging.getLogger(__name__)

ADMISSION_NAMESPACE = "atlas:telemetry:admission:v1"
MAX_EVENTS_PER_WINDOW = 120
WINDOW_TTL_SECONDS = 125
SESSION_COOKIE_NAME = "atlas_telemetry_session"
SESSION_TTL_SECONDS = 30 * 24 * 60 * 60
ANONYMOUS_SCOPE = "anon"
_PROCESS_SECRET = secrets.token_bytes(32)
_FALLBACK_WARNED = False


class TelemetryAdmissionLimitExceeded(Exception):
    """Raised when a client/video window has reached the approved limit."""


class TelemetryAdmissionUnavailable(Exception):
    """Raised when Redis cannot make an admission decision."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def redis_client_factory() -> redis.Redis:
    return redis.from_url(
        config.celery_broker_url(),
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def issue_session_token(*, now: int | None = None) -> str:
    expires_at = int(now if now is not None else time.time()) + SESSION_TTL_SECONDS
    payload = f"{secrets.token_urlsafe(24)}.{expires_at}"
    return f"{payload}.{_signature(payload)}"


def verify_session_token(token: str, *, now: int | None = None) -> bool:
    try:
        payload, signature = token.rsplit(".", 1)
        nonce, expires_at = payload.rsplit(".", 1)
        if not nonce or int(expires_at) <= int(now if now is not None else time.time()):
            return False
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(signature, _signature(payload))


def ensure_session_token(response: Response, cookie_value: str | None) -> str:
    """Return the valid session cookie or mint a fresh one.

    The minted token is stateless session continuity for deduplication only.
    Anonymous admission NEVER keys on it (see :func:`client_scope`), so
    discarding the cookie cannot mint additional admission budget.
    """
    if cookie_value and verify_session_token(cookie_value):
        return cookie_value
    token = issue_session_token()
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
    )
    return token


def _signing_secret() -> bytes:
    """Stable signing-secret contract for telemetry session cookies.

    A configured ``ATLAS_TELEMETRY_SECRET`` is always preferred so signatures
    agree across restarts and replicas. When unset, local development falls
    back to an ephemeral per-process secret; any other environment fails
    closed so anonymous identities cannot silently reset.
    """
    configured = os.getenv("ATLAS_TELEMETRY_SECRET", "")
    if configured:
        return configured.encode()
    if config.env("APP_ENV", "development") == "development":
        global _FALLBACK_WARNED
        if not _FALLBACK_WARNED:
            logger.warning("sector=G stage=telemetry_session using ephemeral signing secret (development only)")
            _FALLBACK_WARNED = True
        return _PROCESS_SECRET
    raise TelemetryAdmissionUnavailable("telemetry session secret is not configured")


def _signature(payload: str) -> str:
    secret = _signing_secret()
    return base64.urlsafe_b64encode(hmac.new(secret, payload.encode(), hashlib.sha256).digest()).rstrip(b"=").decode()


def client_scope(*, user_id: UUID | None, playback_session_id: UUID, anonymous_session_token: str | None = None) -> str:
    """Derive the admission scope using only server-trusted identity.

    Authenticated callers are scoped by their verified user id. Anonymous
    callers share one constant per-video scope: the admission key already
    binds the server-known video id and server-time window, so no
    client-controlled value (cookie, session UUID, request id) can mint a
    fresh rate-limit bucket by rotation. The session cookie survives only as
    best-effort deduplication continuity, not as admission identity.
    """
    del playback_session_id, anonymous_session_token
    if user_id is not None:
        return f"user:{user_id}"
    return ANONYMOUS_SCOPE


def admission_key(*, video_id: UUID, scope: str, now: datetime | None = None) -> str:
    bucket = (now or utc_now()).astimezone(timezone.utc).strftime("%Y%m%d%H%M")
    return f"{ADMISSION_NAMESPACE}:{scope}:{video_id}:{bucket}"


async def admit_playback_event(
    *,
    video_id: UUID,
    user_id: UUID | None,
    playback_session_id: UUID,
    anonymous_session_token: str | None = None,
    now: datetime | None = None,
    redis_factory: Callable[[], redis.Redis] | None = None,
) -> None:
    key = admission_key(
        video_id=video_id,
        scope=client_scope(
            user_id=user_id,
            playback_session_id=playback_session_id,
            anonymous_session_token=anonymous_session_token,
        ),
        now=now,
    )
    client: redis.Redis | None = None
    try:
        client = (redis_factory or redis_client_factory)()
        async with client.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, WINDOW_TTL_SECONDS)
            results = await pipe.execute()
        count = int(results[0])
    except TelemetryAdmissionLimitExceeded:
        raise
    except Exception as exc:
        raise TelemetryAdmissionUnavailable from exc
    finally:
        if client is not None:
            try:
                await client.aclose()
            except Exception:
                pass

    if count > MAX_EVENTS_PER_WINDOW:
        raise TelemetryAdmissionLimitExceeded
