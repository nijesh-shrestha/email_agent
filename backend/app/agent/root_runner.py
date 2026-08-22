"""Runner for the root agent.

This module provides utilities for running the root agent.
"""

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent.root_agent import root_agent


def get_root_runner() -> Runner:
    """Get or create a Runner instance for the root agent."""
    session_service = InMemorySessionService()
    runner = Runner(
        app_name="root_agent",
        agent=root_agent,
        session_service=session_service,
    )
    return runner


def build_user_content(message: str) -> types.Content:
    """Build a user content object for the agent from a plain text message."""
    return types.Content(role="user", parts=[types.Part(text=message)])


def _serialize_model_obj(obj: object) -> object:
    """Serialize a model object to a dictionary."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        try:
            return obj.dict()
        except Exception:
            pass
    return str(obj)


def _serialize_part(part: types.Part) -> dict:
    """Serialize a part of an event."""
    return {
        "text": getattr(part, "text", None),
        "thought": getattr(part, "thought", None),
        "function_call": _serialize_model_obj(getattr(part, "function_call", None)),
        "function_response": _serialize_model_obj(getattr(part, "function_response", None)),
        "tool_call": _serialize_model_obj(getattr(part, "tool_call", None)),
        "tool_response": _serialize_model_obj(getattr(part, "tool_response", None)),
        "part_metadata": getattr(part, "part_metadata", None),
    }


def serialize_event(event: object) -> dict:
    """Serialize an agent event for JSON response."""
    content = getattr(getattr(event, "content", None), "parts", None) or []
    return {
        "author": getattr(event, "author", None),
        "invocation_id": getattr(event, "invocation_id", None),
        "partial": getattr(event, "partial", False),
        "content": [_serialize_part(part) for part in content],
    }


def run_root_agent_message(user_id: str, session_id: str, message: str) -> list[dict]:
    """Run the root agent with a message and return serialized events.

    Args:
        user_id: The user's ID
        session_id: Session identifier for conversation continuity
        message: The user's message to the agent

    Returns:
        List of serialized events from the agent
    """
    runner = get_root_runner()
    user_content = build_user_content(message)
    events = []
    for event in runner.run(user_id=str(user_id), session_id=session_id, new_message=user_content):
        events.append(serialize_event(event))
    return events