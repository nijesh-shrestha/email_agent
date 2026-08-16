from typing import Any, Dict

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.database.models import User
from app.services.gmail_service import read_user_emails, send_email


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


def read_emails_tool(user_id: str, of_user: str, dates: list[str] | str, amount: int = 5) -> Dict[str, Any]:
    """Return matching Gmail messages from a specific sender and date list."""
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
