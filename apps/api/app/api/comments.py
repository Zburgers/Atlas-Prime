from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUserDep, OptionalCurrentUserDep, SessionDep
from app.schemas.comments import CommentCreate, CommentListResponse, CommentResponse
from app.services import comments as comments_service

router = APIRouter(tags=["comments"])


@router.get("/videos/{video_id}/comments", response_model=CommentListResponse)
async def list_video_comments(
    video_id: UUID,
    session: SessionDep,
    user: OptionalCurrentUserDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> CommentListResponse:
    items, total = await comments_service.list_comments(session, user, video_id, page=page, page_size=page_size)
    return CommentListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/videos/{video_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_video_comment(
    video_id: UUID,
    payload: CommentCreate,
    session: SessionDep,
    user: CurrentUserDep,
) -> CommentResponse:
    return await comments_service.create_comment(session, user, video_id, payload)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(comment_id: UUID, session: SessionDep, user: CurrentUserDep) -> Response:
    await comments_service.delete_comment(session, user, comment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
