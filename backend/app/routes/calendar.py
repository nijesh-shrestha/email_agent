"""Calendar agent routes for interacting with Google Calendar."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.agent.calendar_runner import run_calendar_agent_message
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/calendar", tags=["Calendar Agent"])


class CalendarAgentRequest(BaseModel):
    message: Annotated[str, Field(min_length=1, max_length=3000)]
    session_id: str | None = None


class CalendarAgentEventPart(BaseModel):
    text: str | None = None
    thought: bool | None = None
    function_call: Any | None = None
    function_response: Any | None = None
    tool_call: Any | None = None
    tool_response: Any | None = None
    part_metadata: Any | None = None


class CalendarAgentEvent(BaseModel):
    author: str | None = None
    invocation_id: str | None = None
    partial: bool = False
    content: list[CalendarAgentEventPart] = Field(default_factory=list)


class CalendarAgentResponse(BaseModel):
    session_id: str
    events: list[CalendarAgentEvent] = Field(default_factory=list)


@router.post("/run", response_model=CalendarAgentResponse)
def run_calendar_agent(
    request: CalendarAgentRequest, current_user=Depends(get_current_user)
):
    """Run the calendar agent with a user message."""
    session_id = request.session_id or f"calendar-user-{current_user.id}"

    try:
        events = run_calendar_agent_message(str(current_user.id), session_id, request.message)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc

    return {"session_id": session_id, "events": events}
