from fastapi import FastAPI

from .routes.google_auth import router as google_auth_router

app = FastAPI()

app.include_router(google_auth_router)