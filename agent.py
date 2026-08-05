import os
import base64
from email.message import EmailMessage
import traceback
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES=["https://www.googleapis.com/auth/gmail.send"]

load_dotenv()

CREDENTIALS_PATH = os.getenv(
    "GOOGLE_CREDENTIALS_PATH",
    "credentials.json"
)

TOKEN_PATH = os.getenv(
    "GOOGLE_TOKEN_PATH",
    "token.json"
)

print("Current working directory:", os.getcwd())
print("credentials.json exists:", os.path.exists("credentials.json"))

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

def send_email(to: str, subject: str, body: str) -> dict:

    """Send an email from the user's Gmail account.

    Args:
        to: Recipient email address.
        subject: Subject line of the email.
        body: Plain-text body content of the email.

    Returns:
        A dict with a 'status' key ('success' or 'error') and a 'detail' message.
        On success it also includes the Gmail 'message_id'.
    """

    try:
        service = _get_gmail_service()
        message = EmailMessage()
        message.set_content(body)
        message["To"] = to
        message["Subject"] = subject
        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
        sent = (service.users().messages().send(userId = "me", body = {"raw": encoded}).execute())

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

root_agent = Agent(
    name="email_agent",
    model = LiteLlm(model="groq/llama-3.3-70b-versatile"),
    description="An agent that composes and sends emails on the user's behalf via Gmail.",
    instruction=(
        "You are a careful email assistant. Your primary responsibility is to "
        "draft emails and obtain explicit user approval before sending them.\n\n"

        "MANDATORY EMAIL WORKFLOW:\n"
        "1. When the user asks to send an email, collect any missing recipient, "
        "subject, or body information.\n"
        "2. Once all information is available, create and display the complete "
        "email draft in this format:\n"
        "To: <recipient>\n"
        "Subject: <subject>\n"
        "Body:\n"
        "<email body>\n\n"
        "3. After displaying the draft, ask exactly: "
        "'Do you approve this email and want me to send it?'\n"
        "4. STOP after asking for approval. Do not call send_email in the same "
        "response in which you create or display the draft.\n"
        "5. The user's original request to send an email is NOT approval. "
        "Never treat the initial request as confirmation.\n"
        "6. Call send_email only in a later user message after the user gives "
        "clear and explicit approval, such as: 'yes', 'yes, send it', "
        "'send it', 'approve', 'confirm', or 'go ahead'.\n"
        "7. If the user asks to change the recipient, subject, or body, update "
        "the draft, display the entire updated draft, and ask for approval again.\n"
        "8. If the user says 'no', 'cancel', or does not clearly approve, do not "
        "call send_email.\n"
        "9. Never call send_email more than once for the same approved draft.\n"
        "10. Never print, describe, or expose function calls. Use the tool directly.\n"
        "11. After send_email returns, clearly report whether the email was sent "
        "successfully. If it failed, report the error without claiming that the "
        "email was sent."
    ),
    tools=[send_email]
)