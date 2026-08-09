from fastapi import APIRouter, Depends

from app.agent.runner import session_service
from app.auth.dependencies import get_current_user
from app.database.models import User

router = APIRouter()


@router.post("/session")
async def create_session(current_user: User = Depends(get_current_user)):
    session = await session_service.create_session(
        app_name="email_agent",
        user_id=str(current_user.id),
    )

    return {
        "session_id": session.id,
    }