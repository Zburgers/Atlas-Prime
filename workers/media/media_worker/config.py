from __future__ import annotations

import os


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
    raw = env("ATLAS_FFMPEG_TIMEOUT_SECONDS", "120")
    try:
        return int(raw)
    except ValueError:
        return 120
