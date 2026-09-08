from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, VideoChapter
from app.schemas.videos import VideoChapterInput
from app.services import videos as video_service


async def list_chapters(session: AsyncSession, user: User, video_id: UUID) -> list[VideoChapter]:
    await video_service.get_video_for_owner(session, user, video_id)
    result = await session.execute(select(VideoChapter).where(VideoChapter.video_id == video_id).order_by(VideoChapter.position))
    return list(result.scalars())


async def replace_chapters(
    session: AsyncSession,
    user: User,
    video_id: UUID,
    items: list[VideoChapterInput],
) -> list[VideoChapter]:
    video = await video_service.get_video_for_owner(session, user, video_id)
    resolved_video_id = video.id
    _validate_chapters(items, duration_seconds=video.duration_seconds)
    await session.execute(delete(VideoChapter).where(VideoChapter.video_id == video.id))
    chapters = [
        VideoChapter(video_id=video.id, position=index, title=item.title.strip(), start_seconds=item.start_seconds)
        for index, item in enumerate(items)
    ]
    session.add_all(chapters)
    await session.commit()
    session.expire_all()
    result = await session.execute(select(VideoChapter).where(VideoChapter.video_id == resolved_video_id).order_by(VideoChapter.position))
    return list(result.scalars())


def _validate_chapters(items: list[VideoChapterInput], *, duration_seconds: Decimal | None) -> None:
    previous: Decimal | None = None
    for item in items:
        if not item.title.strip():
            raise _invalid("Chapter titles cannot be blank")
        if previous is not None and item.start_seconds <= previous:
            raise _invalid("Chapter start times must be strictly increasing")
        if duration_seconds is not None and item.start_seconds >= duration_seconds:
            raise _invalid("Chapter start times must be within the video duration")
        previous = item.start_seconds


def _invalid(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"error": "InvalidChapters", "message": message})
