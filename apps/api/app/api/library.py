from fastapi import APIRouter

from app.api.deps import CurrentUserDep, SessionDep
from app.api.videos import video_list_item
from app.schemas.library import WatchHistoryItemResponse, WatchHistoryResponse
from app.services import subscriptions as subscription_service

router = APIRouter(prefix="/library", tags=["library"])


@router.get("/history", response_model=WatchHistoryResponse)
async def watch_history(session: SessionDep, user: CurrentUserDep) -> WatchHistoryResponse:
    items = await subscription_service.history(session, user)
    return WatchHistoryResponse(items=[WatchHistoryItemResponse(id=item.id, position_seconds=float(item.position_seconds) if item.position_seconds is not None else None, watched_at=item.watched_at, video=video_list_item(item.video)) for item in items])
