from __future__ import annotations

from enum import StrEnum


class VideoStatus(StrEnum):
    DRAFT = "draft"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROBING = "probing"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class VideoPrivacy(StrEnum):
    PRIVATE = "private"
    PUBLIC = "public"
    UNLISTED = "unlisted"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class RenditionStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


CANONICAL_VIDEO_STATUS_VALUES = [status.value for status in VideoStatus]
PRIVACY_VALUES = [privacy.value for privacy in VideoPrivacy]

ALLOWED_VIDEO_TRANSITIONS: dict[VideoStatus, set[VideoStatus]] = {
    VideoStatus.DRAFT: {VideoStatus.UPLOADING, VideoStatus.FAILED},
    VideoStatus.UPLOADING: {VideoStatus.UPLOADED, VideoStatus.FAILED},
    VideoStatus.UPLOADED: {VideoStatus.QUEUED, VideoStatus.FAILED},
    VideoStatus.QUEUED: {VideoStatus.PROBING, VideoStatus.PROCESSING, VideoStatus.FAILED},
    VideoStatus.PROBING: {VideoStatus.PROCESSING, VideoStatus.FAILED},
    VideoStatus.PROCESSING: {VideoStatus.READY, VideoStatus.FAILED},
    VideoStatus.READY: set(),
    VideoStatus.FAILED: {VideoStatus.UPLOADING, VideoStatus.QUEUED},
}


class InvalidStatusTransition(ValueError):
    def __init__(self, current: VideoStatus, target: VideoStatus) -> None:
        super().__init__(f"invalid video status transition: {current.value} -> {target.value}")
        self.current = current
        self.target = target


def can_transition_video(current: VideoStatus, target: VideoStatus) -> bool:
    if current == target:
        return True
    return target in ALLOWED_VIDEO_TRANSITIONS[current]


def validate_video_transition(current: VideoStatus, target: VideoStatus) -> None:
    if not can_transition_video(current, target):
        raise InvalidStatusTransition(current, target)
