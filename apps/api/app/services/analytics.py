from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CreatorDailyMetric, User, Video, VideoDailyMetric, VideoImpression, VideoView
from app.domain.events import VIEW_COUNT_THRESHOLD_SECONDS
from app.schemas.analytics import AnalyticsDailyPoint, AnalyticsTopVideo, AnalyticsTotals, StudioAnalyticsResponse
from app.schemas.videos import VideoImpressionCreate, VideoViewCreate, VideoViewResponse
from app.services import videos as video_service


@dataclass(frozen=True)
class AnalyticsRebuildResult:
    date_from: date
    date_to: date
    video_metric_rows: int
    creator_metric_rows: int


async def record_impression(
    session: AsyncSession,
    user: User | None,
    video_id: UUID,
    payload: VideoImpressionCreate,
) -> VideoImpression:
    video = await video_service.get_video_for_read(session, user, video_id)
    impression = VideoImpression(
        user_id=getattr(user, "id", None),
        video_id=video.id,
        surface=payload.surface,
        position=payload.position,
        request_id=payload.request_id,
    )
    video.impression_count += 1
    session.add(impression)
    await session.commit()
    await session.refresh(impression)
    return impression


async def record_view(
    session: AsyncSession,
    user: User | None,
    video_id: UUID,
    payload: VideoViewCreate,
    response: Response,
) -> VideoViewResponse:
    video = await video_service.get_video_for_read(session, user, video_id)
    if payload.position_seconds < VIEW_COUNT_THRESHOLD_SECONDS:
        response.status_code = status.HTTP_202_ACCEPTED
        return VideoViewResponse(
            video_id=video.id,
            counted=False,
            view_count=video.view_count,
            threshold_seconds=VIEW_COUNT_THRESHOLD_SECONDS,
        )

    existing = await session.scalar(
        select(VideoView)
        .where(VideoView.video_id == video.id, VideoView.session_id == payload.session_id)
        .limit(1)
    )
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return VideoViewResponse(
            video_id=video.id,
            counted=False,
            view_count=video.view_count,
            threshold_seconds=VIEW_COUNT_THRESHOLD_SECONDS,
        )

    view = VideoView(
        user_id=getattr(user, "id", None),
        video_id=video.id,
        session_id=payload.session_id,
        position_seconds=payload.position_seconds,
        request_id=payload.request_id,
    )
    video.view_count += 1
    session.add(view)
    await session.commit()
    response.status_code = status.HTTP_201_CREATED
    return VideoViewResponse(
        video_id=video.id,
        counted=True,
        view_count=video.view_count,
        threshold_seconds=VIEW_COUNT_THRESHOLD_SECONDS,
    )


async def rebuild_daily_metrics(
    session: AsyncSession,
    *,
    date_from: date,
    date_to: date,
) -> AnalyticsRebuildResult:
    if date_from > date_to:
        raise ValueError("date_from must not be after date_to")

    video_metrics: dict[tuple[date, UUID, UUID], dict[str, Decimal | int]] = defaultdict(
        lambda: {"impressions": 0, "views": 0, "watch_time_seconds": Decimal("0")}
    )
    impressions = await session.execute(
        select(VideoImpression, Video.owner_id).join(Video, Video.id == VideoImpression.video_id)
    )
    for impression, owner_id in impressions.all():
        metric_date = _metric_date(impression.created_at)
        if date_from <= metric_date <= date_to:
            video_metrics[(metric_date, impression.video_id, owner_id)]["impressions"] += 1

    views = await session.execute(select(VideoView, Video.owner_id).join(Video, Video.id == VideoView.video_id))
    for view, owner_id in views.all():
        metric_date = _metric_date(view.created_at)
        if date_from <= metric_date <= date_to:
            aggregate = video_metrics[(metric_date, view.video_id, owner_id)]
            aggregate["views"] += 1
            aggregate["watch_time_seconds"] += Decimal(view.position_seconds)

    creator_metrics: dict[tuple[date, UUID], dict[str, Decimal | int]] = defaultdict(
        lambda: {"impressions": 0, "views": 0, "watch_time_seconds": Decimal("0")}
    )
    for (metric_date, _video_id, owner_id), aggregate in video_metrics.items():
        creator = creator_metrics[(metric_date, owner_id)]
        creator["impressions"] += aggregate["impressions"]
        creator["views"] += aggregate["views"]
        creator["watch_time_seconds"] += aggregate["watch_time_seconds"]

    await session.execute(delete(VideoDailyMetric).where(VideoDailyMetric.metric_date.between(date_from, date_to)))
    await session.execute(delete(CreatorDailyMetric).where(CreatorDailyMetric.metric_date.between(date_from, date_to)))
    session.add_all(
        [
            VideoDailyMetric(
                metric_date=metric_date,
                video_id=video_id,
                owner_id=owner_id,
                impressions=int(aggregate["impressions"]),
                views=int(aggregate["views"]),
                watch_time_seconds=Decimal(aggregate["watch_time_seconds"]),
            )
            for (metric_date, video_id, owner_id), aggregate in video_metrics.items()
        ]
    )
    session.add_all(
        [
            CreatorDailyMetric(
                metric_date=metric_date,
                owner_id=owner_id,
                impressions=int(aggregate["impressions"]),
                views=int(aggregate["views"]),
                watch_time_seconds=Decimal(aggregate["watch_time_seconds"]),
            )
            for (metric_date, owner_id), aggregate in creator_metrics.items()
        ]
    )
    await session.commit()
    return AnalyticsRebuildResult(
        date_from=date_from,
        date_to=date_to,
        video_metric_rows=len(video_metrics),
        creator_metric_rows=len(creator_metrics),
    )


async def studio_analytics(session: AsyncSession, user: User, *, days: int) -> StudioAnalyticsResponse:
    date_to = date.today()
    date_from = date_to - timedelta(days=days - 1)
    result = await session.execute(
        select(CreatorDailyMetric)
        .where(
            CreatorDailyMetric.owner_id == user.id,
            CreatorDailyMetric.metric_date.between(date_from, date_to),
        )
        .order_by(CreatorDailyMetric.metric_date)
    )
    by_date = {metric.metric_date: metric for metric in result.scalars()}
    daily = [
        AnalyticsDailyPoint(
            date=metric_date,
            impressions=by_date.get(metric_date).impressions if metric_date in by_date else 0,
            views=by_date.get(metric_date).views if metric_date in by_date else 0,
            watch_time_seconds=by_date.get(metric_date).watch_time_seconds if metric_date in by_date else Decimal("0"),
        )
        for metric_date in (date_from + timedelta(days=offset) for offset in range(days))
    ]
    totals = AnalyticsTotals(
        impressions=sum(point.impressions for point in daily),
        views=sum(point.views for point in daily),
        watch_time_seconds=sum((point.watch_time_seconds for point in daily), Decimal("0")),
    )
    top_rows = await session.execute(
        select(
            VideoDailyMetric.video_id,
            Video.title,
            func.sum(VideoDailyMetric.impressions).label("impressions"),
            func.sum(VideoDailyMetric.views).label("views"),
            func.sum(VideoDailyMetric.watch_time_seconds).label("watch_time_seconds"),
        )
        .join(Video, Video.id == VideoDailyMetric.video_id)
        .where(
            VideoDailyMetric.owner_id == user.id,
            VideoDailyMetric.metric_date.between(date_from, date_to),
        )
        .group_by(VideoDailyMetric.video_id, Video.title)
        .order_by(func.sum(VideoDailyMetric.views).desc(), func.sum(VideoDailyMetric.watch_time_seconds).desc(), Video.title)
        .limit(10)
    )
    top_videos = [
        AnalyticsTopVideo(
            video_id=video_id,
            title=title,
            impressions=int(impressions or 0),
            views=int(views or 0),
            watch_time_seconds=Decimal(watch_time_seconds or 0),
        )
        for video_id, title, impressions, views, watch_time_seconds in top_rows.all()
    ]
    return StudioAnalyticsResponse(
        date_from=date_from,
        date_to=date_to,
        totals=totals,
        daily=daily,
        top_videos=top_videos,
    )


def _metric_date(timestamp: datetime) -> date:
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc).date()
    return timestamp.astimezone(timezone.utc).date()
