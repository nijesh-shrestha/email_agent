from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.services.gmail_service import send_email
from app.services.rate_limiter import allow_send

router = APIRouter(prefix="/gmail", tags=["Gmail"])


# Basic server-side validation constraints
SubjectStr = Annotated[str, Field(min_length=1, max_length=255)]
BodyStr = Annotated[str, Field(min_length=1, max_length=10000)]


class SendRequest(BaseModel):
    to: EmailStr
    subject: SubjectStr
    body: BodyStr


@router.post("/send")
def gmail_send(request: SendRequest, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # Rate limiting (per-user)
    allowed, meta = allow_send(str(current_user.id))
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limited",
                **meta,
            },
        )

    # Ensure the user has a connected Google account - send_email will raise ValueError if not
    try:
        ok, payload = send_email(db, current_user.id, request.to, request.subject, request.body)
    except ValueError as ve:
        # likely not connected
        raise HTTPException(status_code=400, detail=str(ve))

    if not ok:
        # payload contains error detail
        raise HTTPException(status_code=500, detail=payload)

    # Return success + rate limit meta for client convenience
    return {"status": "ok", **payload, "rate_limit": meta}
