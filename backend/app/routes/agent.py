from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.agent.runner import default_session_id_for_user, run_agent_message
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/agent", tags=["Agent"])


class AgentRequest(BaseModel):
    message: Annotated[str, Field(min_length=1, max_length=3000)]
    session_id: str | None = None


class AgentEventPart(BaseModel):
    text: str | None = None
    thought: bool | None = None
    function_call: Any | None = None
    function_response: Any | None = None
    tool_call: Any | None = None
    tool_response: Any | None = None
    part_metadata: Any | None = None


class AgentEvent(BaseModel):
    author: str | None = None
    invocation_id: str | None = None
    partial: bool = False
    content: list[AgentEventPart] = Field(default_factory=list)


class AgentResponse(BaseModel):
    session_id: str
    events: list[AgentEvent] = Field(default_factory=list)


@router.post("/run", response_model=AgentResponse)
def run_agent(request: AgentRequest, current_user=Depends(get_current_user)):
    session_id = request.session_id or default_session_id_for_user(str(current_user.id))

    try:
        events = run_agent_message(str(current_user.id), session_id, request.message)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return {"session_id": session_id, "events": events}
