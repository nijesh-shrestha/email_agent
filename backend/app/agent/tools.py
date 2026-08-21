from datetime import datetime, timedelta
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.database.models import User, ScheduledEmail, ScheduledEmailStatus
from app.services.gmail_service import read_user_emails, send_email
from app.services.calendar_service import (
    get_calendar_events,
    get_event_by_date,
    get_upcoming_events,
    list_calendars,
)
from app.utils.timezone import now_npt, parse_datetime_to_utc


def send_email_tool(user_id: str, to: str, subject: str, body: str) -> Dict[str, Any]:
    """Tool wrapper that sends an email on behalf of a user using stored OAuth tokens.

    This function opens a DB session, calls the shared send_email service, and
    returns a structured result. Designed to be passed into the agent's tools list.
    """
    db: Session = SessionLocal()
    try:
        ok, payload = send_email(db, int(user_id), to, subject, body)
        if ok:
            return {"success": True, **payload}
        return {"success": False, **payload}
    finally:
        db.close()


def read_emails_tool(user_id: str, of_user: str, dates: list[str] | str | None = None, amount: int | None = None) -> Dict[str, Any]:
    """Return matching Gmail messages from a specific sender.
    
    Args:
        user_id: The user's ID
        of_user: Email address or name of the person whose emails to search for
        dates: Optional list of dates in ISO format (e.g., ['2026-08-16', '2026-08-17']). 
               If not provided, searches all emails.
        amount: Optional number of emails to return. Defaults to 1 (latest result) if not provided.
    """
    db: Session = SessionLocal()
    try:
        ok, payload = read_user_emails(db, int(user_id), of_user, dates, amount)
        if ok:
            return {"success": True, **payload}
        return {"success": False, **payload}
    finally:
        db.close()


def get_user_tool(user_id: str) -> Dict[str, Any]:
    """Return basic user info (id, email, name) for the given user id."""
    db: Session = SessionLocal()
    try:
        user = db.get(User, int(user_id))
        if not user:
            return {"found": False}
        return {"found": True, "id": user.id, "email": user.email, "name": user.name}
    finally:
        db.close()


def schedule_email_tool(
    user_id: str,
    to: str,
    subject: str,
    body: str,
    scheduled_date: str,
) -> Dict[str, Any]:
    """Schedule an email to be sent at a future date and time.

    Args:
        user_id: The user's ID
        to: Recipient email address
        subject: Email subject line
        body: Email body content
        scheduled_date: ISO format date string (e.g., '2026-08-17T15:30:00')

    Returns:
        Dict with success status and scheduled email ID or error message
    """
    db: Session = SessionLocal()
    try:
        # Validate recipient
        if not to or "@" not in to:
            return {"success": False, "error": "Invalid recipient email address"}

        # Parse the scheduled date
        try:
            scheduled_dt = parse_datetime_to_utc(scheduled_date)
        except ValueError as e:
            return {"success": False, "error": f"Invalid date format: {str(e)}"}

        # Ensure the scheduled date is in the future
        now = now_npt().astimezone(scheduled_dt.tzinfo)
        if scheduled_dt <= now:
            return {
                "success": False,
                "error": "Scheduled date must be in the future",
                "current_time": now.isoformat(),
                "provided_time": scheduled_dt.isoformat(),
            }

        # Convert to timezone-naive UTC for database storage
        scheduled_dt_naive = scheduled_dt.replace(tzinfo=None)

        # Create the scheduled email record
        scheduled_email = ScheduledEmail(
            user_id=str(user_id),
            recipient=to,
            subject=subject,
            body=body,
            scheduled_date=scheduled_dt_naive,
            status=ScheduledEmailStatus.PENDING,
        )

        db.add(scheduled_email)
        db.commit()
        db.refresh(scheduled_email)

        return {
            "success": True,
            "scheduled_email_id": scheduled_email.id,
            "recipient": to,
            "subject": subject,
            "scheduled_date": scheduled_dt.isoformat(),
            "message": f"Email scheduled to be sent at {scheduled_dt.astimezone(now_npt().tzinfo).strftime('%Y-%m-%d %H:%M:%S')} NPT",
        }

    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def get_scheduled_emails_tool(user_id: str, status: str | None = None) -> Dict[str, Any]:
    """Retrieve scheduled emails for a user, optionally filtered by status.

    Args:
        user_id: The user's ID
        status: Optional status filter (pending, sent, cancelled, failed)

    Returns:
        Dict with list of scheduled emails
    """
    db: Session = SessionLocal()
    try:
        query = db.query(ScheduledEmail).filter(ScheduledEmail.user_id == str(user_id))

        if status:
            try:
                status_enum = ScheduledEmailStatus(status.lower())
                query = query.filter(ScheduledEmail.status == status_enum)
            except ValueError:
                valid_statuses = [s.value for s in ScheduledEmailStatus]
                return {
                    "success": False,
                    "error": f"Invalid status. Must be one of: {valid_statuses}",
                }

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


def cancel_scheduled_email_tool(user_id: str, scheduled_email_id: int) -> Dict[str, Any]:
    """Cancel a pending scheduled email.

    Args:
        user_id: The user's ID
        scheduled_email_id: ID of the scheduled email to cancel

    Returns:
        Dict with success status
    """
    db: Session = SessionLocal()
    try:
        scheduled_email = (
            db.query(ScheduledEmail)
            .filter(ScheduledEmail.id == scheduled_email_id)
            .filter(ScheduledEmail.user_id == str(user_id))
            .filter(ScheduledEmail.status == ScheduledEmailStatus.PENDING)
            .first()
        )

        if not scheduled_email:
            return {
                "success": False,
                "error": "Scheduled email not found or already processed",
            }

        scheduled_email.status = ScheduledEmailStatus.CANCELLED
        db.commit()

        return {
            "success": True,
            "message": f"Scheduled email (ID: {scheduled_email_id}) has been cancelled",
            "recipient": scheduled_email.recipient,
            "subject": scheduled_email.subject,
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def get_scheduled_email_by_id_tool(user_id: str, scheduled_email_id: int) -> Dict[str, Any]:
    """Get details of a specific scheduled email.

    Args:
        user_id: The user's ID
        scheduled_email_id: ID of the scheduled email to retrieve

    Returns:
        Dict with scheduled email details
    """
    db: Session = SessionLocal()
    try:
        scheduled_email = (
            db.query(ScheduledEmail)
            .filter(ScheduledEmail.id == scheduled_email_id)
            .filter(ScheduledEmail.user_id == str(user_id))
            .first()
        )

        if not scheduled_email:
            return {"success": False, "error": "Scheduled email not found"}

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


# --- Calendar Tools ---
def get_calendar_events_tool(
    user_id: str,
    time_min: str | None = None,
    time_max: str | None = None,
    max_results: int = 10,
    calendar_id: str = "primary",
) -> Dict[str, Any]:
    """Retrieve events from the user's Google Calendar.

    Args:
        user_id: The user's ID
        time_min: ISO format datetime string for start of range (optional)
        time_max: ISO format datetime string for end of range (optional)
        max_results: Maximum number of events to return (default: 10)
        calendar_id: Calendar ID to query (default: 'primary')

    Returns:
        Dict with list of calendar events
    """
    db: Session = SessionLocal()
    try:
        ok, payload = get_calendar_events(
            db, int(user_id), time_min, time_max, max_results, calendar_id
        )
        if ok:
            return {"success": True, **payload}
        return {"success": False, **payload}
    finally:
        db.close()


def get_event_by_date_tool(
    user_id: str,
    date: str,
    calendar_id: str = "primary",
) -> Dict[str, Any]:
    """Retrieve events for a specific date.

    Args:
        user_id: The user's ID
        date: Date in ISO format (YYYY-MM-DD, e.g., '2026-08-18')
        calendar_id: Calendar ID to query (default: 'primary')

    Returns:
        Dict with list of events for the specified date
    """
    db: Session = SessionLocal()
    try:
        ok, payload = get_event_by_date(db, int(user_id), date, calendar_id)
        if ok:
            return {"success": True, **payload}
        return {"success": False, **payload}
    finally:
        db.close()


def get_upcoming_events_tool(
    user_id: str,
    days: int = 7,
    max_results: int = 20,
    calendar_id: str = "primary",
) -> Dict[str, Any]:
    """Retrieve upcoming events for the next N days.

    Args:
        user_id: The user's ID
        days: Number of days to look ahead (default: 7)
        max_results: Maximum number of events to return (default: 20)
        calendar_id: Calendar ID to query (default: 'primary')

    Returns:
        Dict with list of upcoming events
    """
    db: Session = SessionLocal()
    try:
        ok, payload = get_upcoming_events(db, int(user_id), days, max_results, calendar_id)
        if ok:
            return {"success": True, **payload}
        return {"success": False, **payload}
    finally:
        db.close()


def list_calendars_tool(user_id: str) -> Dict[str, Any]:
    """List all calendars the user has access to.

    Args:
        user_id: The user's ID

    Returns:
        Dict with list of available calendars
    """
    db: Session = SessionLocal()
    try:
        ok, payload = list_calendars(db, int(user_id))
        if ok:
            return {"success": True, **payload}
        return {"success": False, **payload}
    finally:
        db.close()


# --- Testing / development helpers ---
def send_email_stub(user_id: str, to: str, subject: str, body: str) -> Dict[str, Any]:
    """A non-destructive stub of the send_email tool intended for local testing.

    It mirrors the send_email_tool signature but does not call the Gmail API.
    Use this in test agents to validate tool invocation and agent flows without
    sending real emails.
    """
    # Simple validation similar to the real tool
    if not to or '@' not in to:
        return {"success": False, "error": "invalid_recipient"}
    if not subject:
        subject = "(no subject)"
    # Return a deterministic fake message id for testing
    fake_message_id = f"stub-{user_id}-{abs(hash((to,subject,body))) % 100000}"
    return {"success": True, "message_id": fake_message_id, "detail": f"Stubbed send to {to}"}
