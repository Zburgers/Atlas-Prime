from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO
from uuid import UUID

import boto3
from botocore.config import Config

from app.core import config


@dataclass(frozen=True)
class StoredObject:
    bucket: str
    key: str
    size_bytes: int
    content_type: str


class OriginalStorage:
    def put_original(
        self,
        *,
        video_id: UUID,
        extension: str,
        body: BinaryIO,
        size_bytes: int,
        content_type: str,
    ) -> StoredObject:
        raise NotImplementedError


class MinioOriginalStorage(OriginalStorage):
    def __init__(self) -> None:
        self._bucket = config.originals_bucket()
        self._client = boto3.client(
            "s3",
            endpoint_url=config.minio_endpoint(),
            aws_access_key_id=config.minio_access_key(),
            aws_secret_access_key=config.minio_secret_key(),
            region_name=config.minio_region(),
            config=Config(signature_version="s3v4"),
        )

    def put_original(
        self,
        *,
        video_id: UUID,
        extension: str,
        body: BinaryIO,
        size_bytes: int,
        content_type: str,
    ) -> StoredObject:
        key = original_storage_key(video_id, extension)
        body.seek(0)
        self._client.upload_fileobj(
            body,
            self._bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        return StoredObject(bucket=self._bucket, key=key, size_bytes=size_bytes, content_type=content_type)


def original_storage_key(video_id: UUID, extension: str) -> str:
    normalized = extension.lower().lstrip(".")
    return f"originals/{video_id}/source.{normalized}"
