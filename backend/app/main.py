from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.session import init_db
from app.routes.auth import router as auth_router
from app.routes.google_auth import router as google_auth_router
from app.routes.agent import router as agent_router
from app.routes.gmail import router as gmail_router

app = FastAPI(title="AI Email Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

app.include_router(auth_router, prefix="/api")
app.include_router(google_auth_router, prefix="/api")
app.include_router(agent_router, prefix="/api")
app.include_router(gmail_router, prefix="/api")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
