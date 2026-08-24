from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from pathlib import PurePosixPath

import boto3
from botocore.config import Config

from media_worker import config


@dataclass(frozen=True)
class UploadedHlsAsset:
    storage_key: str
    relative_path: str
    content_type: str
    size_bytes: int
    sha256: str


class ObjectStorage:
    def __init__(self) -> None:
        self._originals_bucket = config.originals_bucket()
        self._processed_bucket = config.processed_bucket()
        self._client = boto3.client(
            "s3",
            endpoint_url=config.minio_endpoint(),
            aws_access_key_id=config.minio_access_key(),
            aws_secret_access_key=config.minio_secret_key(),
            region_name=config.minio_region(),
            config=Config(signature_version="s3v4"),
        )

    def download_original(self, key: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        self._client.download_file(self._originals_bucket, key, str(destination))

    def upload_hls_tree(self, *, video_id: str, generation: str, hls_root: Path) -> list[UploadedHlsAsset]:
        prefix = _attempt_hls_prefix(video_id=video_id, generation=generation)
        uploaded: list[UploadedHlsAsset] = []
        for path in sorted(hls_root.rglob("*")):
            if not path.is_file():
                continue
            relative = _safe_relative_path(path, hls_root)
            content_type = _content_type(path)
            size_bytes, sha256 = _file_metadata(path)
            key = f"{prefix}{relative}"
            self._client.upload_file(
                str(path),
                self._processed_bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            )
            uploaded.append(
                UploadedHlsAsset(
                    storage_key=key,
                    relative_path=relative,
                    content_type=content_type,
                    size_bytes=size_bytes,
                    sha256=sha256,
                )
            )
        return uploaded

    def delete_hls_tree(self, *, video_id: str, generation: str) -> int:
        prefix = _attempt_hls_prefix(video_id=video_id, generation=generation)
        deleted = 0
        continuation_token: str | None = None
        while True:
            response = self._client.list_objects_v2(
                Bucket=self._processed_bucket,
                Prefix=prefix,
                **({"ContinuationToken": continuation_token} if continuation_token else {}),
            )
            objects = [{"Key": item["Key"]} for item in response.get("Contents", [])]
            if objects:
                self._client.delete_objects(Bucket=self._processed_bucket, Delete={"Objects": objects, "Quiet": True})
                deleted += len(objects)
            if not response.get("IsTruncated"):
                return deleted
            continuation_token = response.get("NextContinuationToken")


def _attempt_hls_prefix(*, video_id: str, generation: str) -> str:
    _validate_key_component(video_id, "video_id")
    _validate_key_component(generation, "generation")
    return f"processed/{video_id}/attempts/{generation}/hls/"


def _validate_key_component(value: str, name: str) -> None:
    if not value or Path(value).is_absolute() or "/" in value or "\\" in value or value in {".", ".."}:
        raise ValueError(f"{name} must be a single safe storage-key component")


def _safe_relative_path(path: Path, root: Path) -> str:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    try:
        relative = resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("HLS asset must be inside the HLS root") from exc
    relative_posix = PurePosixPath(relative.as_posix())
    if relative_posix.is_absolute() or not relative_posix.parts or ".." in relative_posix.parts:
        raise ValueError("HLS asset path must be relative and traversal-free")
    return relative_posix.as_posix()


def _file_metadata(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size_bytes = 0
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            size_bytes += len(chunk)
            digest.update(chunk)
    return size_bytes, digest.hexdigest()


def _content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".m3u8":
        return "application/vnd.apple.mpegurl"
    if suffix == ".ts":
        return "video/mp2t"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    return "application/octet-stream"
