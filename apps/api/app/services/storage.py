from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO
from uuid import UUID

import boto3
from botocore.exceptions import ClientError
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

    def delete_original(self, *, key: str) -> None:
        raise NotImplementedError


class HlsObjectNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class HlsObject:
    key: str
    body: bytes
    content_type: str | None
    content_length: int | None
    etag: str | None


class ProcessedHlsStorage:
    def get_hls_object(self, *, key: str) -> HlsObject:
        raise NotImplementedError

    def put_thumbnail(self, *, key: str, body: BinaryIO, content_type: str) -> None:
        raise NotImplementedError

    def put_caption(self, *, key: str, body: BinaryIO, content_type: str) -> None:
        raise NotImplementedError

    def get_caption(self, *, key: str) -> HlsObject:
        raise NotImplementedError

    def delete_video_tree(self, *, video_id: UUID) -> int:
        raise NotImplementedError

    def presign_hls_object(self, *, key: str, expires_in: int) -> str:
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

    def delete_original(self, *, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)


class MinioProcessedHlsStorage(ProcessedHlsStorage):
    def __init__(self) -> None:
        self._bucket = config.processed_bucket()
        self._client = _s3_client(config.minio_endpoint())
        public_endpoint = config.minio_public_endpoint()
        self._presign_client = self._client if not public_endpoint else _s3_client(public_endpoint)

    def get_hls_object(self, *, key: str) -> HlsObject:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in {"NoSuchKey", "404", "NotFound"}:
                raise HlsObjectNotFoundError(key) from exc
            raise

        with response["Body"] as body:
            data = body.read()
        return HlsObject(
            key=key,
            body=data,
            content_type=response.get("ContentType"),
            content_length=response.get("ContentLength"),
            etag=response.get("ETag"),
        )

    def put_thumbnail(self, *, key: str, body: BinaryIO, content_type: str) -> None:
        body.seek(0)
        self._client.upload_fileobj(body, self._bucket, key, ExtraArgs={"ContentType": content_type})

    def put_caption(self, *, key: str, body: BinaryIO, content_type: str) -> None:
        body.seek(0)
        self._client.upload_fileobj(body, self._bucket, key, ExtraArgs={"ContentType": content_type})

    def get_caption(self, *, key: str) -> HlsObject:
        return self.get_hls_object(key=key)

    def delete_video_tree(self, *, video_id: UUID) -> int:
        prefix = f"processed/{video_id}/"
        deleted = 0
        continuation_token: str | None = None
        while True:
            response = self._client.list_objects_v2(
                Bucket=self._bucket,
                Prefix=prefix,
                **({"ContinuationToken": continuation_token} if continuation_token else {}),
            )
            objects = [{"Key": item["Key"]} for item in response.get("Contents", [])]
            if objects:
                delete_response = self._client.delete_objects(Bucket=self._bucket, Delete={"Objects": objects, "Quiet": True})
                if delete_response.get("Errors"):
                    raise RuntimeError(f"processed object deletion failed for video {video_id}")
                deleted += len(objects)
            if not response.get("IsTruncated"):
                return deleted
            continuation_token = response.get("NextContinuationToken")
            if not continuation_token:
                raise RuntimeError(f"processed object listing did not provide a continuation token for video {video_id}")

    def presign_hls_object(self, *, key: str, expires_in: int) -> str:
        return self._presign_client.generate_presigned_url("get_object", Params={"Bucket": self._bucket, "Key": key}, ExpiresIn=expires_in)


def _s3_client(endpoint_url: str) -> object:
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=config.minio_access_key(),
        aws_secret_access_key=config.minio_secret_key(),
        region_name=config.minio_region(),
        config=Config(signature_version="s3v4"),
    )


def original_storage_key(video_id: UUID, extension: str) -> str:
    normalized = extension.lower().lstrip(".")
    return f"originals/{video_id}/source.{normalized}"
