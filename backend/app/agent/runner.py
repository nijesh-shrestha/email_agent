from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from .agent import root_agent


session_service = InMemorySessionService()

runner = Runner(
    app_name="email_agent",
    agent=root_agent,
    session_service=session_service,
)