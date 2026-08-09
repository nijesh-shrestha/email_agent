from fastapi import FastAPI

from .routes.google_auth import router as google_auth_router
from .routes.chat import router as chat_router
from .routes.session import router as session_router

app = FastAPI()

app.include_router(google_auth_router)
app.include_router(
    chat_router,
    prefix="/api"
)
app.include_router(
    session_router,
    prefix="/api"
)