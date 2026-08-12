import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from fastapi import Request

router = APIRouter(
    prefix="/auth/google",
    tags=["Google OAuth"]
)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send"
]


def create_flow():

    client_config = {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [
                os.getenv("GOOGLE_REDIRECT_URI")
            ],
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=os.getenv("GOOGLE_REDIRECT_URI"),
    )

    return flow


@router.get("")
def google_login():

    flow = create_flow()

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    return RedirectResponse(authorization_url)


@router.get("/callback")
def google_callback(
    request: Request,
    code: str,
):
    flow = create_flow()

    flow.fetch_token(code=code)

    credentials = flow.credentials

    return {
        "message": "Google OAuth successful",
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token,
    }