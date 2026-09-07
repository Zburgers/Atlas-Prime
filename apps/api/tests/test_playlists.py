from collections.abc import AsyncGenerator, Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_session
from app.db.base import Base
from app.db.models import Video
from app.domain.status import VideoPrivacy, VideoStatus
from app.main import app


@pytest.fixture()
def client() -> Iterator[TestClient]:
    engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_maker() as session:
            yield session

    import asyncio

    async def create_schema() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def drop_schema() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    asyncio.run(create_schema())
    app.dependency_overrides[get_session] = override_session
    app.state.test_session_maker = session_maker
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        del app.state.test_session_maker
        asyncio.run(drop_schema())


@pytest.fixture(autouse=True)
def dev_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATLAS_ALLOW_DEV_AUTH_HEADERS", "true")


def headers(user: str) -> dict[str, str]:
    return {"X-Atlas-Dev-Clerk-User-Id": user, "X-Atlas-Dev-Email": f"{user}@example.com"}


def mark_ready(client: TestClient, video_id: str, privacy: VideoPrivacy = VideoPrivacy.PUBLIC) -> None:
    import asyncio

    async def update() -> None:
        async with app.state.test_session_maker() as session:
            video = await session.get(Video, UUID(video_id))
            assert video is not None
            video.status = VideoStatus.READY.value
            video.privacy = privacy.value
            await session.commit()

    asyncio.run(update())


def test_owner_can_create_public_playlist_add_public_video_and_read_it(client: TestClient) -> None:
    video = client.post("/videos", headers=headers("owner"), json={"title": "Playlist-ready"}).json()
    mark_ready(client, video["id"])
    playlist = client.post("/playlists", headers=headers("owner"), json={"title": "Course list", "privacy": "public"})
    added = client.post(f"/playlists/{playlist.json()['id']}/items", headers=headers("owner"), json={"video_id": video["id"]})
    read = client.get(f"/playlists/{playlist.json()['id']}")

    assert playlist.status_code == 201
    assert added.status_code == 201
    assert read.status_code == 200
    assert read.json()["items"][0]["video"]["title"] == "Playlist-ready"


def test_non_owner_cannot_mutate_playlist_and_private_playlist_is_not_public(client: TestClient) -> None:
    playlist = client.post("/playlists", headers=headers("owner"), json={"title": "Private list"}).json()
    private_read = client.get(f"/playlists/{playlist['id']}")
    other_add = client.post(f"/playlists/{playlist['id']}/items", headers=headers("other"), json={"video_id": "00000000-0000-0000-0000-000000000001"})

    assert private_read.status_code == 404
    assert other_add.status_code == 403


def test_public_playlist_filters_private_items_and_keeps_positions_after_middle_delete(client: TestClient) -> None:
    videos = [
        client.post("/videos", headers=headers("owner"), json={"title": title}).json()
        for title in ("First", "Second", "Third", "Fourth")
    ]
    for video in videos:
        mark_ready(client, video["id"])
    playlist = client.post("/playlists", headers=headers("owner"), json={"title": "Stable list", "privacy": "public"}).json()
    items = [
        client.post(
            f"/playlists/{playlist['id']}/items",
            headers=headers("owner"),
            json={"video_id": video["id"]},
        ).json()
        for video in videos[:3]
    ]

    assert client.delete(f"/playlists/{playlist['id']}/items/{items[1]['id']}", headers=headers("owner")).status_code == 204
    fourth = client.post(
        f"/playlists/{playlist['id']}/items",
        headers=headers("owner"),
        json={"video_id": videos[3]["id"]},
    ).json()
    assert fourth["position"] == 3

    assert client.patch(f"/videos/{videos[2]['id']}", headers=headers("owner"), json={"privacy": "private"}).status_code == 200
    read = client.get(f"/playlists/{playlist['id']}")

    assert read.status_code == 200
    assert [(item["position"], item["video"]["title"]) for item in read.json()["items"]] == [(0, "First"), (3, "Fourth")]
