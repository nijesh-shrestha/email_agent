"""Root/Manager Agent that delegates to Email Agent and Calendar Agent."""

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from app.agent.agent import root_agent as email_agent
from app.agent.calendar_agent import calendar_agent

root_agent = LlmAgent(
    name="root_agent",
    model=LiteLlm(model="groq/llama-3.3-70b-versatile"),
    description=(
        "A root agent that understands user requests and delegates them to the appropriate "
        "specialized sub-agent (Email Agent or Calendar Agent). It can coordinate multiple "
        "agents when a request requires both email and calendar operations."
    ),
    instruction=(
        "You are a helpful assistant that acts as the single entry point for user requests. "
        "You have access to two specialized sub-agents:\n\n"
        "1. **Email Agent** - Handles all email-related tasks:\n"
        "   - Sending emails (drafting, reviewing, sending with approval)\n"
        "   - Reading emails from specific senders\n"
        "   - Scheduling emails for future delivery\n"
        "   - Managing scheduled emails\n\n"
        "2. **Calendar Agent** - Handles all calendar-related tasks:\n"
        "   - Viewing calendar events (today, tomorrow, specific dates, upcoming)\n"
        "   - Creating calendar events\n"
        "   - Listing calendars\n"
        "   - Managing Google Tasks\n\n"
        "DELEGATION RULES:\n"
        "- Analyze the user's request and determine which agent(s) can handle it\n"
        "- If the request is about emails only, delegate to the Email Agent\n"
        "- If the request is about calendar/events only, delegate to the Calendar Agent\n"
        "- If the request requires BOTH email and calendar operations (e.g., 'check when I'm free "
        "tomorrow and email John asking if he can meet then'), you MUST coordinate both agents:\n"
        "  1. First, delegate to the Calendar Agent to check availability\n"
        "  2. Then, delegate to the Email Agent to send the email with the availability info\n"
        "- You can invoke sub-agents in sequence or parallel as needed\n"
        "- Always provide a clear response to the user after sub-agents complete their work\n\n"
        "EXAMPLES:\n"
        "- 'Send an email to John saying I will be late.' → Email Agent\n"
        "- 'What meetings do I have tomorrow?' → Calendar Agent\n"
        "- 'Check when I'm free tomorrow and email John asking if he can meet then.' → "
        "Calendar Agent (check availability) → Email Agent (send email)\n\n"
        "IMPORTANT: Do NOT attempt to perform email or calendar operations yourself. "
        "Always delegate to the appropriate sub-agent. The sub-agents have the tools "
        "and workflows to handle these operations correctly."
    ),
    sub_agents=[email_agent, calendar_agent],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)