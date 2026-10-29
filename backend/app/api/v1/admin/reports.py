"""
Admin API - Report Management (SQLAlchemy)

Users file content reports via POST /reports; this router is how admins
see and resolve them.
"""
import json
import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.models.report import Report
from app.models.audit_log import AuditLog
from app.api.v1.deps import require_admin

logger = logging.getLogger(__name__)

router = APIRouter()


class ReportActionRequest(BaseModel):
    """Resolve or dismiss a report."""
    action: Literal["resolved", "dismissed"]
    resolution_note: Optional[str] = Field(None, max_length=2000)


@router.get("")
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    report_status: Optional[str] = Query(None, pattern="^(pending|resolved|dismissed)$"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List content reports, newest first, optionally filtered by status."""
    base = []
    if report_status:
        base.append(Report.status == report_status)

    count_result = await db.execute(select(func.count()).select_from(Report).where(*base))
    total = count_result.scalar()

    result = await db.execute(
        select(Report).where(*base)
        .order_by(Report.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    reports = result.scalars().all()

    return {
        "results": [
            {
                "id": str(r.id),
                "status": r.status,
                "reason": r.reason,
                "details": r.details,
                "resolution_note": r.resolution_note,
                "created_at": r.created_at,
                "resolved_by_name": r.resolved_by.display_name if r.resolved_by else None,
                "reporter_name": r.reporter.display_name or r.reporter.email if r.reporter else None,
                "reporter_email": r.reporter.email if r.reporter else None,
                "resource_id": str(r.resource_id),
                "resource_title": r.resource.title if r.resource else None,
                "resource_slug": r.resource.slug if r.resource else None,
            }
            for r in reports
        ],
        "total": total,
        "page": page,
        "pages": (total + page_size - 1) // page_size if total > 0 else 1,
    }


@router.put("/{report_id}")
async def resolve_report(
    report_id: str,
    data: ReportActionRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Resolve or dismiss a report."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    # M6: a resolved/dismissed report is final — never silently overwrite it.
    if report.status in ("resolved", "dismissed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Report is already {report.status}",
        )

    report.status = data.action
    report.resolved_by_id = current_user.id
    if data.resolution_note is not None:
        report.resolution_note = data.resolution_note

    try:
        audit = AuditLog(
            action=f"{data.action}_report",
            actor_id=current_user.id,
            target_type="report",
            target_id=str(report.id),
            details_json=json.dumps({
                "reason": report.reason,
                "resource_id": str(report.resource_id),
                "note": data.resolution_note,
            }),
        )
        db.add(audit)
    except Exception as e:
        logger.error(f"Audit log error: {e}")

    await db.flush()
    return {"id": str(report.id), "status": report.status, "resolution_note": report.resolution_note}
