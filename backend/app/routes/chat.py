from fastapi import APIRouter, Depends
from pydantic import BaseModel
from google.genai import types

from app.agent.runner import runner
from app.auth.dependencies import get_current_user

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str


@router.post("/chat")
async def chat(request: ChatRequest, current_user = Depends(get_current_user)):
    user_id = current_user.id
    
    content = types.Content(
        role="user",
        parts=[
            types.Part(
                text=request.message
            )
        ],
    )

    events = runner.run_async(
        user_id=user_id,
        session_id=request.session_id,
        new_message=content,
    )

    final_response = None

    async for event in events:

        if event.is_final_response():

            if event.content and event.content.parts:

                final_response = event.content.parts[0].text

    return {
        "session_id": request.session_id,
        "response": final_response,
    }