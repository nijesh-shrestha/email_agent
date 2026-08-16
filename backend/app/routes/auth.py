from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.auth.dependencies import get_current_user
from app.database.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    image: str | None = None
    model_config = ConfigDict(from_attributes=True)


@router.get("/me", response_model=UserOut)
def get_current_user_profile(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)