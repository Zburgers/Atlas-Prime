import pytest
from app.db.models import Video, VideoProcessingJob
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


def test_processing_generation_columns_and_active_job_index_are_declared() -> None:
    assert Video.__table__.c.active_processing_generation.nullable
    assert VideoProcessingJob.__table__.c.generation.nullable is False

    active_index = next(
        index for index in VideoProcessingJob.__table__.indexes if index.name == "uq_video_processing_jobs_active_video"
    )
    assert active_index.unique is True
    assert str(active_index.dialect_options["postgresql"]["where"]).lower() == "status in ('queued', 'running')"
