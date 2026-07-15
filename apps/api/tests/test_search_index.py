import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

import httpx

from app.services import search_index


class _Response:
    def __init__(self, status_code: int, payload: dict[str, object]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, object]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "request failed",
                request=httpx.Request("GET", "http://test"),
                response=httpx.Response(self.status_code),
            )


class _Client:
    def __init__(self, **_kwargs: object) -> None:
        self.requests: list[tuple[str, str, object]] = []
        self.task_uid = 0

    async def __aenter__(self) -> "_Client":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def post(self, path: str, *, json: object) -> _Response:
        return self._task("POST", path, json)

    async def patch(self, path: str, *, json: object) -> _Response:
        return self._task("PATCH", path, json)

    async def put(self, path: str, *, json: object) -> _Response:
        return self._task("PUT", path, json)

    async def delete(self, path: str) -> _Response:
        return self._task("DELETE", path, None)

    async def get(self, path: str) -> _Response:
        self.requests.append(("GET", path, None))
        if path == "/indexes/atlas_videos":
            return _Response(404, {})
        return _Response(200, {"status": "succeeded"})

    def _task(self, method: str, path: str, payload: object) -> _Response:
        self.requests.append((method, path, payload))
        task_uid = self.task_uid
        self.task_uid += 1
        return _Response(202, {"taskUid": task_uid})


class _Result:
    def __init__(self, videos: list[object]) -> None:
        self.videos = videos

    def scalars(self) -> list[object]:
        return self.videos


class _Session:
    def __init__(self, videos: list[object]) -> None:
        self.videos = videos

    async def execute(self, _statement: object) -> _Result:
        return _Result(self.videos)


def test_rebuild_replaces_documents_with_public_video_corpus(monkeypatch) -> None:
    fake_client = _Client()
    video = SimpleNamespace(
        id="video-id",
        title="Atlas Search",
        description=None,
        channel=SimpleNamespace(display_name="Atlas", handle="@atlas"),
        privacy="public",
        view_count=5,
        like_count=2,
        created_at=datetime(2026, 7, 15, tzinfo=UTC),
    )
    monkeypatch.setattr(search_index.httpx, "AsyncClient", lambda **_kwargs: fake_client)

    summary = asyncio.run(search_index.rebuild_public_video_index(_Session([video])))

    assert summary == search_index.SearchIndexSummary(document_count=1, task_uid=3)
    assert ("DELETE", "/indexes/atlas_videos/documents", None) in fake_client.requests
    assert (
        "PUT",
        "/indexes/atlas_videos/documents",
        [
            {
                "id": "video-id",
                "title": "Atlas Search",
                "description": "",
                "channel_display_name": "Atlas",
                "channel_handle": "@atlas",
                "privacy": "public",
                "view_count": 5,
                "like_count": 2,
                "created_at": "2026-07-15T00:00:00+00:00",
            }
        ],
    ) in fake_client.requests
