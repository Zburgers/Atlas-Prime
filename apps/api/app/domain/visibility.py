from __future__ import annotations

from sqlalchemy import and_, or_

from app.db.models import Video
from app.domain.status import ModerationStatus, VideoPrivacy, VideoStatus


def discoverable_video():
    """Public browse/search/feed visibility: ready, public, approved, and live."""
    return and_(
        Video.status == VideoStatus.READY.value,
        Video.privacy == VideoPrivacy.PUBLIC.value,
        Video.moderation_status == ModerationStatus.APPROVED.value,
        Video.deleted_at.is_(None),
    )


def direct_link_readable_video():
    """Readable by a link: public or unlisted, but never private, removed, or tombstoned."""
    return and_(
        Video.status == VideoStatus.READY.value,
        Video.privacy.in_((VideoPrivacy.PUBLIC.value, VideoPrivacy.UNLISTED.value)),
        Video.moderation_status == ModerationStatus.APPROVED.value,
        Video.deleted_at.is_(None),
    )


def is_discoverable_video(video: Video) -> bool:
    return (
        video.status == VideoStatus.READY.value
        and video.privacy == VideoPrivacy.PUBLIC.value
        and video.moderation_status == ModerationStatus.APPROVED.value
        and video.deleted_at is None
    )


def is_direct_link_readable_video(video: Video) -> bool:
    return (
        video.status == VideoStatus.READY.value
        and video.privacy in (VideoPrivacy.PUBLIC.value, VideoPrivacy.UNLISTED.value)
        and video.moderation_status == ModerationStatus.APPROVED.value
        and video.deleted_at is None
    )


def owner_or_direct_link_readable_video(user_id):
    return and_(Video.deleted_at.is_(None), or_(Video.owner_id == user_id, direct_link_readable_video()))
