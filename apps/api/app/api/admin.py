from __future__ import annotations

from uuid import UUID

from celery import Celery
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import AdminUserDep, ProcessingQueueDep, SessionDep
from app.db.models import PlaybackEvent, Video, VideoProcessingJob
from app.domain.status import VideoStatus
from app.schemas.feed import RecommendationAdminResponse, RecommendationDebugResponse, RecommendationRequestSummaryResponse
from app.schemas.search import SearchReindexResponse, SearchResponse
from app.schemas.videos import AdminJobResponse, AdminOpsResponse, AdminVideoDebugResponse, RenditionDebugResponse, VideoDebugResponse
from app.services import recommendation_logging, search as search_service
from app.core import config
from app.api.search import _video_list_item

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/recommendations", response_model=RecommendationAdminResponse)
async def recent_recommendations(session: SessionDep, _user: AdminUserDep, limit: int = Query(default=25, ge=1, le=100)) -> RecommendationAdminResponse:
    items = await recommendation_logging.recent_recommendation_requests(session, limit=limit)
    return RecommendationAdminResponse(items=[RecommendationRequestSummaryResponse(request_id=item.request_id, surface=item.surface, algorithm_version=item.algorithm_version, total_results=item.total_results, created_at=item.created_at) for item in items])


@router.get("/recommendations/{request_id}", response_model=RecommendationDebugResponse)
async def recommendation_debug(request_id: str, session: SessionDep, _user: AdminUserDep) -> RecommendationDebugResponse:
    return await recommendation_logging.admin_recommendation_debug(session, request_id=request_id)


@router.get("/search", response_model=SearchResponse)
async def search_debug(session: SessionDep, _user: AdminUserDep, q: str = Query(default="", max_length=120)) -> SearchResponse:
    normalized = search_service.normalize_search_query(q)
    items, total = await search_service.search_public_videos(session, normalized, 1, 100)
    return SearchResponse(query=normalized, items=[_video_list_item(item.video, item.caption_snippet) for item in items], total=total, page=1, page_size=100)


@router.post("/search/reindex", response_model=SearchReindexResponse, status_code=status.HTTP_202_ACCEPTED)
async def reindex_search(_user: AdminUserDep) -> SearchReindexResponse:
    queue = Celery("atlas_api", broker=config.celery_broker_url(), backend=config.celery_result_backend())
    task = queue.send_task("search_worker.rebuild_public_video_index", queue="search")
    return SearchReindexResponse(task_id=str(task.id), queue="search")


@router.get("/ops", response_model=AdminOpsResponse)
async def ops_status(_user: AdminUserDep, processing_queue: ProcessingQueueDep) -> AdminOpsResponse:
    worker = processing_queue.inspect_workers()
    queue = processing_queue.inspect_queue()
    status_value = "ok" if worker.ok and queue.ok else "degraded"
    return AdminOpsResponse(
        status=status_value,
        api={"ok": True, "service": "api"},
        worker={
            "ok": worker.ok,
            "online_workers": worker.online_workers,
            "active_queues": worker.active_queues,
            "error": worker.error,
        },
        redis={
            "ok": queue.ok,
            "media_queue_depth": queue.media_queue_depth,
            "error": queue.error,
        },
    )


@router.get("/videos", response_model=list[VideoDebugResponse])
async def list_admin_videos(
    session: SessionDep,
    _user: AdminUserDep,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Video]:
    result = await session.execute(select(Video).order_by(Video.created_at.desc()).limit(limit))
    return list(result.scalars())


@router.get("/jobs", response_model=list[AdminJobResponse])
async def list_jobs(
    session: SessionDep,
    _user: AdminUserDep,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AdminJobResponse]:
    result = await session.execute(
        select(VideoProcessingJob, Video)
        .join(Video, Video.id == VideoProcessingJob.video_id)
        .order_by(VideoProcessingJob.created_at.desc())
        .limit(limit)
    )
    return [
        AdminJobResponse.model_validate(job).model_copy(
            update={
                "video_title": video.title,
                "video_status": VideoStatus(video.status),
                "video_failure_code": video.failure_code,
                "video_failure_message": video.failure_message,
            }
        )
        for job, video in result.all()
    ]


@router.get("/videos/{video_id}/debug", response_model=AdminVideoDebugResponse)
async def video_debug(video_id: UUID, session: SessionDep, _user: AdminUserDep) -> AdminVideoDebugResponse:
    result = await session.execute(
        select(Video)
        .options(selectinload(Video.renditions), selectinload(Video.processing_jobs))
        .where(Video.id == video_id)
    )
    video = result.scalar_one_or_none()
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NotFound", "message": "Video not found"},
        )
    events_result = await session.execute(
        select(PlaybackEvent)
        .where(PlaybackEvent.video_id == video.id)
        .order_by(PlaybackEvent.created_at.desc())
        .limit(25)
    )
    return AdminVideoDebugResponse(
        video=VideoDebugResponse.model_validate(video),
        renditions=[RenditionDebugResponse.model_validate(rendition) for rendition in video.renditions],
        processing_jobs=sorted(video.processing_jobs, key=lambda job: job.created_at, reverse=True),
        recent_playback_events=list(events_result.scalars()),
    )
