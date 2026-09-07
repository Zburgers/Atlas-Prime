from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUserDep, OptionalCurrentUserDep, SessionDep
from app.api.videos import video_list_item
from app.domain.visibility import is_discoverable_video
from app.schemas.playlists import PlaylistCreate, PlaylistItemCreate, PlaylistItemResponse, PlaylistResponse
from app.services import playlists as playlist_service

router = APIRouter(prefix="/playlists", tags=["playlists"])

def response(playlist: object) -> PlaylistResponse:
    items = sorted(playlist.items, key=lambda item: item.position)
    if playlist.privacy == "public":
        items = [item for item in items if is_discoverable_video(item.video)]
    return PlaylistResponse(id=playlist.id, owner_id=playlist.owner_id, title=playlist.title, description=playlist.description, privacy=playlist.privacy, created_at=playlist.created_at, updated_at=playlist.updated_at, items=[PlaylistItemResponse(id=item.id, position=item.position, created_at=item.created_at, video=video_list_item(item.video)) for item in items])

@router.post("", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
async def create(payload: PlaylistCreate, session: SessionDep, user: CurrentUserDep) -> PlaylistResponse:
    return response(await playlist_service.create(session, user, payload))

@router.get("/{playlist_id}", response_model=PlaylistResponse)
async def get(playlist_id: UUID, session: SessionDep, user: OptionalCurrentUserDep) -> PlaylistResponse:
    return response(await playlist_service.for_read(session, user, playlist_id))

@router.post("/{playlist_id}/items", response_model=PlaylistItemResponse, status_code=status.HTTP_201_CREATED)
async def add_item(playlist_id: UUID, payload: PlaylistItemCreate, session: SessionDep, user: CurrentUserDep) -> PlaylistItemResponse:
    item = await playlist_service.add_item(session, user, playlist_id, payload.video_id)
    return PlaylistItemResponse(id=item.id, position=item.position, created_at=item.created_at, video=video_list_item(item.video))

@router.delete("/{playlist_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item(playlist_id: UUID, item_id: UUID, session: SessionDep, user: CurrentUserDep) -> Response:
    await playlist_service.remove_item(session, user, playlist_id, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
