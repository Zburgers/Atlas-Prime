from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLogEntry, ContentReport, ModerationAction, User, Video, VideoComment
from app.domain.status import ModerationStatus
from app.schemas.moderation import ContentReportCreate, ModerationActionCreate
from app.services import videos as video_service


def _not_found(message: str = "Content not found") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "NotFound", "message": message})


async def create_report(session: AsyncSession, reporter: User, payload: ContentReportCreate) -> ContentReport:
    await _reportable_target(session, reporter, payload.target_type, payload.target_id)
    report = ContentReport(
        reporter_user_id=reporter.id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        reason=payload.reason,
        details=payload.details,
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


async def list_reports(session: AsyncSession, *, state: str | None, limit: int) -> tuple[list[ContentReport], int]:
    where = [ContentReport.status == state] if state else []
    total = await session.scalar(select(func.count()).select_from(ContentReport).where(*where))
    result = await session.execute(
        select(ContentReport).where(*where).order_by(ContentReport.created_at.desc()).limit(limit)
    )
    return list(result.scalars()), int(total or 0)


async def act_on_report(
    session: AsyncSession,
    actor: User,
    report_id: UUID,
    payload: ModerationActionCreate,
) -> tuple[ContentReport, ModerationAction]:
    report = await session.get(ContentReport, report_id)
    if report is None:
        raise _not_found("Report not found")
    target = await _target_for_moderation(session, report.target_type, report.target_id)
    target.moderation_status = {
        "remove": ModerationStatus.REMOVED.value,
        "restore": ModerationStatus.APPROVED.value,
        "limit": ModerationStatus.LIMITED.value,
    }[payload.action]
    action = ModerationAction(
        actor_user_id=actor.id,
        target_type=report.target_type,
        target_id=report.target_id,
        action=payload.action,
        reason=payload.reason,
    )
    audit = AuditLogEntry(
        actor_user_id=actor.id,
        action=f"moderation.{payload.action}",
        target_type=report.target_type,
        target_id=report.target_id,
        metadata_json={"report_id": str(report.id), "reason": payload.reason},
    )
    report.status = "actioned"
    session.add_all([action, audit])
    await session.commit()
    await session.refresh(report)
    await session.refresh(action)
    return report, action


async def list_audit_log(session: AsyncSession, *, target_id: UUID | None, limit: int) -> list[AuditLogEntry]:
    where = [AuditLogEntry.target_id == target_id] if target_id else []
    result = await session.execute(
        select(AuditLogEntry).where(*where).order_by(AuditLogEntry.created_at.desc()).limit(limit)
    )
    return list(result.scalars())


async def _reportable_target(session: AsyncSession, reporter: User, target_type: str, target_id: UUID) -> object:
    if target_type == "video":
        return await video_service.get_video_for_read(session, reporter, target_id)
    comment = await session.get(VideoComment, target_id)
    if comment is None or comment.moderation_status == ModerationStatus.REMOVED.value:
        raise _not_found()
    await video_service.get_video_for_read(session, reporter, comment.video_id)
    return comment


async def _target_for_moderation(session: AsyncSession, target_type: str, target_id: UUID) -> Video | VideoComment:
    target: Video | VideoComment | None
    if target_type == "video":
        target = await session.get(Video, target_id)
    else:
        target = await session.get(VideoComment, target_id)
    if target is None:
        raise _not_found()
    return target
