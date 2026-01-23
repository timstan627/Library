"""
Reports API endpoint
"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.models.user import User
from app.models.resource import Resource
from app.models.report import Report
from app.api.v1.deps import get_current_active_user

router = APIRouter()


class ReportCreate(BaseModel):
    resource_id: uuid.UUID
    reason: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=1000)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_report(
    data: ReportCreate,
    current_user: User = Depends(get_current_active_user),
):
    """Create a new content report."""
    # Check resource exists
    resource = await Resource.find_one(Resource.id == data.resource_id, Resource.is_deleted == False)
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    
    # Check if user already reported this resource
    existing_report = await Report.find_one(
        Report.reporter.id == current_user.id,
        Report.resource.id == data.resource_id,
        Report.status == "pending"
    )
    
    if existing_report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reported this resource",
        )
    
    # Create report
    report = Report(
        reporter=current_user,
        resource=resource,
        reason=data.reason,
        details=data.description, # Mapped description -> details based on model def
    )
    
    await report.create()
    
    return {"message": "Report submitted successfully", "id": str(report.id)}
