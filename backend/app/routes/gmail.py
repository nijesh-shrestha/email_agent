from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.services.gmail_service import send_email

router = APIRouter(prefix="/gmail", tags=["Gmail"])


class SendRequest(BaseModel):
    to: EmailStr
    subject: str
    body: str


@router.post("/send")
def gmail_send(request: SendRequest, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        ok, payload = send_email(db, current_user.id, request.to, request.subject, request.body)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    if not ok:
        raise HTTPException(status_code=500, detail=payload)

    return {"status": "ok", **payload}
