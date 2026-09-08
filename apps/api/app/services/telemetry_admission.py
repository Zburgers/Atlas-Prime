from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets
import time
from contextvars import ContextVar
from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Response
import redis.asyncio as redis

from app.core import config

logger = logging.getLogger(__name__)

ADMISSION_NAMESPACE = "atlas:telemetry:admission:v1"
IDENTITY_MINT_NAMESPACE = "atlas:telemetry:identity-mint:v1"
MAX_EVENTS_PER_WINDOW = 120
MAX_NEW_ANONYMOUS_CLIENTS_PER_WINDOW = 120
WINDOW_TTL_SECONDS = 125
SESSION_COOKIE_NAME = "atlas_telemetry_session"
SESSION_TTL_SECONDS = 30 * 24 * 60 * 60
_PROCESS_SECRET = secrets.token_bytes(32)
_FALLBACK_WARNED = False
_SESSION_CONTEXT: ContextVar[tuple[str, bool] | None] = ContextVar("atlas_telemetry_session_context", default=None)


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
    """Return a stable anonymous-client token and remember whether this request minted it.

    The signed token is the approved anonymous *client* identity for the
    120-events/minute/client/video budget. A separate server-side identity-mint
    circuit breaker is consumed only when this function has to mint a new
    anonymous identity, so discarding cookies cannot create unbounded write
    capacity while legitimate clients keep independent budgets.
    """
    if cookie_value and verify_session_token(cookie_value):
        _SESSION_CONTEXT.set((cookie_value, False))
        return cookie_value
    token = issue_session_token()
    _SESSION_CONTEXT.set((token, True))
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
    """Derive the approved per-client admission scope.

    Authenticated callers use their verified user id. Anonymous callers use a
    server-signed cookie token; caller-controlled playback/request UUIDs never
    define admission identity. The token itself is not stored in Redis: only a
    one-way digest is used in the short-lived rate-limit key.
    """
    del playback_session_id
    if user_id is not None:
        return f"user:{user_id}"
    if anonymous_session_token is None or not verify_session_token(anonymous_session_token):
        raise TelemetryAdmissionUnavailable("anonymous telemetry session is missing or invalid")
    token_digest = hashlib.sha256(anonymous_session_token.encode()).hexdigest()[:32]
    return f"anon-client:{token_digest}"


def admission_key(*, video_id: UUID, scope: str, now: datetime | None = None) -> str:
    bucket = (now or utc_now()).astimezone(timezone.utc).strftime("%Y%m%d%H%M")
    return f"{ADMISSION_NAMESPACE}:{scope}:{video_id}:{bucket}"


def identity_mint_key(*, video_id: UUID, now: datetime | None = None) -> str:
    bucket = (now or utc_now()).astimezone(timezone.utc).strftime("%Y%m%d%H%M")
    return f"{IDENTITY_MINT_NAMESPACE}:anon:{video_id}:{bucket}"


def _new_anonymous_identity_for_this_request(token: str | None, *, user_id: UUID | None) -> bool:
    if user_id is not None or token is None:
        return False
    context = _SESSION_CONTEXT.get()
    _SESSION_CONTEXT.set(None)
    return context is not None and context[0] == token and context[1]


async def admit_playback_event(
    *,
    video_id: UUID,
    user_id: UUID | None,
    playback_session_id: UUID,
    anonymous_session_token: str | None = None,
    now: datetime | None = None,
    redis_factory: Callable[[], redis.Redis] | None = None,
) -> None:
    client_key = admission_key(
        video_id=video_id,
        scope=client_scope(
            user_id=user_id,
            playback_session_id=playback_session_id,
            anonymous_session_token=anonymous_session_token,
        ),
        now=now,
    )
    minted_anonymous_identity = _new_anonymous_identity_for_this_request(
        anonymous_session_token,
        user_id=user_id,
    )

    client: redis.Redis | None = None
    try:
        client = (redis_factory or redis_client_factory)()
        async with client.pipeline(transaction=True) as pipe:
            pipe.incr(client_key)
            pipe.expire(client_key, WINDOW_TTL_SECONDS)
            if minted_anonymous_identity:
                mint_key = identity_mint_key(video_id=video_id, now=now)
                pipe.incr(mint_key)
                pipe.expire(mint_key, WINDOW_TTL_SECONDS)
            results = await pipe.execute()
        client_count = int(results[0])
        mint_count = int(results[2]) if minted_anonymous_identity else 0
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

    if client_count > MAX_EVENTS_PER_WINDOW:
        raise TelemetryAdmissionLimitExceeded
    if minted_anonymous_identity and mint_count > MAX_NEW_ANONYMOUS_CLIENTS_PER_WINDOW:
        raise TelemetryAdmissionLimitExceeded
