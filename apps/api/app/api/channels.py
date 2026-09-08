from __future__ import annotations

from fastapi import APIRouter, Response, status
from uuid import UUID

from app.api.deps import CurrentUserDep, SessionDep
from app.schemas.channels import ChannelResponse, ChannelUpdate, PublicChannelResponse
from app.services import channels as channel_service
from app.services import subscriptions as subscription_service
from app.api.videos import video_list_item

router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("/me", response_model=ChannelResponse)
async def get_my_channel(session: SessionDep, user: CurrentUserDep) -> object:
    return await channel_service.get_my_channel(session, user)


@router.patch("/me", response_model=ChannelResponse)
async def update_my_channel(payload: ChannelUpdate, session: SessionDep, user: CurrentUserDep) -> object:
    return await channel_service.update_my_channel(session, user, payload)


@router.get("/{handle}", response_model=PublicChannelResponse)
async def get_channel(handle: str, session: SessionDep) -> PublicChannelResponse:
    channel, videos = await channel_service.get_public_channel_with_videos(session, handle)
    channel_data = ChannelResponse.model_validate(channel).model_dump()
    return PublicChannelResponse(**channel_data, videos=[video_list_item(video) for video in videos])


@router.post("/{channel_id}/subscribe", status_code=status.HTTP_200_OK)
async def subscribe(channel_id: UUID, response: Response, session: SessionDep, user: CurrentUserDep) -> Response:
    await subscription_service.subscribe(session, user, channel_id, response)
    return response


@router.delete("/{channel_id}/subscribe", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe(channel_id: UUID, session: SessionDep, user: CurrentUserDep) -> Response:
    await subscription_service.unsubscribe(session, user, channel_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
