"""Lightweight runner utilities for manual testing Module 4.

This module exposes a small manual_test() helper that demonstrates the agent
and tools wiring without requiring a full production Runner configuration.
"""
from importlib import import_module

from google.adk.runners import Runner
from google.genai import types
# InMemorySessionService may or may not be present depending on ADK version.
# Import safely.
try:
    from google.adk.sessions import InMemorySessionService
except Exception:
    InMemorySessionService = None

# Import the package agent
agent_mod = import_module('app.agent.agent')
root_agent = agent_mod.root_agent

# Tools for tests
try:
    from app.agent.tools import get_user_tool, send_email_stub
except Exception:
    get_user_tool = None
    send_email_stub = None


# Provide a Runner instance when InMemorySessionService is available.
runner = None
if InMemorySessionService is not None:
    try:
        session_service = InMemorySessionService()
        runner = Runner(app_name="email_agent", agent=root_agent, session_service=session_service)
    except Exception:
        runner = None


def get_runner() -> Runner:
    global runner
    if runner is not None:
        return runner
    if InMemorySessionService is None:
        raise RuntimeError(
            "ADK InMemorySessionService is unavailable in this environment. "
            "Install a compatible google-adk and google-genai version."
        )
    try:
        session_service = InMemorySessionService()
        runner = Runner(app_name="email_agent", agent=root_agent, session_service=session_service)
        return runner
    except Exception as exc:
        raise RuntimeError("Failed to initialize ADK Runner") from exc


def build_user_content(message: str) -> types.Content:
    """Build a user content object for the agent from a plain text message."""
    return types.Content(role="user", parts=[types.Part(text=message)])


def _serialize_model_obj(obj: object) -> object:
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
    content = getattr(getattr(event, "content", None), "parts", None) or []
    return {
        "author": getattr(event, "author", None),
        "invocation_id": getattr(event, "invocation_id", None),
        "partial": getattr(event, "partial", False),
        "content": [_serialize_part(part) for part in content],
    }


def default_session_id_for_user(user_id: str) -> str:
    return f"user-{user_id}"


def run_agent_message(user_id: str, session_id: str, message: str) -> list[dict]:
    runner = get_runner()
    user_content = build_user_content(message)
    events = []
    for event in runner.run(user_id=str(user_id), session_id=session_id, new_message=user_content):
        events.append(serialize_event(event))
    return events


def create_test_agent_copy():
    """Return a copy/shallow-clone of the root agent with the send tool
    replaced by the non-destructive stub for safe local testing.

    This does not start any ADK session — it only prepares an agent object
    that can later be run with a properly-configured Runner.
    """
    global root_agent
    try:
        new_agent = root_agent.copy()
        new_tools = []
        for t in getattr(new_agent, 'tools', []) or []:
            tname = getattr(t, '__name__', None) or getattr(t, 'name', None)
            if tname and 'send_email' in tname:
                # prefer stub if available
                new_tools.append(send_email_stub or t)
            else:
                new_tools.append(t)
        new_agent.tools = new_tools
    except Exception:
        # fallback: modify a shallow reference (not ideal for concurrent runs)
        new_agent = root_agent
        tools = []
        for t in getattr(new_agent, 'tools', []) or []:
            tname = getattr(t, '__name__', None) or getattr(t, 'name', None)
            if tname and 'send_email' in tname:
                tools.append(send_email_stub or t)
            else:
                tools.append(t)
        new_agent.tools = tools
    return new_agent


def manual_test():
    """Simple developer-facing test that demonstrates tools wiring.

    - Prints agent name and tools
    - Calls get_user_tool for a missing user id
    - Calls the stubbed send_email to show deterministic output
    """
    print('Root agent:', getattr(root_agent, 'name', '<unnamed>'))
    print('Tools:')
    for t in getattr(root_agent, 'tools', []) or []:
        print(' -', getattr(t, '__name__', getattr(t, 'name', str(t))))

    if get_user_tool is not None:
        print('\nget_user_tool(999999) =>', get_user_tool('999999'))
    else:
        print('\nget_user_tool not available in this environment')

    if send_email_stub is not None:
        print('\nsend_email_stub =>', send_email_stub('1', 'test@example.com', 'Stubbed test', 'Hello'))
    else:
        print('\nsend_email_stub not available in this environment')


if __name__ == '__main__':
    manual_test()
