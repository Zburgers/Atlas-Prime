from datetime import timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.api.videos import _resolve_hls_asset
from app.db.models import VideoAssetInventory
from app.services.playback_delivery import PlaybackTokenError, issue_token, verify_token


VIDEO_ID = UUID("11111111-1111-4111-8111-111111111111")
PUBLISHED_GENERATION = UUID("12345678-1234-4234-8234-1234567890ab")


def _resolver_video(*inventory_paths: tuple[UUID, str]) -> SimpleNamespace:
    return SimpleNamespace(
        id=VIDEO_ID,
        hls_master_storage_key=f"processed/{VIDEO_ID}/attempts/{PUBLISHED_GENERATION}/hls/master.m3u8",
        renditions=[SimpleNamespace(label="360p")],
        asset_inventory=[
            VideoAssetInventory(
                video_id=VIDEO_ID,
                generation=generation,
                relative_path=relative_path,
                content_type="video/mp2t",
                size_bytes=1,
                sha256="a" * 64,
            )
            for generation, relative_path in inventory_paths
        ],
    )


def test_playback_token_is_bound_to_video_expiry_and_version(monkeypatch) -> None:
    monkeypatch.setenv("ATLAS_PLAYBACK_TOKEN_SECRET", "test-secret-that-is-long-enough-for-hmac")
    token = issue_token(video_id="video-1", token_version=2, viewer_id="viewer-1", ttl=timedelta(seconds=60))

    claims = verify_token(token, video_id="video-1", token_version=2)

    assert claims.viewer_id == "viewer-1"
    with pytest.raises(PlaybackTokenError):
        verify_token(token, video_id="video-2", token_version=2)
    with pytest.raises(PlaybackTokenError):
        verify_token(token, video_id="video-1", token_version=3)


def test_hls_resolver_constructs_attempt_key_from_published_inventory() -> None:
    video = _resolver_video((PUBLISHED_GENERATION, "360p/segment_000.ts"))

    storage_key, media_type, cache_control = _resolve_hls_asset(video, "360p/segment_000.ts")

    assert storage_key == f"processed/{VIDEO_ID}/attempts/{PUBLISHED_GENERATION}/hls/360p/segment_000.ts"
    assert media_type == "video/mp2t"
    assert "immutable" in cache_control


def test_hls_resolver_rejects_uninventoried_and_old_generation_assets() -> None:
    old_generation = UUID("87654321-4321-4321-8321-ba0987654321")
    video = _resolver_video((old_generation, "360p/segment_000.ts"))

    with pytest.raises(HTTPException) as exc_info:
        _resolve_hls_asset(video, "360p/segment_000.ts")

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == {"error": "NotFound", "message": "HLS asset not found"}
