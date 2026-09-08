from collections.abc import AsyncGenerator, Iterator
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_session
from app.api import videos as videos_api
from app.db.base import Base
from app.db.models import PlaybackEvent, Video, VideoRendition
from app.domain.status import RenditionStatus, VideoPrivacy, VideoStatus
from app.main import app
from app.services import telemetry_admission


class FakePipeline:
    def __init__(self, client: "FakeRedis", *, transaction: bool) -> None:
        self.client = client
        self.transaction = transaction
        self.commands: list[tuple[str, str, int | None]] = []

    def incr(self, key: str) -> "FakePipeline":
        self.commands.append(("incr", key, None))
        return self

    def expire(self, key: str, seconds: int) -> "FakePipeline":
        self.commands.append(("expire", key, seconds))
        return self

    async def execute(self) -> list[int | bool]:
        if not self.transaction:
            raise AssertionError("admission must use a transactional Redis pipeline")
        results: list[int | bool] = []
        for command, key, seconds in self.commands:
            if command == "incr":
                self.client.counters[key] = self.client.counters.get(key, 0) + 1
                results.append(self.client.counters[key])
            else:
                assert seconds is not None
                self.client.expirations[key] = seconds
                results.append(True)
        return results

    async def __aenter__(self) -> "FakePipeline":
        return self

    async def __aexit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        return None


class FakeRedis:
    def __init__(self) -> None:
        self.counters: dict[str, int] = {}
        self.expirations: dict[str, int] = {}
        self.transaction_flags: list[bool] = []
        self.closed = False

    def pipeline(self, *, transaction: bool) -> FakePipeline:
        self.transaction_flags.append(transaction)
        return FakePipeline(self, transaction=transaction)

    async def aclose(self) -> None:
        self.closed = True


class FakeMetricsRedis:
    def __init__(self) -> None:
        self.counters: dict[str, int] = {}
        self.closed = False

    async def incr(self, key: str, amount: int = 1) -> int:
        self.counters[key] = self.counters.get(key, 0) + amount
        return self.counters[key]

    async def mget(self, keys: list[str]) -> list[str | None]:
        return [str(self.counters[key]) if key in self.counters else None for key in keys]

    async def aclose(self) -> None:
        self.closed = True


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


@pytest.fixture(autouse=True)
def fake_telemetry_redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    client = FakeRedis()
    monkeypatch.setattr(videos_api.telemetry_admission, "redis_client_factory", lambda: client)
    return client


@pytest.fixture(autouse=True)
def fake_telemetry_metrics(monkeypatch: pytest.MonkeyPatch) -> FakeMetricsRedis:
    client = FakeMetricsRedis()
    monkeypatch.setattr(videos_api.telemetry_metrics, "redis_client_factory", lambda: client)
    return client


def _headers(user_id: str = "user_123", email: str = "user@example.com") -> dict[str, str]:
    return {
        "X-Atlas-Dev-Clerk-User-Id": user_id,
        "X-Atlas-Dev-Email": email,
    }


def _mark_video_ready(client: TestClient, *, video_id: str, privacy: VideoPrivacy = VideoPrivacy.PUBLIC) -> None:
    import asyncio

    async def mark_ready() -> None:
        async with app.state.test_session_maker() as session:
            video = await session.get(Video, UUID(video_id))
            assert video is not None
            video.status = VideoStatus.READY.value
            video.privacy = privacy.value
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


def test_impression_event_records_surface_position_and_request_id(client: TestClient) -> None:
    video = client.post("/videos", headers=_headers("owner"), json={"title": "Seen card"}).json()
    _mark_video_ready(client, video_id=video["id"], privacy=VideoPrivacy.PUBLIC)

    response = client.post(
        f"/videos/{video['id']}/impressions",
        json={"surface": "home", "position": 2, "request_id": "feed-123"},
    )
    duplicate = client.post(
        f"/videos/{video['id']}/impressions",
        json={"surface": "home", "position": 2, "request_id": "feed-123"},
    )
    list_response = client.get("/videos")

    assert response.status_code == 201
    assert duplicate.status_code == 200
    body = response.json()
    assert body["video_id"] == video["id"]
    assert body["surface"] == "home"
    assert body["position"] == 2
    assert body["request_id"] == "feed-123"
    assert list_response.json()["items"][0]["impression_count"] == 1


def test_view_event_counts_once_per_playback_session_after_threshold(client: TestClient) -> None:
    video = client.post("/videos", headers=_headers("owner"), json={"title": "Watched enough"}).json()
    _mark_video_ready(client, video_id=video["id"], privacy=VideoPrivacy.PUBLIC)

    too_early = client.post(
        f"/videos/{video['id']}/views",
        json={"session_id": "session-1", "position_seconds": "4.9"},
    )
    counted = client.post(
        f"/videos/{video['id']}/views",
        json={"session_id": "session-1", "position_seconds": "5.0"},
    )
    duplicate = client.post(
        f"/videos/{video['id']}/views",
        json={"session_id": "session-1", "position_seconds": "12.0"},
    )
    list_response = client.get("/videos")

    assert too_early.status_code == 202
    assert too_early.json()["counted"] is False
    assert too_early.json()["view_count"] == 0
    assert counted.status_code == 201
    assert counted.json()["counted"] is True
    assert counted.json()["view_count"] == 1
    assert duplicate.status_code == 200
    assert duplicate.json()["counted"] is False
    assert duplicate.json()["view_count"] == 1
    assert list_response.json()["items"][0]["view_count"] == 1


def test_private_video_impression_and_view_require_access(client: TestClient) -> None:
    video = client.post("/videos", headers=_headers("owner"), json={"title": "Private metrics"}).json()
    _mark_video_ready(client, video_id=video["id"], privacy=VideoPrivacy.PRIVATE)

    impression = client.post(
        f"/videos/{video['id']}/impressions",
        headers=_headers("other"),
        json={"surface": "home", "position": 0},
    )
    view = client.post(
        f"/videos/{video['id']}/views",
        headers=_headers("other"),
        json={"session_id": "session-2", "position_seconds": "10.0"},
    )
    owner_view = client.post(
        f"/videos/{video['id']}/views",
        headers=_headers("owner"),
        json={"session_id": "owner-session", "position_seconds": "10.0"},
    )

    assert impression.status_code == 403
    assert view.status_code == 403
    assert owner_view.status_code == 201
    assert owner_view.json()["view_count"] == 1


def test_playback_event_identity_is_returned_and_retry_is_idempotent(
    client: TestClient,
    fake_telemetry_redis: FakeRedis,
    fake_telemetry_metrics: FakeMetricsRedis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video = client.post("/videos", headers=_headers("owner"), json={"title": "Identified playback"}).json()
    _mark_video_ready(client, video_id=video["id"], privacy=VideoPrivacy.PUBLIC)
    payload = {
        "playback_session_id": str(uuid4()),
        "event_id": str(uuid4()),
        "event_type": "play",
        "position_seconds": "5.0",
        "request_id": "telemetry-request-1",
    }
    record_history = AsyncMock()
    monkeypatch.setattr(videos_api.subscription_service, "record_history", record_history)

    first = client.post(f"/videos/{video['id']}/events", json=payload)
    retry = client.post(f"/videos/{video['id']}/events", json=payload)

    assert first.status_code == 201
    assert retry.status_code == 200
    first_body = first.json()
    retry_body = retry.json()
    assert UUID(first_body["playback_session_id"]) == UUID(payload["playback_session_id"])
    assert UUID(first_body["event_id"]) == UUID(payload["event_id"])
    assert retry_body["id"] == first_body["id"]
    assert retry_body["event_id"] == first_body["event_id"]
    assert record_history.await_count == 1
    assert sum(fake_telemetry_redis.counters.values()) == 1
    assert fake_telemetry_metrics.counters["atlas:telemetry:metrics:v1:accepted"] == 1
    assert fake_telemetry_metrics.counters["atlas:telemetry:metrics:v1:duplicate"] == 1


def test_same_playback_session_accepts_distinct_event_ids(client: TestClient) -> None:
    video = client.post("/videos", headers=_headers("owner"), json={"title": "Session events"}).json()
    _mark_video_ready(client, video_id=video["id"], privacy=VideoPrivacy.PUBLIC)
    session_id = str(uuid4())

    first = client.post(
        f"/videos/{video['id']}/events",
        json={"playback_session_id": session_id, "event_id": str(uuid4()), "event_type": "player_ready"},
    )
    second = client.post(
        f"/videos/{video['id']}/events",
        json={"playback_session_id": session_id, "event_id": str(uuid4()), "event_type": "pause"},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["playback_session_id"] == session_id
    assert second.json()["playback_session_id"] == session_id
    assert first.json()["event_id"] != second.json()["event_id"]


def test_event_id_reuse_on_another_video_is_a_sanitized_conflict(client: TestClient) -> None:
    first_video = client.post("/videos", headers=_headers("owner"), json={"title": "First event video"}).json()
    second_video = client.post("/videos", headers=_headers("owner"), json={"title": "Second event video"}).json()
    _mark_video_ready(client, video_id=first_video["id"], privacy=VideoPrivacy.PUBLIC)
    _mark_video_ready(client, video_id=second_video["id"], privacy=VideoPrivacy.PUBLIC)
    event_id = str(uuid4())

    first = client.post(
        f"/videos/{first_video['id']}/events",
        json={"playback_session_id": str(uuid4()), "event_id": event_id, "event_type": "play"},
    )
    conflict = client.post(
        f"/videos/{second_video['id']}/events",
        json={"playback_session_id": str(uuid4()), "event_id": event_id, "event_type": "play"},
    )

    assert first.status_code == 201
    assert conflict.status_code == 409
    assert conflict.json() == {"detail": {"error": "Conflict", "message": "Event ID already exists"}}
    assert event_id not in conflict.text
    assert first_video["id"] not in conflict.text


def test_playback_event_identity_columns_are_required_and_event_id_is_unique() -> None:
    table = PlaybackEvent.__table__

    assert table.c.playback_session_id.nullable is False
    assert table.c.event_id.nullable is False
    assert any(constraint.name == "uq_playback_events_event_id" for constraint in table.constraints)


def test_playback_event_admission_boundary_rejects_121st_event_without_a_row(
    client: TestClient,
    fake_telemetry_redis: FakeRedis,
    fake_telemetry_metrics: FakeMetricsRedis,
) -> None:
    video = client.post("/videos", headers=_headers("boundary-owner"), json={"title": "Admission boundary"}).json()
    _mark_video_ready(client, video_id=video["id"], privacy=VideoPrivacy.PUBLIC)
    playback_session_id = str(uuid4())

    responses = [
        client.post(
            f"/videos/{video['id']}/events",
            json={"playback_session_id": str(uuid4()), "event_id": str(uuid4()), "event_type": "player_ready"},
        )
        for _ in range(121)
    ]

    assert all(response.status_code == 201 for response in responses[:120])
    assert responses[120].status_code == 429
    assert telemetry_admission.SESSION_COOKIE_NAME in responses[0].headers["set-cookie"]
    assert responses[120].json() == {"detail": {"error": "RateLimited", "message": "Playback telemetry rate limit exceeded"}}
    assert sum(fake_telemetry_redis.counters.values()) == 121
    assert fake_telemetry_metrics.counters["atlas:telemetry:metrics:v1:accepted"] == 120
    assert fake_telemetry_metrics.counters["atlas:telemetry:metrics:v1:rate_limited"] == 1

    async def count_events() -> int:
        async with app.state.test_session_maker() as session:
            return len((await session.scalars(select(PlaybackEvent).where(PlaybackEvent.video_id == UUID(video["id"])))).all())

    import asyncio

    assert asyncio.run(count_events()) == 120


def test_admission_keys_separate_video_and_authenticated_anonymous_scopes(
    fake_telemetry_redis: FakeRedis,
) -> None:
    import asyncio

    fixed_now = datetime(2026, 8, 24, 12, 34, 59, tzinfo=timezone.utc)
    video_a = uuid4()
    video_b = uuid4()

    anonymous_session_token = telemetry_admission.issue_session_token(now=int(fixed_now.timestamp()))

    async def admit(
        video_id: UUID,
        user_id: UUID | None,
        session_id: UUID,
        session_token: str | None = None,
    ) -> None:
        await telemetry_admission.admit_playback_event(
            video_id=video_id,
            user_id=user_id,
            playback_session_id=session_id,
            anonymous_session_token=session_token,
            now=fixed_now,
        )

    authenticated_a = uuid4()
    authenticated_b = uuid4()
    asyncio.run(admit(video_a, authenticated_a, uuid4()))
    asyncio.run(admit(video_a, authenticated_b, uuid4()))
    asyncio.run(admit(video_b, authenticated_a, uuid4()))
    # Rotating every client-controlled anonymous value must NOT mint a new bucket.
    asyncio.run(admit(video_a, None, uuid4(), anonymous_session_token))
    asyncio.run(admit(video_a, None, uuid4(), telemetry_admission.issue_session_token(now=int(fixed_now.timestamp()))))
    asyncio.run(admit(video_a, None, uuid4(), None))

    assert len(fake_telemetry_redis.counters) == 4
    assert all(key.startswith("atlas:telemetry:admission:v1:") for key in fake_telemetry_redis.counters)
    assert all("202608241234" in key for key in fake_telemetry_redis.counters)
    assert all("user:" in key or ":anon:" in key for key in fake_telemetry_redis.counters)
    assert all("session:" not in key for key in fake_telemetry_redis.counters)
    assert all("127.0.0.1" not in key for key in fake_telemetry_redis.counters)
    assert all(value == telemetry_admission.WINDOW_TTL_SECONDS for value in fake_telemetry_redis.expirations.values())
    assert fake_telemetry_redis.transaction_flags == [True] * 6
    assert fake_telemetry_redis.closed is True


def test_redis_admission_failure_is_sanitized_and_playback_read_is_unaffected(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video = client.post("/videos", headers=_headers("redis-owner"), json={"title": "Redis unavailable"}).json()
    _mark_video_ready(client, video_id=video["id"], privacy=VideoPrivacy.PUBLIC)

    class FailingRedis:
        def pipeline(self, *, transaction: bool) -> None:
            raise ConnectionError("redis unavailable")

        async def aclose(self) -> None:
            return None

    monkeypatch.setattr(videos_api.telemetry_admission, "redis_client_factory", FailingRedis)
    response = client.post(
        f"/videos/{video['id']}/events",
        json={"playback_session_id": str(uuid4()), "event_id": str(uuid4()), "event_type": "play"},
    )
    playback = client.get(f"/videos/{video['id']}/playback")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {"error": "ServiceUnavailable", "message": "Playback telemetry is temporarily unavailable"}
    }
    assert "redis unavailable" not in response.text
    assert playback.status_code == 200


def test_cookie_rotation_cannot_reset_anonymous_event_admission(
    client: TestClient,
    fake_telemetry_redis: FakeRedis,
    fake_telemetry_metrics: FakeMetricsRedis,
) -> None:
    """Adversarial: every write drops the issued cookie, rotating identity.

    The attacker also rotates playback_session_id and event_id, so the only
    admission identity left is server-derived. Accepted writes must stay
    bounded by the shared per-video budget and no rows may be created past it.
    """
    video = client.post("/videos", headers=_headers("rotation-owner"), json={"title": "Rotation target"}).json()
    _mark_video_ready(client, video_id=video["id"], privacy=VideoPrivacy.PUBLIC)

    accepted = 0
    limited = 0
    for _ in range(150):
        client.cookies.clear()
        response = client.post(
            f"/videos/{video['id']}/events",
            json={"playback_session_id": str(uuid4()), "event_id": str(uuid4()), "event_type": "player_ready"},
        )
        if response.status_code == 201:
            accepted += 1
        elif response.status_code == 429:
            limited += 1
            assert response.json() == {
                "detail": {"error": "RateLimited", "message": "Playback telemetry rate limit exceeded"}
            }
        else:
            raise AssertionError(f"unexpected status {response.status_code}: {response.text}")

    assert accepted == telemetry_admission.MAX_EVENTS_PER_WINDOW
    assert limited == 150 - telemetry_admission.MAX_EVENTS_PER_WINDOW
    anon_keys = [key for key in fake_telemetry_redis.counters if f":{video['id']}:" in key]
    assert 1 <= len(anon_keys) <= 2  # one shared bucket; two only across a minute boundary
    assert all(":anon:" in key for key in anon_keys)

    async def count_events() -> int:
        async with app.state.test_session_maker() as session:
            return len((await session.scalars(select(PlaybackEvent).where(PlaybackEvent.video_id == UUID(video["id"])))).all())

    import asyncio

    assert asyncio.run(count_events()) == telemetry_admission.MAX_EVENTS_PER_WINDOW
    assert fake_telemetry_metrics.counters["atlas:telemetry:metrics:v1:accepted"] == telemetry_admission.MAX_EVENTS_PER_WINDOW


def test_cookie_rotation_cannot_inflate_impression_and_view_counts(
    client: TestClient,
) -> None:
    """Adversarial: rotating cookies must not inflate ranking counters."""
    impression_video = client.post("/videos", headers=_headers("rotation-owner"), json={"title": "Rotation impressions"}).json()
    view_video = client.post("/videos", headers=_headers("rotation-owner"), json={"title": "Rotation views"}).json()
    _mark_video_ready(client, video_id=impression_video["id"], privacy=VideoPrivacy.PUBLIC)
    _mark_video_ready(client, video_id=view_video["id"], privacy=VideoPrivacy.PUBLIC)

    accepted_impressions = 0
    for index in range(150):
        client.cookies.clear()
        response = client.post(
            f"/videos/{impression_video['id']}/impressions",
            json={"surface": "home", "position": index, "request_id": f"rotation-{index}"},
        )
        assert response.status_code in (201, 429), response.text
        accepted_impressions += response.status_code == 201

    accepted_views = 0
    for index in range(150):
        client.cookies.clear()
        response = client.post(
            f"/videos/{view_video['id']}/views",
            json={"session_id": f"rotation-session-{index}", "position_seconds": "10.0"},
        )
        assert response.status_code in (201, 429), response.text
        accepted_views += response.status_code == 201

    assert accepted_impressions == telemetry_admission.MAX_EVENTS_PER_WINDOW
    assert accepted_views == telemetry_admission.MAX_EVENTS_PER_WINDOW
    listing = {item["id"]: item for item in client.get("/videos").json()["items"]}
    assert listing[impression_video["id"]]["impression_count"] == telemetry_admission.MAX_EVENTS_PER_WINDOW
    assert listing[view_video["id"]]["view_count"] == telemetry_admission.MAX_EVENTS_PER_WINDOW


def test_telemetry_secret_missing_fails_closed_outside_development(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video = client.post("/videos", headers=_headers("secret-owner"), json={"title": "Secret contract"}).json()
    _mark_video_ready(client, video_id=video["id"], privacy=VideoPrivacy.PUBLIC)
    payload = {"playback_session_id": str(uuid4()), "event_id": str(uuid4()), "event_type": "pause"}

    monkeypatch.setenv("ATLAS_TELEMETRY_SECRET", "")
    monkeypatch.setenv("APP_ENV", "production")
    client.cookies.clear()
    denied = client.post(f"/videos/{video['id']}/events", json=payload)
    assert denied.status_code == 503
    assert denied.json() == {
        "detail": {"error": "ServiceUnavailable", "message": "Playback telemetry is temporarily unavailable"}
    }

    authenticated = client.post(f"/videos/{video['id']}/events", headers=_headers("secret-owner"), json=payload)
    assert authenticated.status_code == 201

    async def count_events() -> int:
        async with app.state.test_session_maker() as session:
            return len((await session.scalars(select(PlaybackEvent).where(PlaybackEvent.video_id == UUID(video["id"])))).all())

    import asyncio

    assert asyncio.run(count_events()) == 1


def test_telemetry_secret_missing_uses_ephemeral_secret_in_development(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video = client.post("/videos", headers=_headers("dev-secret-owner"), json={"title": "Dev secret"}).json()
    _mark_video_ready(client, video_id=video["id"], privacy=VideoPrivacy.PUBLIC)

    monkeypatch.setenv("ATLAS_TELEMETRY_SECRET", "")
    monkeypatch.setenv("APP_ENV", "development")
    client.cookies.clear()
    response = client.post(
        f"/videos/{video['id']}/events",
        json={"playback_session_id": str(uuid4()), "event_id": str(uuid4()), "event_type": "pause"},
    )
    assert response.status_code == 201
