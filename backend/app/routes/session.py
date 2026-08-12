from fastapi import APIRouter
from app.agent.runner import session_service

router = APIRouter()


@router.post("/session")
async def create_session(user_id: str):

    session = await session_service.create_session(
        app_name="email_agent",
        user_id=user_id,
    )

    return {
        "session_id": session.id
    }