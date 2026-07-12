from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import AdminUserDep, CurrentUserDep, SessionDep
from app.schemas.analytics import AnalyticsRebuildResponse, StudioAnalyticsResponse
from app.services import analytics as analytics_service

studio_router = APIRouter(prefix="/studio", tags=["studio analytics"])
admin_router = APIRouter(prefix="/admin", tags=["analytics"])


@studio_router.get("/analytics", response_model=StudioAnalyticsResponse)
async def creator_analytics(
    session: SessionDep,
    user: CurrentUserDep,
    days: Annotated[int, Query(ge=1, le=90)] = 28,
) -> StudioAnalyticsResponse:
    return await analytics_service.studio_analytics(session, user, days=days)


@admin_router.post("/analytics/rebuild", response_model=AnalyticsRebuildResponse)
async def rebuild_analytics(
    date_from: date,
    date_to: date,
    session: SessionDep,
    _admin: AdminUserDep,
) -> AnalyticsRebuildResponse:
    if date_from > date_to:
        raise HTTPException(status_code=422, detail={"error": "ValidationError", "message": "date_from must not be after date_to"})
    result = await analytics_service.rebuild_daily_metrics(session, date_from=date_from, date_to=date_to)
    return AnalyticsRebuildResponse(
        date_from=result.date_from,
        date_to=result.date_to,
        video_metric_rows=result.video_metric_rows,
        creator_metric_rows=result.creator_metric_rows,
    )
