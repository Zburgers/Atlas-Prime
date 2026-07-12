from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import User, Video
from app.domain.ranking import HOME_FEED_ALGORITHM_VERSION, home_feed_reason, home_feed_score
from app.domain.status import VideoPrivacy, VideoStatus
from app.services import recommendation_logging

HOME_SURFACE = "home"


async def home_feed(
    session: AsyncSession,
    *,
    user: User | None,
    page: int,
    page_size: int,
    request_id: str | None = None,
) -> tuple[str, list[recommendation_logging.RecommendationResultItem], int]:
    resolved_request_id = request_id or f"{HOME_SURFACE}-{uuid4()}"
    existing = await recommendation_logging.load_feed_results(
        session,
        request_id=resolved_request_id,
        user=user,
        surface=HOME_SURFACE,
        algorithm_version=HOME_FEED_ALGORITHM_VERSION,
        page=page,
        page_size=page_size,
    )
    if existing is not None:
        ranked_videos, total = existing
        return resolved_request_id, ranked_videos, total
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
        recommendation_logging.RecommendationResultItem(
            video=video,
            rank=index + 1,
            score=score,
            reason=home_feed_reason(view_count=video.view_count, like_count=video.like_count),
        )
        for index, (score, video) in enumerate(scored)
    ]
    paged_ranked = ranked[start:end]
    total_results = int(total or 0)
    await recommendation_logging.persist_feed_results(
        session,
        request_id=resolved_request_id,
        user=user,
        surface=HOME_SURFACE,
        algorithm_version=HOME_FEED_ALGORITHM_VERSION,
        page=page,
        page_size=page_size,
        total_results=total_results,
        results=paged_ranked,
    )
    return resolved_request_id, paged_ranked, total_results


def home_algorithm_version() -> str:
    return HOME_FEED_ALGORITHM_VERSION
