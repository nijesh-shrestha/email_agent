from googleapiclient.discovery import build

from .google_oauth_service import get_google_credentials

def get_gmail_service(db, user_id):

    creds = get_google_credentials(
        db,
        user_id
    )

    return build(
        "gmail",
        "v1",
        credentials=creds,
    )