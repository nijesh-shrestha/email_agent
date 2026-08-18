from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.session import init_db
from app.routes.auth import router as auth_router
from app.routes.google_auth import router as google_auth_router
from app.routes.agent import router as agent_router
from app.routes.gmail import router as gmail_router
from app.routes.scheduled_emails import router as scheduled_emails_router
from app.services.scheduler_service import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - start/stop scheduler."""
    # Startup
    await start_scheduler()
    yield
    # Shutdown
    await stop_scheduler()


app = FastAPI(title="AI Email Agent", lifespan=lifespan)

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
app.include_router(scheduled_emails_router, prefix="/api/scheduled-emails", tags=["scheduled-emails"])


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
