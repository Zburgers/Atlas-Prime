from sqlalchemy import BigInteger, DateTime, Text
from sqlalchemy.types import Uuid

from app.db.models import Video, VideoAssetInventory
from app.domain.status import (
    CANONICAL_VIDEO_STATUS_VALUES,
    DELETION_STATUS_VALUES,
    DeletionStatus,
    VideoStatus,
)


def test_deletion_status_is_separate_from_video_lifecycle() -> None:
    assert DELETION_STATUS_VALUES == ["pending", "running", "failed", "complete"]
    assert set(CANONICAL_VIDEO_STATUS_VALUES) == {
        "draft",
        "uploading",
        "uploaded",
        "queued",
        "probing",
        "processing",
        "ready",
        "failed",
    }
    assert "deleting" not in {status.value for status in VideoStatus}
    assert set(status.value for status in DeletionStatus) == set(DELETION_STATUS_VALUES)


def test_video_deletion_columns_have_nullable_and_default_contract() -> None:
    table = Video.__table__

    assert isinstance(table.c.deleted_at.type, DateTime)
    assert table.c.deleted_at.type.timezone is True
    assert table.c.deleted_at.nullable is True
    assert table.c.deletion_status.nullable is False
    assert str(table.c.deletion_status.default.arg) == "complete"
    assert str(table.c.deletion_status.server_default.arg) == "complete"
    assert table.c.deletion_error.nullable is True

    constraint = next(item for item in table.constraints if item.name == "ck_videos_deletion_status")
    assert str(constraint.sqltext) == "deletion_status in ('pending', 'running', 'failed', 'complete')"


def test_asset_inventory_fields_foreign_key_and_constraints_are_declared() -> None:
    table = VideoAssetInventory.__table__

    assert table.c.id.primary_key is True
    assert isinstance(table.c.id.type, Uuid)
    assert isinstance(table.c.video_id.type, Uuid)
    assert isinstance(table.c.generation.type, Uuid)
    assert isinstance(table.c.relative_path.type, Text)
    assert isinstance(table.c.content_type.type, Text)
    assert isinstance(table.c.size_bytes.type, BigInteger)
    assert isinstance(table.c.sha256.type, Text)
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True

    foreign_key = next(iter(table.c.video_id.foreign_keys))
    assert foreign_key.target_fullname == "videos.id"
    assert foreign_key.ondelete == "CASCADE"

    unique = next(item for item in table.constraints if item.name == "uq_video_asset_inventory_video_generation_path")
    assert [column.name for column in unique.columns] == ["video_id", "generation", "relative_path"]
    size_constraint = next(
        item for item in table.constraints if item.name == "ck_video_asset_inventory_size_nonnegative"
    )
    assert str(size_constraint.sqltext) == "size_bytes >= 0"


def test_asset_inventory_indexes_cover_generation_and_foreign_key_access() -> None:
    indexes = {index.name: index for index in VideoAssetInventory.__table__.indexes}

    assert [column.name for column in indexes["ix_video_asset_inventory_video_generation"].columns] == [
        "video_id",
        "generation",
    ]
    assert [column.name for column in indexes["ix_video_asset_inventory_video_id"].columns] == ["video_id"]
