import base64
import os
import traceback
from email.message import EmailMessage

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.services.gmail_service import get_gmail_service
from google.adk.tools.tool_context import ToolContext

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

load_dotenv()

CREDENTIALS_PATH = os.getenv(
    "GOOGLE_CREDENTIALS_PATH",
    "credentials.json"
)

TOKEN_PATH = os.getenv(
    "GOOGLE_TOKEN_PATH",
    "token.json"
)


def _get_gmail_service():
    """Load cached OAuth credentials, refreshing or running the consent flow as needed."""

    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(f"Missiong {CREDENTIALS_PATH}.")

            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def send_email(to: str, subject: str, body: str, db: Session, user_id: int, tool_context: ToolContext,) -> dict:
    """Send an email from the user's Gmail account."""

    user_id = tool_context.state.get("user_id")
    
    if not user_id:
        return {
            "status": "error",
            "detail": "Authenticated user not found."
        }

    db = SessionLocal()

    try:
        service = get_gmail_service(db, user_id)
        message = EmailMessage()
        message.set_content(body)
        message["To"] = to
        message["Subject"] = subject
        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
        sent = service.users().messages().send(userId="me", body={"raw": encoded}).execute()

        return {
            "status": "success",
            "message_id": sent.get("id"),
            "detail": f"Email sent to {to}."
        }

    except Exception as e:
        traceback.print_exc()

        return {
            "status": "error",
            "detail": repr(e)
        }


def get_current_user() -> dict:
    """Get the authenticated Gmail user's profile information."""

    try:
        service = _get_gmail_service()
        profile = service.users().getProfile(userId="me").execute()

        return {
            "status": "success",
            "email_address": profile.get("emailAddress"),
            "detail": f"Authenticated Gmail account: {profile.get('emailAddress')}"
        }

    except Exception as e:
        traceback.print_exc()

        return {
            "status": "error",
            "detail": repr(e)
        }