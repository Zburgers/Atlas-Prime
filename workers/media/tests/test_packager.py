from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from media_worker.packager import MediaProbe, ProcessingError, package_to_hls, probe_media, rendition_plan_for
from media_worker.storage import ObjectStorage


def test_probe_and_package_sample_fixture(tmp_path: Path) -> None:
    fixture = _sample_fixture(tmp_path)
    video_id = "00000000-0000-0000-0000-000000000001"
    generation = "generation-a"

    probe = probe_media(fixture)
    plans = rendition_plan_for(probe)
    result = package_to_hls(
        video_id=video_id,
        generation=generation,
        source=fixture,
        output_root=tmp_path,
        probe=probe,
    )

    assert probe.width == 640
    assert probe.height == 360
    assert probe.video_codec
    assert probe.audio_codec
    assert [plan.label for plan in plans] == ["360p"]
    assert (result.hls_root / "master.m3u8").read_text(encoding="utf-8").startswith("#EXTM3U")
    assert (result.hls_root / "360p" / "playlist.m3u8").exists()
    assert list((result.hls_root / "360p").glob("segment_*.ts"))
    assert (result.hls_root / "thumbnail.jpg").stat().st_size > 0
    assert result.master_storage_key.endswith("/hls/master.m3u8")
    assert result.thumbnail_storage_key.endswith("/hls/thumbnail.jpg")
    assert result.generation == generation
    assert result.master_storage_key == f"processed/{video_id}/attempts/{generation}/hls/master.m3u8"
    assert result.renditions[0].playlist_storage_key == (
        f"processed/{video_id}/attempts/{generation}/hls/360p/playlist.m3u8"
    )
    assert result.generated_thumbnail_storage_keys == [
        result.thumbnail_storage_key,
        f"processed/{video_id}/attempts/{generation}/hls/thumbnail_02.jpg",
        f"processed/{video_id}/attempts/{generation}/hls/thumbnail_03.jpg",
    ]
    assert (result.hls_root / "thumbnail_02.jpg").stat().st_size > 0
    assert (result.hls_root / "thumbnail_03.jpg").stat().st_size > 0
    assert len(result.renditions) == 1


def test_probe_rejects_unreadable_media(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.mp4"
    bad_file.write_bytes(b"not a real media file")

    with pytest.raises(ProcessingError) as exc_info:
        probe_media(bad_file)

    assert exc_info.value.code == "MEDIA_COMMAND_FAILED"


def test_rendition_plan_expands_without_upscaling() -> None:
    plans = rendition_plan_for(MediaProbe(duration_seconds=1, width=1920, height=1080, video_codec="h264", audio_codec="aac", source_bitrate=6_000_000, has_audio=True))
    assert [plan.label for plan in plans] == ["1080p", "720p", "480p", "360p"]


def test_upload_returns_typed_attempt_asset_inventory(tmp_path: Path) -> None:
    hls_root = tmp_path / "hls"
    asset = hls_root / "360p" / "playlist.m3u8"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"#EXTM3U\n")
    fake_client = _FakeS3Client()
    storage = _storage_with_client(fake_client)

    uploaded = storage.upload_hls_tree(video_id="video-1", generation="generation-a", hls_root=hls_root)

    assert len(uploaded) == 1
    assert uploaded[0].storage_key == "processed/video-1/attempts/generation-a/hls/360p/playlist.m3u8"
    assert uploaded[0].relative_path == "360p/playlist.m3u8"
    assert uploaded[0].content_type == "application/vnd.apple.mpegurl"
    assert uploaded[0].size_bytes == len(b"#EXTM3U\n")
    assert uploaded[0].sha256 == hashlib.sha256(b"#EXTM3U\n").hexdigest()


def test_failure_on_nth_upload_can_cleanup_only_that_attempt(tmp_path: Path) -> None:
    hls_root = tmp_path / "hls"
    hls_root.mkdir()
    (hls_root / "master.m3u8").write_text("master", encoding="utf-8")
    (hls_root / "360p").mkdir()
    (hls_root / "360p" / "playlist.m3u8").write_text("playlist", encoding="utf-8")
    fake_client = _FakeS3Client(fail_on_upload=2)
    storage = _storage_with_client(fake_client)

    with pytest.raises(RuntimeError, match="upload 2 failed"):
        storage.upload_hls_tree(video_id="video-1", generation="generation-a", hls_root=hls_root)

    storage.delete_hls_tree(video_id="video-1", generation="generation-a")

    assert fake_client.objects == {}


def test_cleanup_cannot_delete_other_generation_or_legacy_tree() -> None:
    fake_client = _FakeS3Client(
        objects={
            "processed/video-1/attempts/generation-a/hls/master.m3u8": b"a",
            "processed/video-1/attempts/generation-b/hls/master.m3u8": b"b",
            "processed/video-1/hls/master.m3u8": b"published",
        }
    )
    storage = _storage_with_client(fake_client)

    assert storage.delete_hls_tree(video_id="video-1", generation="generation-a") == 1
    assert fake_client.objects == {
        "processed/video-1/attempts/generation-b/hls/master.m3u8": b"b",
        "processed/video-1/hls/master.m3u8": b"published",
    }
    assert storage.delete_hls_tree(video_id="video-1", generation="generation-a") == 0


class _FakeS3Client:
    def __init__(self, *, objects: dict[str, bytes] | None = None, fail_on_upload: int | None = None) -> None:
        self.objects = objects or {}
        self.fail_on_upload = fail_on_upload
        self.upload_count = 0

    def upload_file(self, filename: str, bucket: str, key: str, *, ExtraArgs: dict[str, str]) -> None:
        del bucket, ExtraArgs
        self.upload_count += 1
        if self.upload_count == self.fail_on_upload:
            raise RuntimeError(f"upload {self.upload_count} failed")
        self.objects[key] = Path(filename).read_bytes()

    def list_objects_v2(self, *, Bucket: str, Prefix: str, **kwargs: str) -> dict[str, object]:
        del Bucket, kwargs
        return {
            "Contents": [{"Key": key} for key in sorted(self.objects) if key.startswith(Prefix)],
            "IsTruncated": False,
        }

    def delete_objects(self, *, Bucket: str, Delete: dict[str, object]) -> dict[str, object]:
        del Bucket
        for item in Delete["Objects"]:
            assert isinstance(item, dict)
            self.objects.pop(item["Key"], None)
        return {}


def _storage_with_client(client: _FakeS3Client) -> ObjectStorage:
    storage = ObjectStorage.__new__(ObjectStorage)
    storage._processed_bucket = "processed-test"
    storage._client = client
    return storage


def _sample_fixture(tmp_path: Path) -> Path:
    for parent in Path(__file__).resolve().parents:
        repo_fixture = parent / "fixtures" / "media" / "sample-2s.mp4"
        if repo_fixture.exists():
            return repo_fixture

    generated = tmp_path / "sample-2s.mp4"
    import subprocess

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=640x360:rate=24",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=1000:sample_rate=48000",
            "-t",
            "2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            "-movflags",
            "+faststart",
            str(generated),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return generated
