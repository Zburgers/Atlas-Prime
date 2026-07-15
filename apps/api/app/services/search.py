from __future__ import annotations

import logging
from uuid import UUID

import httpx
from sqlalchemy import case, func, literal_column, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import config
from app.db.models import Channel, Video
from app.domain.status import ModerationStatus, VideoPrivacy, VideoStatus
from app.services.search_index import INDEX_UID

logger = logging.getLogger(__name__)


def normalize_search_query(query: str) -> str:
    return " ".join(query.strip().split())


async def search_public_videos(
    session: AsyncSession,
    query: str,
    page: int,
    page_size: int,
) -> tuple[list[Video], int]:
    normalized_query = normalize_search_query(query)
    if not normalized_query:
        return [], 0

    if config.search_backend() == "meilisearch" and session.get_bind().dialect.name == "postgresql":
        try:
            return await _search_public_videos_meilisearch(session, normalized_query, page, page_size)
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.warning("sector=G stage=search_fallback backend=meilisearch error=%s", exc)

    if session.get_bind().dialect.name == "postgresql":
        return await _search_public_videos_postgres(session, normalized_query, page, page_size)
    return await _search_public_videos_fallback(session, normalized_query, page, page_size)


async def _search_public_videos_meilisearch(
    session: AsyncSession,
    query: str,
    page: int,
    page_size: int,
) -> tuple[list[Video], int]:
    headers = {"Authorization": f"Bearer {config.meilisearch_master_key()}"} if config.meilisearch_master_key() else {}
    async with httpx.AsyncClient(base_url=config.meilisearch_url(), headers=headers, timeout=5) as client:
        response = await client.post(
            f"/indexes/{INDEX_UID}/search",
            json={
                "q": query,
                "filter": "privacy = public",
                "offset": (page - 1) * page_size,
                "limit": page_size,
            },
        )
        response.raise_for_status()
    payload = response.json()
    document_ids = [UUID(str(hit["id"])) for hit in payload.get("hits", [])]
    if not document_ids:
        return [], int(payload.get("estimatedTotalHits", 0))

    result = await session.execute(
        select(Video)
        .options(selectinload(Video.channel))
        .where(Video.id.in_(document_ids), _public_ready())
    )
    videos_by_id = {video.id: video for video in result.scalars()}
    videos = [videos_by_id[video_id] for video_id in document_ids if video_id in videos_by_id]
    return videos, int(payload.get("estimatedTotalHits", len(videos)))


async def _search_public_videos_postgres(
    session: AsyncSession,
    query: str,
    page: int,
    page_size: int,
) -> tuple[list[Video], int]:
    document = _postgres_search_document()
    ts_query = func.websearch_to_tsquery("english", query)
    rank = func.ts_rank_cd(document, ts_query).label("search_rank")
    conditions = [_public_ready(), document.bool_op("@@")(ts_query)]

    total = await session.scalar(
        select(func.count())
        .select_from(Video)
        .outerjoin(Channel, Video.channel_id == Channel.id)
        .where(*conditions)
    )
    result = await session.execute(
        select(Video)
        .outerjoin(Channel, Video.channel_id == Channel.id)
        .options(selectinload(Video.channel))
        .where(*conditions)
        .order_by(rank.desc(), Video.view_count.desc(), Video.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars()), int(total or 0)


async def _search_public_videos_fallback(
    session: AsyncSession,
    query: str,
    page: int,
    page_size: int,
) -> tuple[list[Video], int]:
    lowered_query = query.lower()
    contains_query = f"%{lowered_query}%"
    starts_query = f"{lowered_query}%"

    title = func.lower(func.coalesce(Video.title, ""))
    description = func.lower(func.coalesce(Video.description, ""))
    channel_display_name = func.lower(func.coalesce(Channel.display_name, ""))
    channel_handle = func.lower(func.coalesce(Channel.handle, ""))
    conditions = [
        _public_ready(),
        or_(
            title.like(contains_query),
            description.like(contains_query),
            channel_display_name.like(contains_query),
            channel_handle.like(contains_query),
        ),
    ]
    rank = case(
        (title.like(starts_query), 4),
        (title.like(contains_query), 3),
        (description.like(contains_query), 2),
        (channel_display_name.like(contains_query), 1),
        (channel_handle.like(contains_query), 1),
        else_=0,
    )

    total = await session.scalar(
        select(func.count())
        .select_from(Video)
        .outerjoin(Channel, Video.channel_id == Channel.id)
        .where(*conditions)
    )
    result = await session.execute(
        select(Video)
        .outerjoin(Channel, Video.channel_id == Channel.id)
        .options(selectinload(Video.channel))
        .where(*conditions)
        .order_by(rank.desc(), Video.view_count.desc(), Video.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars()), int(total or 0)


def _postgres_search_document() -> object:
    title = func.setweight(func.to_tsvector("english", func.coalesce(Video.title, "")), literal_column("'A'"))
    description = func.setweight(func.to_tsvector("english", func.coalesce(Video.description, "")), literal_column("'B'"))
    channel_display_name = func.setweight(
        func.to_tsvector("english", func.coalesce(Channel.display_name, "")),
        literal_column("'C'"),
    )
    channel_handle = func.setweight(func.to_tsvector("english", func.coalesce(Channel.handle, "")), literal_column("'C'"))
    return title.op("||")(description).op("||")(channel_display_name).op("||")(channel_handle)


def _public_ready() -> object:
    return (
        (Video.status == VideoStatus.READY.value)
        & (Video.privacy == VideoPrivacy.PUBLIC.value)
        & (Video.moderation_status == ModerationStatus.APPROVED.value)
    )
