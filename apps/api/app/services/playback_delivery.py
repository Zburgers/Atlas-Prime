from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from datetime import timedelta


class PlaybackTokenError(ValueError):
    pass


@dataclass(frozen=True)
class PlaybackTokenClaims:
    video_id: str
    token_version: int
    viewer_id: str | None
    expires_at: int


def issue_token(*, video_id: str, token_version: int, viewer_id: str | None, ttl: timedelta) -> str:
    expires_at = int(time.time() + ttl.total_seconds())
    payload = {"v": video_id, "tv": token_version, "sub": viewer_id, "exp": expires_at}
    encoded = _encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    signature = _encode(hmac.new(_secret(), encoded.encode(), hashlib.sha256).digest())
    return f"{encoded}.{signature}"


def verify_token(token: str, *, video_id: str, token_version: int) -> PlaybackTokenClaims:
    try:
        encoded, signature = token.split(".", 1)
        expected = _encode(hmac.new(_secret(), encoded.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise PlaybackTokenError("invalid signature")
        payload = json.loads(_decode(encoded))
        claims = PlaybackTokenClaims(video_id=payload["v"], token_version=int(payload["tv"]), viewer_id=payload.get("sub"), expires_at=int(payload["exp"]))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise PlaybackTokenError("invalid token") from exc
    if claims.video_id != video_id or claims.token_version != token_version or claims.expires_at <= int(time.time()):
        raise PlaybackTokenError("expired or revoked token")
    return claims


def _secret() -> bytes:
    secret = os.getenv("ATLAS_PLAYBACK_TOKEN_SECRET", "")
    if len(secret) < 32:
        raise PlaybackTokenError("playback token secret is not configured")
    return secret.encode()


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
