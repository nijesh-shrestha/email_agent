import base64
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Iterable, Tuple

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.services.google_oauth_service import get_google_credentials


def get_gmail_service(db, user_id):
    creds = get_google_credentials(db, user_id)
    return build("gmail", "v1", credentials=creds)


def _normalize_dates(dates: Iterable[str] | str | None) -> list[str]:
    if dates is None:
        return []
    if isinstance(dates, str):
        values = [part.strip() for part in dates.split(",") if part.strip()]
    else:
        values = [str(part).strip() for part in dates if str(part).strip()]
    return values


def _date_query(date_value: str) -> str:
    start = datetime.strptime(date_value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return f"after:{int(start.timestamp())} before:{int(end.timestamp())}"


def _extract_headers(headers: list[dict]) -> dict[str, str]:
    extracted: dict[str, str] = {}
    for header in headers or []:
        name = header.get("name")
        value = header.get("value")
        if name and value:
            extracted[name] = value
    return extracted


def read_emails(service, user_email: str, of_user: str, dates: Iterable[str] | str | None, amount: int = 5) -> dict:
    """Read Gmail messages for a given sender and optional date list."""
    normalized_dates = _normalize_dates(dates)
    seen_ids: set[str] = set()
    collected: list[dict] = []

    filter_query = f"from:({of_user})"
    if normalized_dates:
        for date_value in normalized_dates:
            query = f"{filter_query} {_date_query(date_value)}"
            response = (
                service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max(1, amount))
                .execute()
            )
            for item in response.get("messages", []) or []:
                msg_id = item.get("id")
                if msg_id and msg_id not in seen_ids:
                    seen_ids.add(msg_id)
                    collected.append({"id": msg_id})
    else:
        response = (
            service.users()
            .messages()
            .list(userId="me", q=filter_query, maxResults=max(1, amount))
            .execute()
        )
        for item in response.get("messages", []) or []:
            msg_id = item.get("id")
            if msg_id and msg_id not in seen_ids:
                seen_ids.add(msg_id)
                collected.append({"id": msg_id})

    if not collected:
        return {"status": "success", "count": 0, "emails": [], "requested_by": user_email, "of_user": of_user, "dates": normalized_dates, "amount": amount}

    emails: list[dict] = []
    for item in collected[:amount]:
        message = (
            service.users()
            .messages()
            .get(userId="me", id=item["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"])
            .execute()
        )
        headers = _extract_headers(message.get("payload", {}).get("headers", []))
        emails.append(
            {
                "id": message.get("id"),
                "thread_id": message.get("threadId"),
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", "(no subject)"),
                "date": headers.get("Date", ""),
                "snippet": message.get("snippet", ""),
            }
        )

    return {
        "status": "success",
        "count": len(emails),
        "emails": emails,
        "requested_by": user_email,
        "of_user": of_user,
        "dates": normalized_dates,
        "amount": amount,
    }


def read_user_emails(db, user_id: int, of_user: str, dates: Iterable[str] | str | None, amount: int = 5) -> Tuple[bool, dict]:
    """Read matching Gmail messages for a user from the given sender and date filter."""
    try:
        service = get_gmail_service(db, user_id)
        profile = service.users().getProfile(userId="me").execute()
        user_email = profile.get("emailAddress", "")
        result = read_emails(service, user_email, of_user, dates, amount)
        return True, result
    except HttpError as e:
        return False, {"status": "error", "detail": e.content.decode() if hasattr(e, "content") else str(e)}
    except Exception as e:
        return False, {"status": "error", "detail": str(e)}


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
