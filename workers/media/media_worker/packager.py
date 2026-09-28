from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

from media_worker import config


class ProcessingError(RuntimeError):
    def __init__(self, code: str, safe_message: str, detail: str | None = None, *, reason: str | None = None) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message
        self.detail = detail or safe_message
        self.reason = reason


@dataclass(frozen=True)
class MediaProbe:
    duration_seconds: float | None
    width: int | None
    height: int | None
    video_codec: str | None
    audio_codec: str | None
    source_bitrate: int | None
    has_audio: bool
    duration_exact: Fraction | None = None
    effective_width: int | None = None
    effective_height: int | None = None
    rotation_degrees: int | None = 0
    frame_rate: Fraction | None = None


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
    video_codec: str
    segment_count: int
    output_size_bytes: int
    playlist_storage_key: str


@dataclass(frozen=True)
class PackageResult:
    generation: str
    hls_root: Path
    master_storage_key: str
    thumbnail_storage_key: str
    generated_thumbnail_storage_keys: list[str]
    renditions: list[PackagedRendition]


RENDITION_LADDER = (
    RenditionPlan(label="1080p", width=1920, height=1080, target_bitrate=5_000_000),
    RenditionPlan(label="720p", width=1280, height=720, target_bitrate=2_800_000),
    RenditionPlan(label="480p", width=854, height=480, target_bitrate=1_400_000),
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


def _parse_finite_fraction(value: Any) -> Fraction | None:
    if value is None or isinstance(value, bool):
        return None
    text = str(value)
    if len(text) > 128:
        return None
    try:
        return Fraction(text)
    except (ValueError, ZeroDivisionError, OverflowError):
        return None


def _parse_positive_fraction(value: Any) -> Fraction | None:
    parsed = _parse_finite_fraction(value)
    return parsed if parsed is not None and parsed > 0 else None


def _parse_positive_dimension(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if not isinstance(value, str) or not value.isdecimal():
        return None
    parsed = int(value)
    return parsed if parsed > 0 else None


def _display_rotation(video_stream: dict[str, Any]) -> int | None:
    side_data = video_stream.get("side_data_list", [])
    if not isinstance(side_data, list):
        return None
    rotations: set[int] = set()
    for item in side_data:
        if not isinstance(item, dict):
            return None
        if item.get("side_data_type") != "Display Matrix" or "rotation" not in item:
            continue
        rotation = _parse_finite_fraction(item["rotation"])
        if rotation is None:
            return None
        normalized = rotation % 360
        if normalized.denominator != 1 or int(normalized) not in (0, 90, 180, 270):
            return None
        rotations.add(int(normalized))
    return next(iter(rotations), 0) if len(rotations) <= 1 else None


def _policy_rejection(reason: str) -> ProcessingError:
    return ProcessingError(
        "MEDIA_POLICY_REJECTED",
        f"Uploaded media was rejected by policy ({reason})",
        reason=reason,
    )


def _parse_int(value: Any) -> int | None:
    if value in (None, "", "N/A"):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError, OverflowError):
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
        "-show_entries",
        "stream=codec_type,codec_name,width,height,duration,avg_frame_rate,r_frame_rate,bit_rate:stream_side_data=side_data_type,rotation:format=duration,bit_rate",
        str(source),
    ]
    try:
        result = _run(command, timeout=30)
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ProcessingError("FFPROBE_INVALID_JSON", "Could not inspect media", str(exc)) from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("streams"), list):
        raise _policy_rejection("metadata")
    streams = payload["streams"]
    if any(not isinstance(stream, dict) for stream in streams):
        raise _policy_rejection("metadata")
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    if not video_stream:
        raise ProcessingError("NO_VIDEO_STREAM", "Uploaded file does not contain a video stream")

    width = _parse_positive_dimension(video_stream.get("width"))
    height = _parse_positive_dimension(video_stream.get("height"))
    rotation = _display_rotation(video_stream)
    effective_width = effective_height = None
    if width is not None and height is not None and rotation is not None:
        effective_width, effective_height = (height, width) if rotation in (90, 270) else (width, height)

    format_data = payload.get("format") or {}
    if not isinstance(format_data, dict):
        raise _policy_rejection("metadata")
    durations = [
        duration
        for duration in (
            _parse_positive_fraction(video_stream.get("duration")),
            _parse_positive_fraction(format_data.get("duration")),
        )
        if duration is not None
    ]
    duration_exact = max(durations) if durations else None
    try:
        duration_seconds = float(duration_exact) if duration_exact is not None else None
        if duration_seconds is not None and not (duration_seconds > 0 and duration_seconds < float("inf")):
            duration_seconds = None
    except OverflowError:
        duration_seconds = None
    rates = [
        rate
        for rate in (
            _parse_positive_fraction(video_stream.get("avg_frame_rate")),
            _parse_positive_fraction(video_stream.get("r_frame_rate")),
        )
        if rate is not None
    ]
    source_bitrate = _parse_int(format_data.get("bit_rate")) or _parse_int(video_stream.get("bit_rate"))

    return MediaProbe(
        duration_seconds=duration_seconds,
        width=width,
        height=height,
        video_codec=video_stream.get("codec_name"),
        audio_codec=audio_stream.get("codec_name") if audio_stream else None,
        source_bitrate=source_bitrate,
        has_audio=audio_stream is not None,
        duration_exact=duration_exact,
        effective_width=effective_width,
        effective_height=effective_height,
        rotation_degrees=rotation,
        frame_rate=max(rates) if rates else None,
    )


def validate_media_policy(probe: MediaProbe, policy: config.MediaAdmissionPolicy) -> None:
    if (
        probe.duration_exact is None
        or probe.duration_exact <= 0
        or probe.width is None
        or probe.height is None
        or probe.width <= 0
        or probe.height <= 0
        or probe.effective_width is None
        or probe.effective_height is None
        or probe.effective_width <= 0
        or probe.effective_height <= 0
        or probe.rotation_degrees is None
        or probe.rotation_degrees not in (0, 90, 180, 270)
        or probe.frame_rate is None
        or probe.frame_rate <= 0
    ):
        raise _policy_rejection("metadata")
    if probe.duration_exact > policy.max_duration_seconds:
        raise _policy_rejection("duration")
    area = probe.effective_width * probe.effective_height
    if (
        probe.effective_width > policy.max_width
        or probe.effective_height > policy.max_height
        or area > policy.max_pixel_area
    ):
        raise _policy_rejection("dimensions")
    expected_dimensions = (
        (probe.height, probe.width) if probe.rotation_degrees in (90, 270) else (probe.width, probe.height)
    )
    if (probe.effective_width, probe.effective_height) != expected_dimensions:
        raise _policy_rejection("metadata")
    if probe.frame_rate > policy.max_frame_rate:
        raise _policy_rejection("frame_rate")
    if area * probe.frame_rate * probe.duration_exact > policy.max_decoded_work_pixel_frames:
        raise _policy_rejection("work")


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


def package_to_hls(
    *, video_id: str, generation: str, source: Path, output_root: Path, probe: MediaProbe
) -> PackageResult:
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
        segment_count = len(list(rendition_dir.glob("segment_*.ts")))
        output_size_bytes = sum(path.stat().st_size for path in rendition_dir.iterdir() if path.is_file())
        renditions.append(
            PackagedRendition(
                label=plan.label,
                width=plan.width,
                height=plan.height,
                target_bitrate=plan.target_bitrate,
                video_codec="h264",
                segment_count=segment_count,
                output_size_bytes=output_size_bytes,
                playlist_storage_key=f"processed/{video_id}/attempts/{generation}/hls/{plan.label}/playlist.m3u8",
            )
        )

    thumbnail_offsets = _thumbnail_offsets(probe.duration_seconds)
    thumbnail_paths = [hls_root / "thumbnail.jpg", *[hls_root / f"thumbnail_{index:02d}.jpg" for index in range(2, len(thumbnail_offsets) + 1)]]
    for offset, thumbnail_path in zip(thumbnail_offsets, thumbnail_paths, strict=True):
        _run(["ffmpeg", "-y", "-ss", str(offset), "-i", str(source), "-frames:v", "1", "-q:v", "3", str(thumbnail_path)], timeout=30)
    _write_master_playlist(hls_root / "master.m3u8", renditions)
    return PackageResult(
        generation=generation,
        hls_root=hls_root,
        master_storage_key=f"processed/{video_id}/attempts/{generation}/hls/master.m3u8",
        thumbnail_storage_key=f"processed/{video_id}/attempts/{generation}/hls/thumbnail.jpg",
        generated_thumbnail_storage_keys=[
            f"processed/{video_id}/attempts/{generation}/hls/{path.name}" for path in thumbnail_paths
        ],
        renditions=renditions,
    )


def _thumbnail_offsets(duration_seconds: float | None) -> list[float]:
    if duration_seconds is None or duration_seconds <= 1:
        return [0.1]
    return [min(duration_seconds - 0.1, fraction * duration_seconds) for fraction in (0.1, 0.5, 0.9)]


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
