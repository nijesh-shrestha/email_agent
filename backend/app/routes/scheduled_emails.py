from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.database.models import ScheduledEmail, ScheduledEmailStatus
from app.auth.dependencies import get_current_user
from app.services.gmail_service import send_email

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
            # Parse the date
            if v.endswith("Z"):
                dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            elif "+" in v or v.count("-") > 2:
                dt = datetime.fromisoformat(v)
            else:
                dt = datetime.fromisoformat(v)

            # Make timezone-naive for comparison
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)

            # Ensure it's in the future
            if dt <= datetime.utcnow():
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
    db = SessionLocal()
    try:
        user_id = current_user.id

        # Parse the scheduled date
        scheduled_dt = datetime.fromisoformat(request.scheduled_date)
        if scheduled_dt.tzinfo is not None:
            scheduled_dt = scheduled_dt.replace(tzinfo=None)

        # Create the scheduled email record
        scheduled_email = ScheduledEmail(
            user_id=user_id,
            recipient=request.to,
            subject=request.subject,
            body=request.body,
            scheduled_date=scheduled_dt,
            status=ScheduledEmailStatus.PENDING,
        )

        db.add(scheduled_email)
        db.commit()
        db.refresh(scheduled_email)

        return {
            "success": True,
            "scheduled_email_id": scheduled_email.id,
            "recipient": request.to,
            "subject": request.subject,
            "scheduled_date": scheduled_dt.isoformat(),
            "message": f"Email scheduled for {scheduled_dt.strftime('%Y-%m-%d %H:%M:%S')} UTC",
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/list")
def list_scheduled_emails(
    status: Optional[str] = None,
    current_user=Depends(get_current_user),
):
    """List all scheduled emails for the current user."""
    db = SessionLocal()
    try:
        user_id = current_user.id

        query = db.query(ScheduledEmail).filter(ScheduledEmail.user_id == user_id)

        if status:
            try:
                status_enum = ScheduledEmailStatus(status.lower())
                query = query.filter(ScheduledEmail.status == status_enum)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status. Must be one of: {[s.value for s in ScheduledEmailStatus]}",
                )

        scheduled_emails = query.order_by(ScheduledEmail.scheduled_date).all()

        return {
            "success": True,
            "count": len(scheduled_emails),
            "scheduled_emails": [
                {
                    "id": email.id,
                    "recipient": email.recipient,
                    "subject": email.subject,
                    "body": email.body,
                    "scheduled_date": email.scheduled_date.isoformat(),
                    "status": email.status.value,
                    "created_at": email.created_at.isoformat(),
                    "sent_at": email.sent_at.isoformat() if email.sent_at else None,
                    "error_message": email.error_message,
                    "message_id": email.message_id,
                }
                for email in scheduled_emails
            ],
        }

    finally:
        db.close()


@router.delete("/{scheduled_email_id}")
def cancel_scheduled_email(
    scheduled_email_id: int,
    current_user=Depends(get_current_user),
):
    """Cancel a pending scheduled email."""
    db = SessionLocal()
    try:
        user_id = current_user.id

        scheduled_email = (
            db.query(ScheduledEmail)
            .filter(ScheduledEmail.id == scheduled_email_id)
            .filter(ScheduledEmail.user_id == user_id)
            .filter(ScheduledEmail.status == ScheduledEmailStatus.PENDING)
            .first()
        )

        if not scheduled_email:
            raise HTTPException(
                status_code=404,
                detail="Scheduled email not found or already processed",
            )

        scheduled_email.status = ScheduledEmailStatus.CANCELLED
        db.commit()

        return {
            "success": True,
            "message": f"Scheduled email {scheduled_email_id} cancelled",
            "recipient": scheduled_email.recipient,
            "subject": scheduled_email.subject,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/{scheduled_email_id}")
def get_scheduled_email(
    scheduled_email_id: int,
    current_user=Depends(get_current_user),
):
    """Get details of a specific scheduled email."""
    db = SessionLocal()
    try:
        user_id = current_user.id

        scheduled_email = (
            db.query(ScheduledEmail)
            .filter(ScheduledEmail.id == scheduled_email_id)
            .filter(ScheduledEmail.user_id == user_id)
            .first()
        )

        if not scheduled_email:
            raise HTTPException(status_code=404, detail="Scheduled email not found")

        return {
            "success": True,
            "scheduled_email": {
                "id": scheduled_email.id,
                "recipient": scheduled_email.recipient,
                "subject": scheduled_email.subject,
                "body": scheduled_email.body,
                "scheduled_date": scheduled_email.scheduled_date.isoformat(),
                "status": scheduled_email.status.value,
                "created_at": scheduled_email.created_at.isoformat(),
                "sent_at": scheduled_email.sent_at.isoformat() if scheduled_email.sent_at else None,
                "error_message": scheduled_email.error_message,
                "message_id": scheduled_email.message_id,
            },
        }

    finally:
        db.close()
