"""Calendar agent routes for interacting with Google Calendar."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.agent.calendar_runner import run_calendar_agent_message
from app.auth.dependencies import get_current_user
from app.database.session import SessionLocal
from app.services.calendar_service import (
    get_calendar_events,
    get_event_by_date,
    get_upcoming_events,
    list_calendars,
)
from app.utils.errors import InsufficientCalendarScopeError

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


class CalendarEvent(BaseModel):
    id: str
    summary: str
    description: str
    location: str
    start: str
    end: str
    status: str
    html_link: str
    creator: str
    organizer: str


class CalendarEventsResponse(BaseModel):
    success: bool
    count: int
    calendar_id: str
    time_min: str
    time_max: str
    events: list[CalendarEvent]


class CalendarListResponse(BaseModel):
    success: bool
    count: int
    calendars: list[dict]


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


@router.get("/events", response_model=CalendarEventsResponse)
def get_calendar_events_endpoint(
    current_user=Depends(get_current_user),
    time_min: str | None = Query(None, description="ISO format datetime for start of range"),
    time_max: str | None = Query(None, description="ISO format datetime for end of range"),
    max_results: int = Query(10, ge=1, le=100),
    calendar_id: str = Query("primary"),
):
    """Retrieve events from the user's Google Calendar."""
    db = SessionLocal()
    try:
        ok, payload = get_calendar_events(
            db, current_user.id, time_min, time_max, max_results, calendar_id
        )
        if not ok:
            error_type = payload.get("error")
            message = payload.get("message", payload.get("error", "Unknown error"))
            if error_type == "insufficient_calendar_scope":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=message,
                )
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)
        return payload
    finally:
        db.close()


@router.get("/events/date/{date}", response_model=CalendarEventsResponse)
def get_events_by_date(
    date: str,
    current_user=Depends(get_current_user),
    calendar_id: str = Query("primary"),
):
    """Retrieve events for a specific date (YYYY-MM-DD)."""
    db = SessionLocal()
    try:
        ok, payload = get_event_by_date(db, current_user.id, date, calendar_id)
        if not ok:
            error_type = payload.get("error")
            message = payload.get("message", payload.get("error", "Unknown error"))
            if error_type == "insufficient_calendar_scope":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=message,
                )
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)
        return payload
    finally:
        db.close()


@router.get("/events/upcoming", response_model=CalendarEventsResponse)
def get_upcoming_events_endpoint(
    current_user=Depends(get_current_user),
    days: int = Query(7, ge=1, le=365),
    max_results: int = Query(20, ge=1, le=100),
    calendar_id: str = Query("primary"),
):
    """Retrieve upcoming events for the next N days."""
    db = SessionLocal()
    try:
        ok, payload = get_upcoming_events(db, current_user.id, days, max_results, calendar_id)
        if not ok:
            error_type = payload.get("error")
            message = payload.get("message", payload.get("error", "Unknown error"))
            if error_type == "insufficient_calendar_scope":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=message,
                )
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)
        return payload
    finally:
        db.close()


@router.get("/calendars", response_model=CalendarListResponse)
def list_calendars_endpoint(current_user=Depends(get_current_user)):
    """List all calendars the user has access to."""
    db = SessionLocal()
    try:
        ok, payload = list_calendars(db, current_user.id)
        if not ok:
            error_type = payload.get("error")
            message = payload.get("message", payload.get("error", "Unknown error"))
            if error_type == "insufficient_calendar_scope":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=message,
                )
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)
        return payload
    finally:
        db.close()
