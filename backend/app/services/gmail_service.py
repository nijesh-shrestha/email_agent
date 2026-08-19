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


def read_emails(service, user_email: str, of_user: str, dates: Iterable[str] | str | None = None, amount: int | None = None) -> dict:
    """Read Gmail messages for a given sender and optional date list.
    
    If amount is not provided, defaults to 1 (latest result).
    If dates are not provided, searches without date filter.
    of_user can be either an email address or a person's name.
    """
    normalized_dates = _normalize_dates(dates)
    seen_ids: set[str] = set()
    collected: list[dict] = []
    
    # Default amount to 1 if not provided
    if amount is None:
        amount = 1

    # Build the from query - handle both email and name
    # If of_user contains @, treat as email; otherwise treat as name/partial match
    if "@" in of_user:
        # Treat as email - search for exact email and also without quotes for broader match
        filter_queries = [f'from:"{of_user}"', f'from:{of_user}']
    else:
        # Treat as name - search for name matches in from field (both quoted and unquoted)
        filter_queries = [f'from:"{of_user}"', f'from:{of_user}']
    
    # Try each query variant until we find results
    filter_query = filter_queries[0]
    
    # Helper function to try queries
    def try_queries(queries, date_filter=None):
        for q in queries:
            try:
                full_query = f"{q} {date_filter}" if date_filter else q
                response = (
                    service.users()
                    .messages()
                    .list(userId="me", q=full_query, maxResults=max(1, amount))
                    .execute()
                )
                if response.get("messages"):
                    return response.get("messages", [])
            except Exception as e:
                continue
        return []
    
    if normalized_dates:
        for date_value in normalized_dates:
            date_filter = _date_query(date_value)
            items = try_queries(filter_queries, date_filter)
            for item in items:
                msg_id = item.get("id")
                if msg_id and msg_id not in seen_ids:
                    seen_ids.add(msg_id)
                    collected.append({"id": msg_id})
    else:
        items = try_queries(filter_queries)
        for item in items:
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


def read_user_emails(db, user_id: int, of_user: str, dates: Iterable[str] | str | None = None, amount: int | None = None) -> Tuple[bool, dict]:
    """Read matching Gmail messages for a user from the given sender and date filter."""
    try:
        service = get_gmail_service(db, user_id)
        profile = service.users().getProfile(userId="me").execute()
        user_email = profile.get("emailAddress", "")
        result = read_emails(service, user_email, of_user, dates, amount)
        print("read_user_emails result:", result)
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
