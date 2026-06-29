from __future__ import annotations

from pathlib import Path

import pytest

from media_worker.packager import ProcessingError, package_to_hls, probe_media, rendition_plan_for


def test_probe_and_package_sample_fixture(tmp_path: Path) -> None:
    fixture = _sample_fixture(tmp_path)

    probe = probe_media(fixture)
    plans = rendition_plan_for(probe)
    result = package_to_hls(
        video_id="00000000-0000-0000-0000-000000000001",
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
    assert len(result.renditions) == 1


def test_probe_rejects_unreadable_media(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.mp4"
    bad_file.write_bytes(b"not a real media file")

    with pytest.raises(ProcessingError) as exc_info:
        probe_media(bad_file)

    assert exc_info.value.code == "MEDIA_COMMAND_FAILED"


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
