from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID

import redis.asyncio as redis

from app.core import config

ADMISSION_NAMESPACE = "atlas:telemetry:admission:v1"
MAX_EVENTS_PER_WINDOW = 120
WINDOW_TTL_SECONDS = 125


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


def client_scope(*, user_id: UUID | None, playback_session_id: UUID) -> str:
    if user_id is not None:
        return f"user:{user_id}"
    return f"session:{playback_session_id}"


def admission_key(*, video_id: UUID, scope: str, now: datetime | None = None) -> str:
    bucket = (now or utc_now()).astimezone(timezone.utc).strftime("%Y%m%d%H%M")
    return f"{ADMISSION_NAMESPACE}:{scope}:{video_id}:{bucket}"


async def admit_playback_event(
    *,
    video_id: UUID,
    user_id: UUID | None,
    playback_session_id: UUID,
    now: datetime | None = None,
    redis_factory: Callable[[], redis.Redis] | None = None,
) -> None:
    key = admission_key(video_id=video_id, scope=client_scope(user_id=user_id, playback_session_id=playback_session_id), now=now)
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
