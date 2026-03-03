"""
Reports API endpoint (SQLAlchemy)
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.models.resource import Resource
from app.models.report import Report
from app.api.v1.deps import get_current_active_user

router = APIRouter()


class ReportCreate(BaseModel):
    resource_id: str
    reason: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=1000)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_report(
    data: ReportCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new content report."""
    result = await db.execute(
        select(Resource).where(Resource.id == data.resource_id, Resource.is_deleted == False)
    )
    resource = result.scalar_one_or_none()
    
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    
    # Check if user already reported
    existing = await db.execute(
        select(Report).where(
            Report.reporter_id == current_user.id,
            Report.resource_id == data.resource_id,
            Report.status == "pending",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You have already reported this resource")
    
    report = Report(
        reporter_id=current_user.id,
        resource_id=resource.id,
        reason=data.reason,
        details=data.description,
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)
    
    return {"message": "Report submitted successfully", "id": str(report.id)}
