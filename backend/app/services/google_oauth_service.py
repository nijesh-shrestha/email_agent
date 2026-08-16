import os
from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from app.database.models import OAuthAccount


GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def get_google_credentials(db, user_id: int) -> Credentials:
    """Return refreshed google Credentials for the given user, or raise ValueError if not found."""
    oauth_account = (
        db.query(OAuthAccount)
        .filter(
            OAuthAccount.user_id == int(user_id),
            OAuthAccount.provider == "google",
        )
        .first()
    )

    if not oauth_account:
        raise ValueError("Google account is not connected.")

    creds = Credentials(
        token=oauth_account.access_token,
        refresh_token=oauth_account.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=SCOPES,
    )

    # If credentials are not valid, try to refresh using stored refresh token.
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

            oauth_account.access_token = creds.token
            oauth_account.expires_at = creds.expiry if creds.expiry else datetime.now(timezone.utc)
            db.commit()
        else:
            raise ValueError(
                "Google credentials are invalid. Please reconnect your Google account."
            )

    return creds