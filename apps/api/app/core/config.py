from __future__ import annotations

import os


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def database_url() -> str:
    raw = env("DATABASE_URL", "postgresql+asyncpg://atlas:atlas@postgres:5432/atlas_prime")
    if raw.startswith("postgresql://"):
        return raw.replace("postgresql://", "postgresql+asyncpg://", 1)
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


def upload_max_bytes() -> int:
    raw = env("ATLAS_UPLOAD_MAX_BYTES", str(100 * 1024 * 1024))
    try:
        return int(raw)
    except ValueError:
        return 100 * 1024 * 1024


def celery_broker_url() -> str:
    return env("CELERY_BROKER_URL", env("REDIS_URL", "redis://redis:6379/0"))


def celery_result_backend() -> str:
    return env("CELERY_RESULT_BACKEND", "redis://redis:6379/1")
