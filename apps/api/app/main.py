import os
from typing import Any

import asyncpg
import boto3
from botocore.config import Config
from fastapi import FastAPI
from redis.asyncio import from_url as redis_from_url

from app.api.admin import router as admin_router
from app.api.videos import router as videos_router
from app.domain.status import CANONICAL_VIDEO_STATUS_VALUES, PRIVACY_VALUES

STATUS_VALUES = CANONICAL_VIDEO_STATUS_VALUES

app = FastAPI(title="Atlas Prime API", version="0.0.1")
app.include_router(videos_router)
app.include_router(admin_router)


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _skip_dependency_checks() -> bool:
    return _env("ATLAS_HEALTH_SKIP_DEPENDENCIES").lower() in {"1", "true", "yes"}


async def _check_postgres() -> dict[str, Any]:
    conn = await asyncpg.connect(_env("DATABASE_URL"))
    try:
        value = await conn.fetchval("select 1")
        return {"ok": value == 1}
    finally:
        await conn.close()


async def _check_redis() -> dict[str, Any]:
    client = redis_from_url(_env("REDIS_URL", "redis://redis:6379/0"))
    try:
        return {"ok": bool(await client.ping())}
    finally:
        await client.aclose()


def _check_minio() -> dict[str, Any]:
    client = boto3.client(
        "s3",
        endpoint_url=_env("MINIO_ENDPOINT", "http://minio:9000"),
        aws_access_key_id=_env("MINIO_ACCESS_KEY", _env("MINIO_ROOT_USER")),
        aws_secret_access_key=_env("MINIO_SECRET_KEY", _env("MINIO_ROOT_PASSWORD")),
        region_name=_env("MINIO_REGION", "us-east-1"),
        config=Config(signature_version="s3v4"),
    )
    buckets = {bucket["Name"] for bucket in client.list_buckets().get("Buckets", [])}
    required = {
        _env("MINIO_BUCKET_ORIGINALS", "atlas-originals"),
        _env("MINIO_BUCKET_PROCESSED", "atlas-processed"),
    }
    return {"ok": required.issubset(buckets), "buckets": sorted(required)}


@app.get("/healthz/live")
async def live() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    if _skip_dependency_checks():
        return {
            "status": "ok",
            "service": "api",
            "dependencies": "skipped",
        }

    checks: dict[str, Any] = {
        "postgres": await _check_postgres(),
        "redis": await _check_redis(),
        "minio": _check_minio(),
    }
    status = "ok" if all(check["ok"] for check in checks.values()) else "degraded"
    return {"status": status, "service": "api", "dependencies": checks}


@app.get("/dev/mvp-contract")
async def mvp_contract() -> dict[str, Any]:
    return {
        "service": "api",
        "video_status_values": STATUS_VALUES,
        "privacy_values": PRIVACY_VALUES,
        "default_privacy": "private",
        "upload_transport": "api-mediated",
        "playback_delivery": "api-proxied-hls",
        "auth": {
            "provider": "clerk",
            "api_token_sources": ["authorization_bearer", "__session_cookie"],
            "dev_headers_enabled": _env("ATLAS_ALLOW_DEV_AUTH_HEADERS").lower() in {"1", "true", "yes"},
        },
        "storage": {
            "originals_bucket": _env("MINIO_BUCKET_ORIGINALS", "atlas-originals"),
            "processed_bucket": _env("MINIO_BUCKET_PROCESSED", "atlas-processed"),
            "processed_hls_prefix": "processed/{video_id}/hls/",
        },
        "smoke_coverage": {
            "core_video_metadata_and_processing_status": "implemented-by-sector-b",
            "upload_process_playback_metadata": "upload-storage-worker-proxy-pending-sectors-c-d-e",
            "cross_user_private_playback_denial": "implemented-by-sector-f-api-tests",
        },
    }
