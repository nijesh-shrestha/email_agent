import base64
from email.message import EmailMessage
from typing import Tuple

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.services.google_oauth_service import get_google_credentials


def get_gmail_service(db, user_id):
    creds = get_google_credentials(db, user_id)
    return build("gmail", "v1", credentials=creds)


def send_email(db, user_id: int, to: str, subject: str, body: str) -> Tuple[bool, dict]:
    """Send a plain-text email using the stored OAuth credentials for user_id.

    Returns (ok, payload) where payload contains detail or message_id on success.
    """
    service = get_gmail_service(db, user_id)

    message = EmailMessage()
    message.set_content(body)
    message["To"] = to
    message["Subject"] = subject

    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()

    try:
        sent = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": encoded})
            .execute()
        )

        return True, {"message_id": sent.get("id"), "status": "sent"}

    except HttpError as e:
        # Return structured error information
        return False, {"status": "error", "detail": e.content.decode() if hasattr(e, "content") else str(e)}
    except Exception as e:
        return False, {"status": "error", "detail": str(e)}


def get_current_user(db, user_id: int) -> dict:
    """Get authenticated Gmail profile information for a specific app user."""
    try:
        service = get_gmail_service(db, user_id)
        profile = service.users().getProfile(userId="me").execute()

        return {
            "status": "success",
            "email_address": profile.get("emailAddress"),
            "detail": f"Authenticated Gmail account: {profile.get('emailAddress')}",
        }

    except HttpError as e:
        return {"status": "error", "detail": e.content.decode() if hasattr(e, "content") else str(e)}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
