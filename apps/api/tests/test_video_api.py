from collections.abc import AsyncGenerator, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_session
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
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        asyncio.run(drop_schema())


def _headers(user_id: str = "user_123", email: str = "user@example.com") -> dict[str, str]:
    return {
        "X-Atlas-Dev-Clerk-User-Id": user_id,
        "X-Atlas-Dev-Email": email,
    }


def test_create_video_defaults_to_private_draft(client: TestClient) -> None:
    response = client.post("/videos", headers=_headers(), json={"title": "First lesson"})

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "First lesson"
    assert body["privacy"] == "private"
    assert body["status"] == "draft"
    assert body["owner_id"]


def test_private_video_is_owner_only(client: TestClient) -> None:
    created = client.post("/videos", headers=_headers("owner"), json={"title": "Private cut"})
    video_id = created.json()["id"]

    owner_response = client.get(f"/videos/{video_id}", headers=_headers("owner"))
    other_response = client.get(f"/videos/{video_id}", headers=_headers("other"))

    assert owner_response.status_code == 200
    assert other_response.status_code == 403


def test_processing_status_reports_draft_without_job(client: TestClient) -> None:
    created = client.post("/videos", headers=_headers(), json={"title": "Needs upload"})
    video_id = created.json()["id"]

    response = client.get(f"/videos/{video_id}/processing-status", headers=_headers())

    assert response.status_code == 200
    assert response.json() == {
        "video_id": video_id,
        "video_status": "draft",
        "latest_job": None,
        "failure_code": None,
        "failure_message": None,
    }


def test_process_requires_uploaded_state(client: TestClient) -> None:
    created = client.post("/videos", headers=_headers(), json={"title": "Not uploaded"})
    video_id = created.json()["id"]

    response = client.post(f"/videos/{video_id}/process", headers=_headers())

    assert response.status_code == 409
    assert response.json()["detail"]["details"]["required_status"] == "uploaded"
