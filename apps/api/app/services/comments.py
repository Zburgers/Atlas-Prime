from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import User, VideoComment
from app.domain.status import ModerationStatus
from app.schemas.comments import CommentCreate, CommentResponse
from app.services import videos as video_service


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "NotFound", "message": "Comment not found"},
    )


def _forbidden() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error": "Forbidden", "message": "You do not have access to this comment"},
    )


async def list_comments(
    session: AsyncSession,
    user: User | None,
    video_id: UUID,
    *,
    page: int,
    page_size: int,
) -> tuple[list[CommentResponse], int]:
    video = await video_service.get_video_for_read(session, user, video_id)
    visible = (VideoComment.video_id == video.id) & (VideoComment.moderation_status == ModerationStatus.APPROVED.value)
    total = await session.scalar(select(func.count()).select_from(VideoComment).where(visible))
    result = await session.execute(
        select(VideoComment)
        .options(selectinload(VideoComment.user))
        .where(visible)
        .order_by(VideoComment.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return [_comment_response(comment, user) for comment in result.scalars()], int(total or 0)


async def create_comment(session: AsyncSession, user: User, video_id: UUID, payload: CommentCreate) -> CommentResponse:
    video = await video_service.get_video_for_read(session, user, video_id)
    comment = VideoComment(video_id=video.id, user_id=user.id, body=payload.body)
    session.add(comment)
    await session.commit()
    result = await session.execute(
        select(VideoComment).options(selectinload(VideoComment.user)).where(VideoComment.id == comment.id)
    )
    return _comment_response(result.scalar_one(), user)


async def delete_comment(session: AsyncSession, user: User, comment_id: UUID) -> None:
    comment = await session.get(VideoComment, comment_id)
    if comment is None:
        raise _not_found()
    if comment.user_id != user.id:
        raise _forbidden()
    await session.delete(comment)
    await session.commit()


def _comment_response(comment: VideoComment, current_user: User | None) -> CommentResponse:
    author = comment.user
    author_display_name = "Deleted user"
    if author is not None:
        author_display_name = author.email or "Atlas viewer"
    return CommentResponse(
        id=comment.id,
        video_id=comment.video_id,
        body=comment.body,
        author_display_name=author_display_name,
        owned_by_current_user=current_user is not None and comment.user_id == current_user.id,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )
