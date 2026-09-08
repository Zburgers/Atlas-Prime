from __future__ import annotations

import math
from datetime import datetime, timezone

HOME_FEED_ALGORITHM_VERSION = "home-v1"
RELATED_ALGORITHM_VERSION = "related-v1"
TRENDING_ALGORITHM_VERSION = "trending-v1"


def home_feed_score(*, view_count: int, like_count: int, created_at: datetime, now: datetime | None = None) -> float:
    now_value = now or datetime.now(timezone.utc)
    created_value = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
    age_hours = max(0.0, (now_value - created_value).total_seconds() / 3600)
    freshness = 80.0 / (1.0 + age_hours / 36.0)
    quality = math.log1p(max(0, view_count)) * 8.0 + math.log1p(max(0, like_count)) * 22.0
    return round(freshness + quality, 6)


def home_feed_reason(*, view_count: int, like_count: int) -> str:
    if like_count > 0 and view_count > 0:
        return "fresh public video with views and likes"
    if like_count > 0:
        return "fresh public video with likes"
    if view_count > 0:
        return "fresh public video with views"
    return "fresh public video"


def trending_feed_score(*, view_count: int, like_count: int, created_at: datetime, now: datetime | None = None) -> float:
    return home_feed_score(view_count=view_count, like_count=like_count, created_at=created_at, now=now)


def related_feed_score(
    *,
    view_count: int,
    like_count: int,
    created_at: datetime,
    same_channel: bool,
    now: datetime | None = None,
) -> float:
    channel_match = 10_000.0 if same_channel else 0.0
    return round(channel_match + home_feed_score(view_count=view_count, like_count=like_count, created_at=created_at, now=now), 6)
