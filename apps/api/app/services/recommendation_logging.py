from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import PlaybackEvent, RecommendationRequest, RecommendationResult, User, Video, VideoImpression, VideoView
from app.domain.status import ModerationStatus, VideoPrivacy, VideoStatus


@dataclass(frozen=True)
class RecommendationResultItem:
    video: Video
    rank: int
    score: float
    reason: str


@dataclass(frozen=True)
class RecommendationDebugResult:
    video_id: UUID
    rank: int
    score: float
    reason: str
    impression_count: int
    playback_event_count: int
    view_count: int


@dataclass(frozen=True)
class RecommendationDebug:
    request_id: str
    surface: str
    algorithm_version: str
    page: int
    page_size: int
    total_results: int
    results: list[RecommendationDebugResult]


async def recent_recommendation_requests(session: AsyncSession, *, limit: int) -> list[RecommendationRequest]:
    result = await session.execute(select(RecommendationRequest).order_by(RecommendationRequest.created_at.desc()).limit(limit))
    return list(result.scalars())


async def admin_recommendation_debug(session: AsyncSession, *, request_id: str) -> RecommendationDebug:
    recommendation_request = await session.scalar(select(RecommendationRequest).where(RecommendationRequest.request_id == request_id))
    if recommendation_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "NotFound", "message": "Feed request not found"})
    return await _recommendation_debug(session, recommendation_request)


async def load_feed_results(
    session: AsyncSession,
    *,
    request_id: str,
    user: User | None,
    surface: str,
    algorithm_version: str,
    page: int,
    page_size: int,
) -> tuple[list[RecommendationResultItem], int] | None:
    recommendation_request = await session.scalar(
        select(RecommendationRequest).where(RecommendationRequest.request_id == request_id)
    )
    if recommendation_request is None:
        return None
    if recommendation_request.user_id != getattr(user, "id", None):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "NotFound", "message": "Feed request not found"})
    if (
        recommendation_request.surface != surface
        or recommendation_request.algorithm_version != algorithm_version
        or recommendation_request.page != page
        or recommendation_request.page_size != page_size
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "Conflict", "message": "Feed request ID was already used with different parameters"},
        )
    result = await session.execute(
        select(RecommendationResult)
        .join(Video, Video.id == RecommendationResult.video_id)
        .options(selectinload(RecommendationResult.video).selectinload(Video.channel))
        .where(
            RecommendationResult.recommendation_request_id == recommendation_request.id,
            Video.status == VideoStatus.READY.value,
            Video.privacy == VideoPrivacy.PUBLIC.value,
            Video.moderation_status == ModerationStatus.APPROVED.value,
        )
        .order_by(RecommendationResult.rank)
    )
    total = await session.scalar(
        select(func.count())
        .select_from(Video)
        .where(
            Video.status == VideoStatus.READY.value,
            Video.privacy == VideoPrivacy.PUBLIC.value,
            Video.moderation_status == ModerationStatus.APPROVED.value,
        )
    )
    return (
        [
            RecommendationResultItem(
                video=item.video,
                rank=item.rank,
                score=float(item.score),
                reason=item.reason,
            )
            for item in result.scalars()
        ],
        int(total or 0),
    )


async def persist_feed_results(
    session: AsyncSession,
    *,
    request_id: str,
    user: User | None,
    surface: str,
    algorithm_version: str,
    page: int,
    page_size: int,
    total_results: int,
    results: list[RecommendationResultItem],
) -> None:
    recommendation_request = RecommendationRequest(
        request_id=request_id,
        user_id=getattr(user, "id", None),
        surface=surface,
        algorithm_version=algorithm_version,
        page=page,
        page_size=page_size,
        total_results=total_results,
    )
    session.add(recommendation_request)
    await session.flush()
    session.add_all(
        [
            RecommendationResult(
                recommendation_request_id=recommendation_request.id,
                video_id=item.video.id,
                rank=item.rank,
                score=item.score,
                reason=item.reason,
            )
            for item in results
        ]
    )
    await session.commit()


async def recommendation_debug(session: AsyncSession, *, request_id: str, user: User) -> RecommendationDebug:
    recommendation_request = await session.scalar(
        select(RecommendationRequest).where(RecommendationRequest.request_id == request_id)
    )
    if recommendation_request is None or recommendation_request.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "NotFound", "message": "Feed request not found"})
    return await _recommendation_debug(session, recommendation_request)


async def _recommendation_debug(session: AsyncSession, recommendation_request: RecommendationRequest) -> RecommendationDebug:
    result = await session.execute(
        select(RecommendationResult)
        .where(RecommendationResult.recommendation_request_id == recommendation_request.id)
        .order_by(RecommendationResult.rank)
    )
    ranked_results = list(result.scalars())
    video_ids = [item.video_id for item in ranked_results]
    impression_counts = await _event_counts(session, VideoImpression, recommendation_request.request_id, video_ids)
    playback_counts = await _event_counts(session, PlaybackEvent, recommendation_request.request_id, video_ids)
    view_counts = await _event_counts(session, VideoView, recommendation_request.request_id, video_ids)
    return RecommendationDebug(
        request_id=recommendation_request.request_id,
        surface=recommendation_request.surface,
        algorithm_version=recommendation_request.algorithm_version,
        page=recommendation_request.page,
        page_size=recommendation_request.page_size,
        total_results=recommendation_request.total_results,
        results=[
            RecommendationDebugResult(
                video_id=item.video_id,
                rank=item.rank,
                score=float(item.score),
                reason=item.reason,
                impression_count=impression_counts.get(item.video_id, 0),
                playback_event_count=playback_counts.get(item.video_id, 0),
                view_count=view_counts.get(item.video_id, 0),
            )
            for item in ranked_results
        ],
    )


async def _event_counts(
    session: AsyncSession,
    model: type[VideoImpression] | type[PlaybackEvent] | type[VideoView],
    request_id: str,
    video_ids: list[UUID],
) -> dict[UUID, int]:
    if not video_ids:
        return {}
    result = await session.execute(
        select(model.video_id, func.count(model.id))
        .where(model.request_id == request_id, model.video_id.in_(video_ids))
        .group_by(model.video_id)
    )
    return {video_id: int(count) for video_id, count in result.all()}
