import os

from dotenv import load_dotenv

load_dotenv()


def get_jwt_secret_key() -> str:
    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        raise RuntimeError("JWT_SECRET_KEY must be configured")
    if len(secret_key.encode("utf-8")) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be at least 32 bytes long")
    return secret_key


SECRET_KEY = get_jwt_secret_key()
ALGORITHM = "HS256"