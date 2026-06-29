from __future__ import annotations

from pathlib import Path

import boto3
from botocore.config import Config

from media_worker import config


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

    def upload_hls_tree(self, *, video_id: str, hls_root: Path) -> list[str]:
        uploaded: list[str] = []
        for path in sorted(hls_root.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(hls_root).as_posix()
            key = f"processed/{video_id}/hls/{relative}"
            self._client.upload_file(
                str(path),
                self._processed_bucket,
                key,
                ExtraArgs={"ContentType": _content_type(path)},
            )
            uploaded.append(key)
        return uploaded


def _content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".m3u8":
        return "application/vnd.apple.mpegurl"
    if suffix == ".ts":
        return "video/mp2t"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    return "application/octet-stream"
