from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import redis.asyncio as redis

from app.core import config
from app.services.telemetry_retention import retention_cutoff

METRICS_NAMESPACE = "atlas:telemetry:metrics:v1"
METRIC_NAMES = ("accepted", "duplicate", "rate_limited", "purged")
METRICS_TIMEOUT_SECONDS = 1.0

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TelemetryMetricsSnapshot:
    status: Literal["ok", "degraded"]
    accepted_event_count: int | None
    duplicate_event_count: int | None
    rate_limited_event_count: int | None
    purged_event_count: int | None
    retention_cutoff: datetime


def metric_key(metric: str) -> str:
    if metric not in METRIC_NAMES:
        raise ValueError("unknown telemetry metric")
    return f"{METRICS_NAMESPACE}:{metric}"


def redis_client_factory() -> redis.Redis:
    return redis.from_url(
        config.celery_broker_url(),
        decode_responses=True,
        socket_connect_timeout=METRICS_TIMEOUT_SECONDS,
        socket_timeout=METRICS_TIMEOUT_SECONDS,
    )


async def increment_metric(metric: str, amount: int = 1) -> None:
    """Record an aggregate outcome without making it part of correctness."""
    if amount < 0:
        raise ValueError("metric amount cannot be negative")
    if amount == 0:
        return

    client = None
    try:
        client = redis_client_factory()
        await client.incr(metric_key(metric), amount)
    except Exception as exc:  # pragma: no cover - exercised with injected failures
        logger.warning(
            "sector=G stage=telemetry_metric_write metric=%s error=%s",
            metric,
            exc.__class__.__name__,
        )
    finally:
        if client is not None:
            try:
                await client.aclose()
            except Exception as exc:  # pragma: no cover - defensive close path
                logger.warning(
                    "sector=G stage=telemetry_metric_close metric=%s error=%s",
                    metric,
                    exc.__class__.__name__,
                )


async def read_metrics(*, now: datetime | None = None) -> TelemetryMetricsSnapshot:
    current_cutoff = retention_cutoff(now=now or datetime.now(timezone.utc))
    client = None
    try:
        client = redis_client_factory()
        values = await client.mget([metric_key(metric) for metric in METRIC_NAMES])
        counts = [0 if value is None else int(value) for value in values]
        return TelemetryMetricsSnapshot(
            status="ok",
            accepted_event_count=counts[0],
            duplicate_event_count=counts[1],
            rate_limited_event_count=counts[2],
            purged_event_count=counts[3],
            retention_cutoff=current_cutoff,
        )
    except Exception as exc:  # pragma: no cover - exercised with injected failures
        logger.warning(
            "sector=G stage=telemetry_metric_read error=%s",
            exc.__class__.__name__,
        )
        return TelemetryMetricsSnapshot(
            status="degraded",
            accepted_event_count=None,
            duplicate_event_count=None,
            rate_limited_event_count=None,
            purged_event_count=None,
            retention_cutoff=current_cutoff,
        )
    finally:
        if client is not None:
            try:
                await client.aclose()
            except Exception as exc:  # pragma: no cover - defensive close path
                logger.warning("sector=G stage=telemetry_metric_close error=%s", exc.__class__.__name__)
