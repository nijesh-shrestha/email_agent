import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.models import User
from app.database.session import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key")
ALGORITHM = "HS256"


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    image: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def _create_access_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "name": user.name,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/register", response_model=AuthResponse)
def register_user(request: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    email = request.email.strip().lower()
    if not email or len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password (8+ characters) are required",
        )

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with that email already exists",
        )

    user = User(
        email=email,
        name=request.name.strip() if request.name else email.split("@", 1)[0],
        password_hash=_hash_password(request.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return AuthResponse(
        access_token=_create_access_token(user),
        user=UserOut.model_validate(user),
    )


@router.post("/login", response_model=AuthResponse)
def login_user(request: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    email = request.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()

    if not user or not user.password_hash or not _verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return AuthResponse(
        access_token=_create_access_token(user),
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
def get_current_user_profile(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)
