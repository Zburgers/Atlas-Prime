from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest

from media_worker import config, packager
from media_worker.packager import (
    MediaProbe,
    ProcessingError,
    package_to_hls,
    probe_media,
    rendition_plan_for,
    validate_media_policy,
)
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
    assert probe.duration_exact == Fraction(2)
    assert probe.frame_rate == Fraction(24)
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


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"duration_exact": Fraction("600.0001")}, "duration"),
        ({"effective_width": 1921}, "dimensions"),
        ({"effective_height": 1921}, "dimensions"),
        ({"effective_width": 1920, "effective_height": 1081}, "dimensions"),
        ({"frame_rate": Fraction(30001, 1000)}, "frame_rate"),
        ({"effective_width": 0}, "metadata"),
        ({"frame_rate": Fraction(0)}, "metadata"),
        ({"duration_exact": None}, "metadata"),
        ({"effective_width": None}, "metadata"),
        ({"rotation_degrees": None}, "metadata"),
        ({"frame_rate": None}, "metadata"),
    ],
)
def test_media_admission_rejects_over_limit_or_missing_metadata(changes, reason: str) -> None:
    probe = replace(_admission_probe(), **changes)

    with pytest.raises(ProcessingError) as exc_info:
        validate_media_policy(probe, config.media_admission_policy())

    assert exc_info.value.code == "MEDIA_POLICY_REJECTED"
    assert exc_info.value.reason == reason
    assert exc_info.value.safe_message == f"Uploaded media was rejected by policy ({reason})"


def test_media_admission_accepts_exact_all_limits() -> None:
    validate_media_policy(
        _admission_probe(
            duration=Fraction(600),
            width=1920,
            height=1080,
            frame_rate=Fraction(30),
        ),
        config.media_admission_policy(),
    )


def test_media_admission_checks_decoded_work_exactly() -> None:
    exact = _admission_probe(duration=Fraction(600), width=1920, height=1080, frame_rate=Fraction(30))
    policy = replace(config.media_admission_policy(), max_decoded_work_pixel_frames=37_324_799_999)

    with pytest.raises(ProcessingError) as exc_info:
        validate_media_policy(exact, policy)

    assert exc_info.value.reason == "work"


@pytest.mark.parametrize(
    ("stream_duration", "format_duration", "avg_rate", "r_rate", "rotation", "expected_duration", "expected_rate", "expected_dims"),
    [
        ("599/1", "600.0", "24000/1001", "30/1", None, Fraction(600), Fraction(30), (1920, 1080)),
        ("N/A", "2.5", "N/A", "24000/1001", {"rotation": -90}, Fraction(5, 2), Fraction(24000, 1001), (1080, 1920)),
        ("nan", "inf", "0/0", "N/A", None, None, None, (1920, 1080)),
    ],
)
def test_probe_normalizes_duration_rate_and_display_rotation(
    monkeypatch,
    tmp_path: Path,
    stream_duration,
    format_duration,
    avg_rate,
    r_rate,
    rotation,
    expected_duration,
    expected_rate,
    expected_dims,
) -> None:
    stream = {
        "codec_type": "video",
        "codec_name": "h264",
        "width": 1920,
        "height": 1080,
        "duration": stream_duration,
        "avg_frame_rate": avg_rate,
        "r_frame_rate": r_rate,
    }
    if rotation is not None:
        stream["side_data_list"] = [{"side_data_type": "Display Matrix", **rotation}]
    command_seen: list[list[str]] = []

    def fake_run(command: list[str], *, timeout: int | None = None):
        command_seen.append(command)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"streams": [stream], "format": {"duration": format_duration}}),
            stderr="",
        )

    monkeypatch.setattr(packager, "_run", fake_run)
    probe = probe_media(tmp_path / "source.mp4")

    assert len(command_seen) == 1
    assert "-print_format" in command_seen[0] and "json" in command_seen[0]
    assert "-show_entries" in command_seen[0]
    assert probe.duration_exact == expected_duration
    assert probe.frame_rate == expected_rate
    assert (probe.effective_width, probe.effective_height) == expected_dims
    if expected_duration is not None and expected_rate is not None:
        validate_media_policy(probe, config.media_admission_policy())


@pytest.mark.parametrize("rotation", ["45", "nan", "inf", "bad"])
def test_probe_marks_invalid_display_rotation_as_metadata(monkeypatch, tmp_path: Path, rotation: str) -> None:
    payload = {
        "streams": [
            {
                "codec_type": "video",
                "width": 640,
                "height": 360,
                "duration": "2",
                "avg_frame_rate": "24/1",
                "r_frame_rate": "24/1",
                "side_data_list": [{"side_data_type": "Display Matrix", "rotation": rotation}],
            }
        ],
        "format": {},
    }
    monkeypatch.setattr(
        packager,
        "_run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, json.dumps(payload), ""),
    )

    probe = probe_media(tmp_path / "source.mp4")
    with pytest.raises(ProcessingError) as exc_info:
        validate_media_policy(probe, config.media_admission_policy())
    assert exc_info.value.reason == "metadata"


@pytest.mark.parametrize("dimensions", [(None, 360), (0, 360), (-1, 360), (640, "360.0")])
def test_probe_rejects_malformed_dimensions_as_policy_metadata(monkeypatch, tmp_path: Path, dimensions) -> None:
    payload = {
        "streams": [
            {
                "codec_type": "video",
                "width": dimensions[0],
                "height": dimensions[1],
                "duration": "2",
                "avg_frame_rate": "24/1",
                "r_frame_rate": "24/1",
            }
        ],
        "format": {},
    }
    monkeypatch.setattr(
        packager,
        "_run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, json.dumps(payload), ""),
    )

    probe = probe_media(tmp_path / "source.mp4")
    with pytest.raises(ProcessingError) as exc_info:
        validate_media_policy(probe, config.media_admission_policy())
    assert exc_info.value.reason == "metadata"


def test_media_policy_configuration_fails_closed(monkeypatch) -> None:
    monkeypatch.setenv("ATLAS_MEDIA_MAX_DURATION_SECONDS", "not-a-number")
    with pytest.raises(ValueError, match="ATLAS_MEDIA_MAX_DURATION_SECONDS"):
        config.media_admission_policy()

    monkeypatch.setenv("ATLAS_MEDIA_MAX_DURATION_SECONDS", "601")
    with pytest.raises(ValueError, match="ATLAS_MEDIA_MAX_DURATION_SECONDS"):
        config.media_admission_policy()

    monkeypatch.delenv("ATLAS_MEDIA_MAX_DURATION_SECONDS")
    monkeypatch.setenv("ATLAS_MEDIA_MAX_FRAME_RATE", "30/0")
    with pytest.raises(ValueError, match="ATLAS_MEDIA_MAX_FRAME_RATE"):
        config.media_admission_policy()

    monkeypatch.delenv("ATLAS_MEDIA_MAX_FRAME_RATE")
    monkeypatch.setenv("ATLAS_MEDIA_MAX_PIXEL_AREA", "2073601")
    with pytest.raises(ValueError, match="ATLAS_MEDIA_MAX_PIXEL_AREA"):
        config.media_admission_policy()


def test_ffmpeg_timeout_default_and_invalid_configuration(monkeypatch) -> None:
    monkeypatch.delenv("ATLAS_FFMPEG_TIMEOUT_SECONDS", raising=False)
    assert config.ffmpeg_timeout_seconds() == 1800
    monkeypatch.setenv("ATLAS_FFMPEG_TIMEOUT_SECONDS", "bad")
    with pytest.raises(ValueError, match="ATLAS_FFMPEG_TIMEOUT_SECONDS"):
        config.ffmpeg_timeout_seconds()
    monkeypatch.setenv("ATLAS_FFMPEG_TIMEOUT_SECONDS", "2000")
    assert config.ffmpeg_timeout_seconds() == 2000


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


def _admission_probe(
    *,
    duration: Fraction = Fraction(1),
    width: int = 640,
    height: int = 360,
    frame_rate: Fraction = Fraction(24),
) -> MediaProbe:
    return MediaProbe(
        duration_seconds=float(duration),
        width=width,
        height=height,
        video_codec="h264",
        audio_codec="aac",
        source_bitrate=1000,
        has_audio=True,
        duration_exact=duration,
        effective_width=width,
        effective_height=height,
        rotation_degrees=0,
        frame_rate=frame_rate,
    )
