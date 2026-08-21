import os
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.settings import ALGORITHM, SECRET_KEY
from app.database.models import OAuthAccount, User
from app.database.session import get_db
from dotenv import load_dotenv

import secrets
import base64
import hashlib

load_dotenv()

router = APIRouter(prefix="/auth/google", tags=["Google OAuth"])

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

pkce_store = {}


def create_flow(redirect_uri: str) -> Flow:
    # redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")
    client_config = {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }

    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )

def generate_pkce():
    code_verifier = secrets.token_urlsafe(64)

    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    return code_verifier, code_challenge

def create_oauth_state(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "purpose": "google_connect",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_oauth_state(state: str) -> int:
    try:
        payload = jwt.decode(
            state,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        if payload.get("purpose") != "google_connect":
            raise HTTPException(
                status_code=400,
                detail="Invalid OAuth state",
            )

        return int(payload["sub"])

    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OAuth state",
        )


def _create_access_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "name": user.name,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@router.get("/start")
def google_start(current_user=Depends(get_current_user)):
    """Begin the OAuth flow and return the Google consent URL for an authenticated user."""

    redirect_uri = os.getenv(
        "GOOGLE_CONNECT_REDIRECT_URI",
        "http://localhost:8000/api/auth/google/callback",
    )

    flow = create_flow(redirect_uri)
    state = create_oauth_state(current_user)

    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state
    )

    return {"authorization_url": authorization_url}


@router.get("/login/start")
def google_login_start() -> dict[str, str]:
    """Start the Google OAuth login flow for the app."""
    redirect_uri = os.getenv(
        "GOOGLE_LOGIN_REDIRECT_URI",
        "http://localhost:8000/api/auth/google/login/callback",
    )

    flow = create_flow(redirect_uri)

    code_verifier, code_challenge = generate_pkce()
    state = secrets.token_urlsafe(32)

    pkce_store[state] = code_verifier

    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )
    return {"authorization_url": authorization_url}


@router.get("/callback")
def google_callback(request: Request, code: str, state: str, db: Session = Depends(get_db)):
    """Handle OAuth callback, exchange code, inspect userinfo, and persist tokens under OAuthAccount linked to current_user."""

    user_id = decode_oauth_state(state)

    current_user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not current_user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    redirect_uri = os.getenv(
        "GOOGLE_CONNECT_REDIRECT_URI",
        "http://localhost:8000/api/auth/google/callback",
    )

    flow = create_flow(redirect_uri)
    flow.fetch_token(code=code)
    credentials = flow.credentials

    if not credentials or not credentials.token:
        raise HTTPException(status_code=400, detail="Failed to obtain credentials from Google")

    oauth2 = build("oauth2", "v2", credentials=credentials)
    userinfo = oauth2.userinfo().get().execute()

    provider_account_id = userinfo.get("id")
    email = userinfo.get("email")

    if not provider_account_id or not email:
        raise HTTPException(
            status_code=400,
            detail="Google did not return required user information",
        )

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
        if credentials.refresh_token:
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

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000",)

    return RedirectResponse(
        f"{frontend_url.rstrip('/')}/dashboard"
    )


@router.get("/login/callback")
def google_login_callback(code: str, state: str, db: Session = Depends(get_db)):
    """Authenticate a user with Google and redirect them back to the frontend."""

    code_verifier = pkce_store.pop(state, None)

    redirect_uri = os.getenv(
        "GOOGLE_LOGIN_REDIRECT_URI",
        "http://localhost:8000/api/auth/google/login/callback",
    )

    flow = create_flow(redirect_uri)
    flow.fetch_token(code=code, code_verifier=code_verifier,)
    credentials = flow.credentials

    if not credentials or not credentials.token:
        raise HTTPException(status_code=400, detail="Failed to obtain credentials from Google")

    oauth2 = build("oauth2", "v2", credentials=credentials)
    userinfo = oauth2.userinfo().get().execute()

    provider_account_id = userinfo.get("id")
    email = userinfo.get("email")
    name = userinfo.get("name") or email.split("@", 1)[0]
    picture = userinfo.get("picture")

    if not provider_account_id or not email:
        raise HTTPException(
            status_code=400,
            detail="Google did not return required user information",
        )

    user = db.query(User).filter(User.google_id == provider_account_id).first()
    if not user and email:
        user = db.query(User).filter(User.email == email).first()

    if not user:
        user = User(
            email=email,
            name=name,
            google_id=provider_account_id,
            image=picture,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if not user.google_id:
            user.google_id = provider_account_id
        if not user.name:
            user.name = name
        if not user.image and picture:
            user.image = picture
        db.commit()

    oauth_account = (
        db.query(OAuthAccount)
        .filter(
            OAuthAccount.user_id == user.id,
            OAuthAccount.provider == "google",
        )
        .first()
    )
    expires_at = credentials.expiry if getattr(credentials, "expiry", None) else datetime.now(timezone.utc) + timedelta(seconds=3600)

    if oauth_account:
        oauth_account.provider_account_id = provider_account_id
        oauth_account.email = email
        oauth_account.access_token = credentials.token
        if credentials.refresh_token:
            oauth_account.refresh_token = credentials.refresh_token

        oauth_account.expires_at = expires_at
    else:
        oauth_account = OAuthAccount(
            user_id=user.id,
            provider="google",
            provider_account_id=provider_account_id,
            email=email,
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            expires_at=expires_at,
        )
        db.add(oauth_account)

    db.commit()

    token = _create_access_token(user)
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    redirect_target = f"{frontend_url.rstrip('/')}/dashboard?token={quote(token)}"
    return RedirectResponse(redirect_target)


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
