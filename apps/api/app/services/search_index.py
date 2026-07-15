from __future__ import annotations

import asyncio
import html
import re
from dataclasses import dataclass

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import config
from app.db.models import Video, VideoTextTrack
from app.domain.status import ModerationStatus, VideoPrivacy, VideoStatus
from app.services.storage import HlsObjectNotFoundError, ProcessedHlsStorage

INDEX_UID = "atlas_videos"


@dataclass(frozen=True)
class SearchIndexSummary:
    document_count: int
    task_uid: int


class SearchIndexError(RuntimeError):
    pass


async def rebuild_public_video_index(
    session: AsyncSession,
    storage: ProcessedHlsStorage | None = None,
) -> SearchIndexSummary:
    result = await session.execute(
        select(Video)
        .options(selectinload(Video.channel), selectinload(Video.text_tracks))
        .where(
            Video.status == VideoStatus.READY.value,
            Video.privacy == VideoPrivacy.PUBLIC.value,
            Video.moderation_status == ModerationStatus.APPROVED.value,
        )
        .order_by(Video.created_at.desc())
    )
    documents = [await _document(video, storage) for video in result.scalars()]
    headers = {"Authorization": f"Bearer {config.meilisearch_master_key()}"} if config.meilisearch_master_key() else {}
    async with httpx.AsyncClient(base_url=config.meilisearch_url(), headers=headers, timeout=15) as client:
        index = await client.get(f"/indexes/{INDEX_UID}")
        if index.status_code == 404:
            creation = await client.post("/indexes", json={"uid": INDEX_UID, "primaryKey": "id"})
            _require_task(creation)
            await _wait_for_task(client, int(creation.json()["taskUid"]))
        elif index.status_code != 200:
            _raise(index)
        settings = await client.patch(
            f"/indexes/{INDEX_UID}/settings",
            json={"searchableAttributes": ["title", "description", "caption_text", "channel_display_name", "channel_handle"], "filterableAttributes": ["privacy"]},
        )
        _require_task(settings)
        await _wait_for_task(client, int(settings.json()["taskUid"]))
        removal = await client.delete(f"/indexes/{INDEX_UID}/documents")
        _require_task(removal)
        await _wait_for_task(client, int(removal.json()["taskUid"]))
        replacement = await client.put(f"/indexes/{INDEX_UID}/documents", json=documents)
        _require_task(replacement)
        task_uid = int(replacement.json()["taskUid"])
        await _wait_for_task(client, task_uid)
    return SearchIndexSummary(document_count=len(documents), task_uid=task_uid)


async def _document(video: Video, storage: ProcessedHlsStorage | None) -> dict[str, object]:
    channel = video.channel
    return {
        "id": str(video.id),
        "title": video.title,
        "description": video.description or "",
        "caption_text": await _caption_text(video.text_tracks, storage),
        "channel_display_name": channel.display_name if channel else "",
        "channel_handle": channel.handle if channel else "",
        "privacy": video.privacy,
        "view_count": video.view_count,
        "like_count": video.like_count,
        "created_at": video.created_at.isoformat() if video.created_at else "",
    }


async def _caption_text(tracks: list[VideoTextTrack], storage: ProcessedHlsStorage | None) -> str:
    if storage is None:
        return ""
    fragments: list[str] = []
    for track in tracks:
        try:
            stored = await asyncio.to_thread(storage.get_caption, key=track.storage_key)
        except HlsObjectNotFoundError:
            continue
        fragment = _webvtt_to_text(stored.body)
        if fragment:
            fragments.append(fragment)
    return " ".join(fragments)[:100_000]


def _webvtt_to_text(body: bytes) -> str:
    text = body.decode("utf-8-sig", errors="replace").replace("\r\n", "\n")
    fragments: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timestamp_index = next((index for index, line in enumerate(lines) if "-->" in line), None)
        if timestamp_index is None:
            continue
        cue_text = " ".join(lines[timestamp_index + 1 :])
        cue_text = html.unescape(re.sub(r"<[^>]*>", "", cue_text)).strip()
        if cue_text:
            fragments.append(cue_text)
    return " ".join(fragments)


async def _wait_for_task(client: httpx.AsyncClient, task_uid: int) -> None:
    for _ in range(300):
        response = await client.get(f"/tasks/{task_uid}")
        response.raise_for_status()
        payload = response.json()
        if payload["status"] == "succeeded":
            return
        if payload["status"] in {"failed", "canceled"}:
            raise SearchIndexError(f"Meilisearch task {task_uid} {payload['status']}")
        await asyncio.sleep(0.1)
    raise SearchIndexError(f"Meilisearch task {task_uid} timed out")


def _require_task(response: httpx.Response) -> None:
    if response.status_code != 202:
        _raise(response)


def _raise(response: httpx.Response) -> None:
    raise SearchIndexError(f"Meilisearch request failed: {response.status_code}")
