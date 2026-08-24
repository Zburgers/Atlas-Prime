from collections.abc import AsyncGenerator, Iterator
from uuid import UUID, uuid4

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


def test_viewer_can_subscribe_and_see_only_public_ready_videos_in_subscription_feed(client: TestClient) -> None:
    public = client.post("/videos", headers=headers("creator"), json={"title": "Public release"}).json()
    private = client.post("/videos", headers=headers("creator"), json={"title": "Private release"}).json()
    mark_ready(client, public["id"])
    mark_ready(client, private["id"], VideoPrivacy.PRIVATE)
    channel = client.get("/channels/me", headers=headers("creator")).json()

    created = client.post(f"/channels/{channel['id']}/subscribe", headers=headers("viewer"))
    duplicate = client.post(f"/channels/{channel['id']}/subscribe", headers=headers("viewer"))
    feed = client.get("/feed/subscriptions", headers=headers("viewer"))
    removed = client.delete(f"/channels/{channel['id']}/subscribe", headers=headers("viewer"))

    assert created.status_code == 201
    assert duplicate.status_code == 200
    assert [item["title"] for item in feed.json()["items"]] == ["Public release"]
    assert removed.status_code == 204


def test_authenticated_play_event_upserts_private_history_and_library_is_viewer_scoped(client: TestClient) -> None:
    video = client.post("/videos", headers=headers("creator"), json={"title": "Private history"}).json()
    mark_ready(client, video["id"], VideoPrivacy.PRIVATE)
    own_play = client.post(
        f"/videos/{video['id']}/events",
        headers=headers("creator"),
        json={"playback_session_id": str(uuid4()), "event_id": str(uuid4()), "event_type": "play", "position_seconds": 14},
    )
    own_history = client.get("/library/history", headers=headers("creator"))
    other_history = client.get("/library/history", headers=headers("viewer"))

    assert own_play.status_code == 201
    assert own_history.status_code == 200
    assert own_history.json()["items"][0]["video"]["title"] == "Private history"
    assert other_history.json()["items"] == []
