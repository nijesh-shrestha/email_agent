"""Lightweight runner utilities for manual testing Module 4.

This module exposes a small manual_test() helper that demonstrates the agent
and tools wiring without requiring a full production Runner configuration.
"""
from importlib import import_module

from google.adk.runners import Runner
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
