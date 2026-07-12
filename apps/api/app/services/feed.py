from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Video
from app.domain.ranking import HOME_FEED_ALGORITHM_VERSION, home_feed_reason, home_feed_score
from app.domain.status import VideoPrivacy, VideoStatus

HOME_SURFACE = "home"


@dataclass(frozen=True)
class RankedVideo:
    video: Video
    rank: int
    score: float
    reason: str


async def home_feed(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    request_id: str | None = None,
) -> tuple[str, list[RankedVideo], int]:
    resolved_request_id = request_id or f"{HOME_SURFACE}-{uuid4()}"
    visible = (Video.status == VideoStatus.READY.value) & (Video.privacy == VideoPrivacy.PUBLIC.value)
    total = await session.scalar(select(func.count()).select_from(Video).where(visible))
    result = await session.execute(select(Video).options(selectinload(Video.channel)).where(visible))
    now = datetime.now(timezone.utc)
    scored = [
        (
            home_feed_score(
                view_count=video.view_count,
                like_count=video.like_count,
                created_at=video.created_at,
                now=now,
            ),
            video,
        )
        for video in result.scalars()
    ]
    scored.sort(key=lambda item: (-item[0], item[1].created_at, str(item[1].id)))
    start = (page - 1) * page_size
    end = start + page_size
    ranked = [
        RankedVideo(
            video=video,
            rank=index + 1,
            score=score,
            reason=home_feed_reason(view_count=video.view_count, like_count=video.like_count),
        )
        for index, (score, video) in enumerate(scored)
    ]
    return resolved_request_id, ranked[start:end], int(total or 0)


def home_algorithm_version() -> str:
    return HOME_FEED_ALGORITHM_VERSION
