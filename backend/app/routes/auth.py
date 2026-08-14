from datetime import datetime, timedelta, timezone
import os

import jwt
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.auth.dependencies import get_current_user
from app.database.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key")
ALGORITHM = "HS256"


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    image: str | None = None
    model_config = ConfigDict(from_attributes=True)


def _create_access_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "name": user.name,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@router.get("/me", response_model=UserOut)
def get_current_user_profile(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)
