from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from media_worker import config


class ProcessingError(RuntimeError):
    def __init__(self, code: str, safe_message: str, detail: str | None = None) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message
        self.detail = detail or safe_message


@dataclass(frozen=True)
class MediaProbe:
    duration_seconds: float | None
    width: int
    height: int
    video_codec: str | None
    audio_codec: str | None
    source_bitrate: int | None
    has_audio: bool


@dataclass(frozen=True)
class RenditionPlan:
    label: str
    width: int
    height: int
    target_bitrate: int

    @property
    def bandwidth(self) -> int:
        return int(self.target_bitrate * 1.15)


@dataclass(frozen=True)
class PackagedRendition:
    label: str
    width: int
    height: int
    target_bitrate: int
    playlist_storage_key: str


@dataclass(frozen=True)
class PackageResult:
    hls_root: Path
    master_storage_key: str
    thumbnail_storage_key: str
    renditions: list[PackagedRendition]


RENDITION_LADDER = (
    RenditionPlan(label="720p", width=1280, height=720, target_bitrate=2_800_000),
    RenditionPlan(label="360p", width=640, height=360, target_bitrate=800_000),
)


def _run(command: list[str], *, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout or config.ffmpeg_timeout_seconds(),
        )
    except subprocess.TimeoutExpired as exc:
        raise ProcessingError("MEDIA_COMMAND_TIMEOUT", "Media processing timed out", str(exc)) from exc
    except subprocess.CalledProcessError as exc:
        detail = "\n".join(part for part in [exc.stdout, exc.stderr] if part).strip()
        raise ProcessingError("MEDIA_COMMAND_FAILED", "Media processing command failed", detail) from exc


def _parse_float(value: Any) -> float | None:
    if value in (None, "", "N/A"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_int(value: Any) -> int | None:
    if value in (None, "", "N/A"):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def probe_media(source: Path) -> MediaProbe:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(source),
    ]
    try:
        result = _run(command, timeout=30)
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ProcessingError("FFPROBE_INVALID_JSON", "Could not inspect media", str(exc)) from exc

    streams = payload.get("streams") or []
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    if not video_stream:
        raise ProcessingError("NO_VIDEO_STREAM", "Uploaded file does not contain a video stream")

    width = _parse_int(video_stream.get("width"))
    height = _parse_int(video_stream.get("height"))
    if not width or not height:
        raise ProcessingError("INVALID_VIDEO_DIMENSIONS", "Uploaded video dimensions could not be read")

    format_data = payload.get("format") or {}
    duration = _parse_float(video_stream.get("duration")) or _parse_float(format_data.get("duration"))
    source_bitrate = _parse_int(format_data.get("bit_rate")) or _parse_int(video_stream.get("bit_rate"))

    return MediaProbe(
        duration_seconds=duration,
        width=width,
        height=height,
        video_codec=video_stream.get("codec_name"),
        audio_codec=audio_stream.get("codec_name") if audio_stream else None,
        source_bitrate=source_bitrate,
        has_audio=audio_stream is not None,
    )


def rendition_plan_for(probe: MediaProbe) -> list[RenditionPlan]:
    plans = [plan for plan in RENDITION_LADDER if probe.width >= plan.width and probe.height >= plan.height]
    if plans:
        return plans
    return [
        RenditionPlan(
            label=f"{probe.height}p",
            width=probe.width,
            height=probe.height,
            target_bitrate=min(probe.source_bitrate or 800_000, 800_000),
        )
    ]


def package_to_hls(*, video_id: str, source: Path, output_root: Path, probe: MediaProbe) -> PackageResult:
    hls_root = output_root / "hls"
    hls_root.mkdir(parents=True, exist_ok=True)
    plans = rendition_plan_for(probe)
    renditions: list[PackagedRendition] = []

    for plan in plans:
        rendition_dir = hls_root / plan.label
        rendition_dir.mkdir(parents=True, exist_ok=True)
        playlist_path = rendition_dir / "playlist.m3u8"
        segment_path = rendition_dir / "segment_%03d.ts"
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-map",
            "0:v:0",
        ]
        if probe.has_audio:
            command.extend(["-map", "0:a:0"])
        command.extend(
            [
                "-vf",
                f"scale=w={plan.width}:h={plan.height}:force_original_aspect_ratio=decrease,"
                f"pad={plan.width}:{plan.height}:(ow-iw)/2:(oh-ih)/2",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-profile:v",
                "main",
                "-pix_fmt",
                "yuv420p",
                "-crf",
                "23",
                "-maxrate",
                str(plan.target_bitrate),
                "-bufsize",
                str(plan.target_bitrate * 2),
                "-g",
                "48",
                "-keyint_min",
                "48",
                "-sc_threshold",
                "0",
            ]
        )
        if probe.has_audio:
            command.extend(["-c:a", "aac", "-b:a", "128k", "-ac", "2"])
        else:
            command.append("-an")
        command.extend(
            [
                "-f",
                "hls",
                "-hls_time",
                "2",
                "-hls_playlist_type",
                "vod",
                "-hls_segment_filename",
                str(segment_path),
                str(playlist_path),
            ]
        )
        _run(command)
        renditions.append(
            PackagedRendition(
                label=plan.label,
                width=plan.width,
                height=plan.height,
                target_bitrate=plan.target_bitrate,
                playlist_storage_key=f"processed/{video_id}/hls/{plan.label}/playlist.m3u8",
            )
        )

    thumbnail_path = hls_root / "thumbnail.jpg"
    _run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            "0.1",
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-q:v",
            "3",
            str(thumbnail_path),
        ],
        timeout=30,
    )
    _write_master_playlist(hls_root / "master.m3u8", renditions)
    return PackageResult(
        hls_root=hls_root,
        master_storage_key=f"processed/{video_id}/hls/master.m3u8",
        thumbnail_storage_key=f"processed/{video_id}/hls/thumbnail.jpg",
        renditions=renditions,
    )


def _write_master_playlist(path: Path, renditions: list[PackagedRendition]) -> None:
    lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
    for rendition in renditions:
        lines.append(
            "#EXT-X-STREAM-INF:"
            f"BANDWIDTH={int(rendition.target_bitrate * 1.15)},"
            f"RESOLUTION={rendition.width}x{rendition.height},"
            'CODECS="avc1.4d401f,mp4a.40.2"'
        )
        lines.append(f"{rendition.label}/playlist.m3u8")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
