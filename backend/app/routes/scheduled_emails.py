from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional

from app.auth.dependencies import get_current_user
from app.agent.tools import (
    schedule_email_tool,
    get_scheduled_emails_tool,
    cancel_scheduled_email_tool,
    get_scheduled_email_by_id_tool,
)
from app.utils.timezone import now_npt, parse_datetime_to_utc

router = APIRouter()


class ScheduleEmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    scheduled_date: str  # ISO format datetime

    @field_validator("to")
    @classmethod
    def validate_email(cls, v):
        if not v or "@" not in v:
            raise ValueError("Invalid email address")
        return v

    @field_validator("scheduled_date")
    @classmethod
    def validate_date(cls, v):
        try:
            dt = parse_datetime_to_utc(v)

            # Ensure it's in the future
            if dt <= now_npt().astimezone(dt.tzinfo):
                raise ValueError("Scheduled date must be in the future")

            return dt.isoformat()
        except ValueError:
            raise


class CancelScheduledEmailRequest(BaseModel):
    scheduled_email_id: int


class ScheduledEmailResponse(BaseModel):
    id: int
    recipient: str
    subject: str
    body: str
    scheduled_date: str
    status: str
    created_at: str
    sent_at: Optional[str] = None
    error_message: Optional[str] = None
    message_id: Optional[str] = None


@router.post("/schedule")
def schedule_email_direct(
    request: ScheduleEmailRequest,
    current_user=Depends(get_current_user),
):
    """Manually schedule an email without using the agent."""
    result = schedule_email_tool(
        user_id=str(current_user.id),
        to=request.to,
        subject=request.subject,
        body=request.body,
        scheduled_date=request.scheduled_date,
    )
    print("schedule_email_direct result:", result)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to schedule email"))

    return result


@router.get("/list")
def list_scheduled_emails(
    status: Optional[str] = None,
    current_user=Depends(get_current_user),
):
    """List all scheduled emails for the current user."""
    result = get_scheduled_emails_tool(user_id=str(current_user.id), status=status)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to retrieve scheduled emails"))

    return result


@router.delete("/{scheduled_email_id}")
def cancel_scheduled_email(
    scheduled_email_id: int,
    current_user=Depends(get_current_user),
):
    """Cancel a pending scheduled email."""
    result = cancel_scheduled_email_tool(
        user_id=str(current_user.id),
        scheduled_email_id=scheduled_email_id,
    )

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Scheduled email not found"))

    return result


@router.get("/{scheduled_email_id}")
def get_scheduled_email(
    scheduled_email_id: int,
    current_user=Depends(get_current_user),
):
    """Get details of a specific scheduled email."""
    result = get_scheduled_email_by_id_tool(
        user_id=str(current_user.id),
        scheduled_email_id=scheduled_email_id,
    )

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Scheduled email not found"))

    return result
