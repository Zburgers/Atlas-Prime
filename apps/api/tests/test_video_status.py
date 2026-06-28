import pytest

from app.domain.status import InvalidStatusTransition, VideoStatus, can_transition_video, validate_video_transition


def test_canonical_lifecycle_transitions_are_allowed() -> None:
    path = [
        VideoStatus.DRAFT,
        VideoStatus.UPLOADING,
        VideoStatus.UPLOADED,
        VideoStatus.QUEUED,
        VideoStatus.PROBING,
        VideoStatus.PROCESSING,
        VideoStatus.READY,
    ]

    for current, target in zip(path, path[1:]):
        assert can_transition_video(current, target)


def test_invalid_lifecycle_jump_is_rejected() -> None:
    with pytest.raises(InvalidStatusTransition):
        validate_video_transition(VideoStatus.DRAFT, VideoStatus.READY)
