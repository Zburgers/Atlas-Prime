from __future__ import annotations

import os
import re
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class MediaAdmissionPolicy:
    max_duration_seconds: int
    max_width: int
    max_height: int
    max_pixel_area: int
    max_frame_rate: Fraction
    max_decoded_work_pixel_frames: int


def _positive_int(name: str, default: int, approved_max: int | None = None) -> int:
    raw = env(name, str(default))
    if not re.fullmatch(r"[0-9]+", raw):
        raise ValueError(f"{name} must be a positive integer")
    value = int(raw)
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    if approved_max is not None and value > approved_max:
        raise ValueError(f"{name} must not exceed {approved_max}")
    return value


def _positive_fraction(name: str, default: str, approved_max: Fraction) -> Fraction:
    raw = env(name, default)
    try:
        value = Fraction(raw)
    except (ValueError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError(f"{name} must be a positive finite rational") from exc
    if value <= 0 or value > approved_max:
        raise ValueError(f"{name} must be positive and no greater than {approved_max}")
    return value


def media_admission_policy() -> MediaAdmissionPolicy:
    return MediaAdmissionPolicy(
        max_duration_seconds=_positive_int("ATLAS_MEDIA_MAX_DURATION_SECONDS", 600, 600),
        max_width=_positive_int("ATLAS_MEDIA_MAX_WIDTH", 1920, 1920),
        max_height=_positive_int("ATLAS_MEDIA_MAX_HEIGHT", 1920, 1920),
        max_pixel_area=_positive_int("ATLAS_MEDIA_MAX_PIXEL_AREA", 2_073_600, 2_073_600),
        max_frame_rate=_positive_fraction("ATLAS_MEDIA_MAX_FRAME_RATE", "30/1", Fraction(30)),
        max_decoded_work_pixel_frames=_positive_int(
            "ATLAS_MEDIA_MAX_DECODED_WORK_PIXEL_FRAMES", 37_324_800_000, 37_324_800_000
        ),
    )


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def celery_broker_url() -> str:
    return env("CELERY_BROKER_URL", env("REDIS_URL", "redis://redis:6379/0"))


def celery_result_backend() -> str:
    return env("CELERY_RESULT_BACKEND", "redis://redis:6379/1")


def database_url() -> str:
    raw = env("DATABASE_URL", "postgresql://atlas:atlas@postgres:5432/atlas_prime")
    if raw.startswith("postgresql+asyncpg://"):
        return raw.replace("postgresql+asyncpg://", "postgresql://", 1)
    return raw


def minio_endpoint() -> str:
    return env("MINIO_ENDPOINT", "http://minio:9000")


def minio_access_key() -> str:
    return env("MINIO_ACCESS_KEY", env("MINIO_ROOT_USER", "atlasminio"))


def minio_secret_key() -> str:
    return env("MINIO_SECRET_KEY", env("MINIO_ROOT_PASSWORD", "atlasminiopassword"))


def minio_region() -> str:
    return env("MINIO_REGION", "us-east-1")


def originals_bucket() -> str:
    return env("MINIO_BUCKET_ORIGINALS", "atlas-originals")


def processed_bucket() -> str:
    return env("MINIO_BUCKET_PROCESSED", "atlas-processed")


def worker_id() -> str:
    return env("ATLAS_WORKER_ID", "media-worker")


def ffmpeg_timeout_seconds() -> int:
    return _positive_int("ATLAS_FFMPEG_TIMEOUT_SECONDS", 1800)
