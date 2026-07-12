from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import AdminUserDep, CurrentUserDep, SessionDep
from app.schemas.moderation import (
    AuditLogEntryResponse,
    AuditLogListResponse,
    ContentReportCreate,
    ContentReportListResponse,
    ContentReportResponse,
    ModerationActionCreate,
    ModerationActionResult,
    ModerationActionResponse,
)
from app.services import moderation as moderation_service

router = APIRouter(tags=["moderation"])


@router.post("/moderation/reports", response_model=ContentReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(payload: ContentReportCreate, session: SessionDep, user: CurrentUserDep) -> ContentReportResponse:
    return ContentReportResponse.model_validate(await moderation_service.create_report(session, user, payload))


@router.get("/admin/reports", response_model=ContentReportListResponse)
async def report_queue(
    session: SessionDep,
    _admin: AdminUserDep,
    state: Annotated[str | None, Query(pattern="^(open|actioned|dismissed)$")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> ContentReportListResponse:
    items, total = await moderation_service.list_reports(session, state=state, limit=limit)
    return ContentReportListResponse(items=[ContentReportResponse.model_validate(item) for item in items], total=total)


@router.post("/admin/reports/{report_id}/actions", response_model=ModerationActionResult)
async def action_report(
    report_id: UUID,
    payload: ModerationActionCreate,
    session: SessionDep,
    admin: AdminUserDep,
) -> ModerationActionResult:
    report, action = await moderation_service.act_on_report(session, admin, report_id, payload)
    return ModerationActionResult(
        report=ContentReportResponse.model_validate(report),
        action=ModerationActionResponse.model_validate(action),
    )


@router.get("/admin/audit-log", response_model=AuditLogListResponse)
async def audit_log(
    session: SessionDep,
    _admin: AdminUserDep,
    target_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> AuditLogListResponse:
    items = await moderation_service.list_audit_log(session, target_id=target_id, limit=limit)
    return AuditLogListResponse(items=[AuditLogEntryResponse.model_validate(item) for item in items])
