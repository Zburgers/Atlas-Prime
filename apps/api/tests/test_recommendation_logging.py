from collections.abc import AsyncGenerator, Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api import admin, videos as videos_api
from app.api.deps import get_session
from app.db.base import Base
from app.db.models import Video, VideoRendition
from app.domain.status import RenditionStatus, VideoPrivacy, VideoStatus
from app.main import app


@pytest.fixture()
def client() -> Iterator[TestClient]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_maker() as session:
            yield session

    async def create_schema() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_schema() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    import asyncio

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
def enable_dev_auth_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATLAS_ALLOW_DEV_AUTH_HEADERS", "true")
    monkeypatch.setenv("ATLAS_ADMIN_CLERK_USER_IDS", "operator")


@pytest.fixture(autouse=True)
def disable_external_telemetry_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    async def ignore_metric(_metric: str, _amount: int = 1) -> None:
        return None

    monkeypatch.setattr(videos_api.telemetry_metrics, "increment_metric", ignore_metric)


def _headers(user_id: str = "viewer", email: str = "viewer@example.com") -> dict[str, str]:
    return {
        "X-Atlas-Dev-Clerk-User-Id": user_id,
        "X-Atlas-Dev-Email": email,
    }


def _mark_video_ready(client: TestClient, *, video_id: str) -> None:
    import asyncio

    async def mark_ready() -> None:
        async with app.state.test_session_maker() as session:
            video = await session.get(Video, UUID(video_id))
            assert video is not None
            video.status = VideoStatus.READY.value
            video.privacy = VideoPrivacy.PUBLIC.value
            video.hls_master_storage_key = f"processed/{video_id}/hls/master.m3u8"
            video.thumbnail_storage_key = f"processed/{video_id}/hls/thumbnail.jpg"
            video.duration_seconds = 20
            session.add(
                VideoRendition(
                    video_id=video.id,
                    label="360p",
                    width=640,
                    height=360,
                    target_bitrate=800_000,
                    playlist_storage_key=f"processed/{video_id}/hls/360p/playlist.m3u8",
                    status=RenditionStatus.READY.value,
                )
            )
            await session.commit()

    asyncio.run(mark_ready())


def test_feed_request_persists_ranked_results_and_replays_them(client: TestClient) -> None:
    first = client.post("/videos", headers=_headers("owner"), json={"title": "First"}).json()
    second = client.post("/videos", headers=_headers("owner"), json={"title": "Second"}).json()
    _mark_video_ready(client, video_id=first["id"])
    _mark_video_ready(client, video_id=second["id"])

    request_id = "recommendation-request-1"
    feed = client.get(f"/feed/home?request_id={request_id}", headers=_headers())
    replay = client.get(f"/feed/home?request_id={request_id}", headers=_headers())
    debug = client.get(f"/feed/requests/{request_id}/debug", headers=_headers())

    assert feed.status_code == 200
    assert replay.status_code == 200
    assert replay.json() == feed.json()
    assert debug.status_code == 200
    body = debug.json()
    assert body["request_id"] == request_id
    assert body["surface"] == "home"
    assert [(item["video_id"], item["rank"]) for item in body["results"]] == [
        (item["video"]["id"], item["rank"]) for item in feed.json()["items"]
    ]


def test_recommendation_debug_joins_impression_playback_and_view_events(client: TestClient) -> None:
    video = client.post("/videos", headers=_headers("owner"), json={"title": "Tracked"}).json()
    _mark_video_ready(client, video_id=video["id"])

    request_id = "recommendation-request-2"
    feed = client.get(f"/feed/home?request_id={request_id}", headers=_headers())
    assert feed.status_code == 200

    impression = client.post(
        f"/videos/{video['id']}/impressions",
        headers=_headers(),
        json={"surface": "home", "position": 0, "request_id": request_id},
    )
    playback = client.post(
        f"/videos/{video['id']}/events",
        headers=_headers(),
        json={"playback_session_id": str(uuid4()), "event_id": str(uuid4()), "event_type": "play", "position_seconds": 2, "request_id": request_id},
    )
    click = client.post(
        f"/videos/{video['id']}/events",
        headers=_headers(),
        json={"playback_session_id": str(uuid4()), "event_id": str(uuid4()), "event_type": "card_click", "request_id": request_id},
    )
    view = client.post(
        f"/videos/{video['id']}/views",
        headers=_headers(),
        json={"session_id": "recommendation-session", "position_seconds": 5, "request_id": request_id},
    )
    debug = client.get(f"/feed/requests/{request_id}/debug", headers=_headers())

    assert impression.status_code == 201
    assert playback.status_code == 201
    assert click.status_code == 201
    assert view.status_code == 201
    assert debug.status_code == 200
    result = debug.json()["results"][0]
    assert result["video_id"] == video["id"]
    assert result["impression_count"] == 1
    assert result["click_count"] == 1
    assert result["playback_event_count"] == 1
    assert result["view_count"] == 1


def test_admin_can_inspect_recommendation_and_search_debug_but_viewers_cannot(client: TestClient) -> None:
    video = client.post("/videos", headers=_headers("owner"), json={"title": "Atlas search lesson"}).json()
    _mark_video_ready(client, video_id=video["id"])
    request_id = "admin-recommendation-request"
    assert client.get(f"/feed/home?request_id={request_id}", headers=_headers("viewer")).status_code == 200

    denied = client.get("/admin/recommendations", headers=_headers("viewer"))
    denied_debug = client.get(f"/admin/recommendations/{request_id}", headers=_headers("viewer"))
    recent = client.get("/admin/recommendations", headers=_headers("operator"))
    debug = client.get(f"/admin/recommendations/{request_id}", headers=_headers("operator"))
    search = client.get("/admin/search?q=atlas", headers=_headers("operator"))

    assert denied.status_code == 403
    assert denied_debug.status_code == 403
    assert recent.status_code == 200
    assert recent.json()["items"][0]["request_id"] == request_id
    assert debug.status_code == 200
    assert debug.json()["request_id"] == request_id
    assert search.status_code == 200
    assert [item["id"] for item in search.json()["items"]] == [video["id"]]


def test_admin_can_enqueue_search_reindex_but_viewers_cannot(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeCelery:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def send_task(self, task_name: str, *, queue: str) -> object:
            assert task_name == "search_worker.rebuild_public_video_index"
            assert queue == "search"
            return type("Task", (), {"id": "search-task-1"})()

    monkeypatch.setattr(admin, "Celery", FakeCelery)

    denied = client.post("/admin/search/reindex", headers=_headers("viewer"))
    accepted = client.post("/admin/search/reindex", headers=_headers("operator"))

    assert denied.status_code == 403
    assert accepted.status_code == 202
    assert accepted.json() == {"task_id": "search-task-1", "queue": "search"}


def test_admin_telemetry_is_aggregate_only_and_allowlisted(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeMetricsRedis:
        async def mget(self, keys: list[str]) -> list[str]:
            assert keys == [
                "atlas:telemetry:metrics:v1:accepted",
                "atlas:telemetry:metrics:v1:duplicate",
                "atlas:telemetry:metrics:v1:rate_limited",
                "atlas:telemetry:metrics:v1:purged",
            ]
            return ["12", "3", "4", "5"]

        async def aclose(self) -> None:
            return None

    monkeypatch.setattr(admin.telemetry_metrics, "redis_client_factory", FakeMetricsRedis)

    denied = client.get("/admin/telemetry", headers=_headers("viewer"))
    response = client.get("/admin/telemetry", headers=_headers("operator"))

    assert denied.status_code == 403
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["accepted_event_count"] == 12
    assert response.json()["duplicate_event_count"] == 3
    assert response.json()["rate_limited_event_count"] == 4
    assert response.json()["purged_event_count"] == 5
    assert set(response.json()) == {
        "status",
        "accepted_event_count",
        "duplicate_event_count",
        "rate_limited_event_count",
        "purged_event_count",
        "retention_cutoff",
    }
    assert not any(
        forbidden in response.text
        for forbidden in ("playback_session_id", "event_id", "request_id", "user_id", "video_id", "ip_hash")
    )


def test_admin_telemetry_degrades_without_breaking_ops_access(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenMetricsRedis:
        async def mget(self, _keys: list[str]) -> list[str]:
            raise ConnectionError("metrics unavailable")

        async def aclose(self) -> None:
            return None

    monkeypatch.setattr(admin.telemetry_metrics, "redis_client_factory", BrokenMetricsRedis)

    response = client.get("/admin/telemetry", headers=_headers("operator"))
    ops = client.get("/admin/ops", headers=_headers("operator"))

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["accepted_event_count"] is None
    assert response.json()["duplicate_event_count"] is None
    assert response.json()["rate_limited_event_count"] is None
    assert response.json()["purged_event_count"] is None
    assert "metrics unavailable" not in response.text
    assert ops.status_code == 200


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/admin/search?q=atlas"),
        ("get", "/admin/ops"),
        ("get", "/admin/videos"),
        ("get", "/admin/jobs"),
        ("get", "/admin/videos/00000000-0000-0000-0000-000000000001/debug"),
    ],
)
def test_non_admin_cannot_access_each_core_admin_router_family(client: TestClient, method: str, path: str) -> None:
    response = getattr(client, method)(path, headers=_headers("viewer"))

    assert response.status_code == 403
