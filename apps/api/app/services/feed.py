from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import User, Video
from app.domain.ranking import (
    HOME_FEED_ALGORITHM_VERSION,
    RELATED_ALGORITHM_VERSION,
    TRENDING_ALGORITHM_VERSION,
    home_feed_reason,
    home_feed_score,
    related_feed_score,
    trending_feed_score,
)
from app.domain.status import ModerationStatus, VideoPrivacy, VideoStatus
from app.services import recommendation_logging
from app.services import videos as video_service

HOME_SURFACE = "home"
RELATED_SURFACE = "related"
TRENDING_SURFACE = "trending"


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
    visible = (
        (Video.status == VideoStatus.READY.value)
        & (Video.privacy == VideoPrivacy.PUBLIC.value)
        & (Video.moderation_status == ModerationStatus.APPROVED.value)
    )
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


async def trending_feed(
    session: AsyncSession,
    *,
    user: User | None,
    page: int,
    page_size: int,
    request_id: str | None = None,
) -> tuple[str, list[recommendation_logging.RecommendationResultItem], int]:
    return await _ranked_public_feed(
        session,
        user=user,
        page=page,
        page_size=page_size,
        request_id=request_id,
        surface=TRENDING_SURFACE,
        algorithm_version=TRENDING_ALGORITHM_VERSION,
        reason_for=lambda _video: "trending public video",
        score_for=lambda video, now: trending_feed_score(
            view_count=video.view_count,
            like_count=video.like_count,
            created_at=video.created_at,
            now=now,
        ),
    )


async def related_videos(
    session: AsyncSession,
    *,
    user: User | None,
    video_id: UUID,
    page: int,
    page_size: int,
    request_id: str | None = None,
) -> tuple[str, list[recommendation_logging.RecommendationResultItem], int]:
    current_video = await video_service.get_video_for_read(session, user, video_id)
    return await _ranked_public_feed(
        session,
        user=user,
        page=page,
        page_size=page_size,
        request_id=request_id,
        surface=RELATED_SURFACE,
        algorithm_version=RELATED_ALGORITHM_VERSION,
        excluded_video_id=current_video.id,
        reason_for=lambda video: "same channel public video" if video.channel_id == current_video.channel_id else "related public video",
        score_for=lambda video, now: related_feed_score(
            view_count=video.view_count,
            like_count=video.like_count,
            created_at=video.created_at,
            same_channel=video.channel_id == current_video.channel_id,
            now=now,
        ),
    )


async def _ranked_public_feed(
    session: AsyncSession,
    *,
    user: User | None,
    page: int,
    page_size: int,
    request_id: str | None,
    surface: str,
    algorithm_version: str,
    reason_for: Callable[[Video], str],
    score_for: Callable[[Video, datetime], float],
    excluded_video_id: UUID | None = None,
) -> tuple[str, list[recommendation_logging.RecommendationResultItem], int]:
    resolved_request_id = request_id or f"{surface}-{uuid4()}"
    existing = await recommendation_logging.load_feed_results(
        session,
        request_id=resolved_request_id,
        user=user,
        surface=surface,
        algorithm_version=algorithm_version,
        page=page,
        page_size=page_size,
    )
    if existing is not None:
        ranked_videos, total = existing
        return resolved_request_id, ranked_videos, total
    visible = (
        (Video.status == VideoStatus.READY.value)
        & (Video.privacy == VideoPrivacy.PUBLIC.value)
        & (Video.moderation_status == ModerationStatus.APPROVED.value)
    )
    if excluded_video_id is not None:
        visible &= Video.id != excluded_video_id
    total = await session.scalar(select(func.count()).select_from(Video).where(visible))
    result = await session.execute(select(Video).options(selectinload(Video.channel)).where(visible))
    now = datetime.now(timezone.utc)
    scored = [(score_for(video, now), video) for video in result.scalars()]
    scored.sort(key=lambda item: (-item[0], item[1].created_at, str(item[1].id)))
    start = (page - 1) * page_size
    end = start + page_size
    ranked = [
        recommendation_logging.RecommendationResultItem(
            video=video,
            rank=index + 1,
            score=score,
            reason=reason_for(video),
        )
        for index, (score, video) in enumerate(scored)
    ]
    paged_ranked = ranked[start:end]
    total_results = int(total or 0)
    await recommendation_logging.persist_feed_results(
        session,
        request_id=resolved_request_id,
        user=user,
        surface=surface,
        algorithm_version=algorithm_version,
        page=page,
        page_size=page_size,
        total_results=total_results,
        results=paged_ranked,
    )
    return resolved_request_id, paged_ranked, total_results
