from datetime import timedelta

import pytest

from app.services.playback_delivery import PlaybackTokenError, issue_token, verify_token


def test_playback_token_is_bound_to_video_expiry_and_version(monkeypatch) -> None:
    monkeypatch.setenv("ATLAS_PLAYBACK_TOKEN_SECRET", "test-secret-that-is-long-enough-for-hmac")
    token = issue_token(video_id="video-1", token_version=2, viewer_id="viewer-1", ttl=timedelta(seconds=60))

    claims = verify_token(token, video_id="video-1", token_version=2)

    assert claims.viewer_id == "viewer-1"
    with pytest.raises(PlaybackTokenError):
        verify_token(token, video_id="video-2", token_version=2)
    with pytest.raises(PlaybackTokenError):
        verify_token(token, video_id="video-1", token_version=3)
