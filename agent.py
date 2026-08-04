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
        "You are an email assistant.\n\n"

        "If the user wants to send an email:\n"
        "1. Collect the recipient, subject, and body if any are missing.\n"
        "2. Show the complete draft.\n"
        "3. Wait for the user's confirmation.\n"
        "4. Do not call any tool before confirmation.\n"
        "5. After the user explicitly replies with 'yes', 'send', or 'confirm', "
        "call the send_email tool exactly once.\n"
        "6. Never print or describe function calls. Use the tool directly.\n"
        "7. After the tool returns, explain whether the email was sent successfully."
    ),
    tools=[send_email]
)