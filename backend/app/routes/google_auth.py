import os
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.database.models import OAuthAccount

router = APIRouter(prefix="/auth/google", tags=["Google OAuth"]) 

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def create_flow():
    client_config = {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI")],
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=os.getenv("GOOGLE_REDIRECT_URI"),
    )

    return flow


@router.get("/start")
def google_start(current_user=Depends(get_current_user)):
    """Begin the OAuth flow and return the Google consent URL for the authenticated user.

    The frontend must call this endpoint with the user's Authorization header and then
    redirect the browser to the returned URL so the OAuth consent flow runs in the
    user's browser session.
    """
    flow = create_flow()

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    return {"authorization_url": authorization_url}


@router.get("/callback")
def google_callback(request: Request, code: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Handle OAuth callback, exchange code, inspect userinfo, and persist tokens under OAuthAccount linked to current_user."""
    flow = create_flow()
    flow.fetch_token(code=code)
    credentials = flow.credentials

    if not credentials or not credentials.token:
        raise HTTPException(status_code=400, detail="Failed to obtain credentials from Google")

    # Fetch userinfo to tie the OAuth account to a provider-specific id and email
    oauth2 = build("oauth2", "v2", credentials=credentials)
    userinfo = oauth2.userinfo().get().execute()

    provider_account_id = userinfo.get("id")
    email = userinfo.get("email")

    # Upsert OAuthAccount for this user
    oauth_account = (
        db.query(OAuthAccount)
        .filter(
            OAuthAccount.user_id == current_user.id,
            OAuthAccount.provider == "google",
        )
        .first()
    )

    expires_at = credentials.expiry if getattr(credentials, "expiry", None) else datetime.now(timezone.utc) + timedelta(seconds=3600)

    if oauth_account:
        oauth_account.provider_account_id = provider_account_id
        oauth_account.email = email
        oauth_account.access_token = credentials.token
        oauth_account.refresh_token = credentials.refresh_token
        oauth_account.expires_at = expires_at
    else:
        oauth_account = OAuthAccount(
            user_id=current_user.id,
            provider="google",
            provider_account_id=provider_account_id,
            email=email,
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            expires_at=expires_at,
        )
        db.add(oauth_account)

    db.commit()

    # After successful connection, redirect the user back to frontend dashboard if FRONTEND_URL is configured
    frontend_url = os.getenv("FRONTEND_URL")
    if frontend_url:
        return RedirectResponse(frontend_url + "/dashboard")

    return {"status": "connected", "email": email}


@router.get("/status")
def google_status(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Return the Gmail connection status for the current authenticated user."""
    oauth_account = (
        db.query(OAuthAccount)
        .filter(
            OAuthAccount.user_id == current_user.id,
            OAuthAccount.provider == "google",
        )
        .first()
    )

    if not oauth_account:
        return {"connected": False}

    return {
        "connected": True,
        "email": oauth_account.email,
        "provider_account_id": oauth_account.provider_account_id,
        "expires_at": oauth_account.expires_at.isoformat() if oauth_account.expires_at else None,
    }
