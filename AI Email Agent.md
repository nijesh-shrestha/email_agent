# AI Email Agent — Complete Application Architecture & Implementation Specification

## 1. Project Overview

Build a production-oriented, multi-user AI Email Assistant that allows authenticated users to connect their Google/Gmail account and interact with an AI agent through a web chat interface.

The user should be able to:

1. Register/login to the application.
2. Authenticate with Google.
3. Connect their Gmail account.
4. Open a chat interface.
5. Ask the AI agent to compose an email.
6. Review the generated email draft.
7. Explicitly confirm the draft.
8. Have the agent send the email through the authenticated user's Gmail account.
9. Ask the agent to read messages from a specific sender on selected dates and limit the number returned.
10. Store users, OAuth information, conversations, and messages in Supabase PostgreSQL.
11. Maintain separate data and Gmail credentials for every user.

The application must be **multi-user**.

A user's Gmail credentials must NEVER be shared with another user.

## 1.1 New Gmail Read Workflow

The backend now supports a read-email workflow for the agent and the UI.

Required input contract:

- of_user: the sender email address to search for
- dates: an array of ISO dates such as ["2026-08-01", "2026-08-03"]
- amount: the maximum number of matching messages to return

Example request payload:

```json
{
  "of_user": "sender@example.com",
  "dates": ["2026-08-01", "2026-08-03"],
  "amount": 5
}
```

The system calls Gmail's `messages.list` API with a query like `from:(sender@example.com) after:... before:...` and then fetches the message metadata for each result.

The response contains summary fields such as:

- id
- thread_id
- from
- subject
- date
- snippet
- count

This read workflow is available in both the backend API at `/api/gmail/read` and through the agent tool `read_emails_tool`.

---

# 2. Core Architecture

```text
                         ┌─────────────────────┐
                         │       Browser       │
                         │                     │
                         │  Login / Chat UI    │
                         └──────────┬──────────┘
                                    │
                                    │ HTTPS
                                    ▼
                         ┌─────────────────────┐
                         │      FastAPI        │
                         │      Backend        │
                         │                     │
                         │ Authentication      │
                         │ OAuth callbacks     │
                         │ Chat API            │
                         │ User API             │
                         └──────────┬──────────┘
                                    │
                  ┌─────────────────┼─────────────────┐
                  │                 │                 │
                  ▼                 ▼                 ▼
           ┌────────────┐    ┌──────────────┐  ┌──────────────┐
           │ Supabase   │    │ Google ADK   │  │ Google OAuth │
           │ PostgreSQL │    │              │  │              │
           │            │    │ Agent        │  │ Gmail API    │
           │ Users      │    │ Sessions     │  │              │
           │ Chats      │    │ Tools        │  │ OAuth tokens │
           │ Messages   │    │ State        │  │              │
           │ OAuth      │    │              │  │              │
           └────────────┘    └──────┬───────┘  └──────────────┘
                                    │
                                    ▼
                             ┌──────────────┐
                             │  Gmail Tool  │
                             │              │
                             │ send_email() │
                             └──────┬───────┘
                                    │
                                    ▼
                             User's Gmail
```

---

# 3. Technology Stack

## Frontend

Use:

- React / Next.js
- TypeScript
- Tailwind CSS
- Chat interface
- Authentication UI
- Google OAuth connection UI

The frontend communicates with the FastAPI backend using HTTPS APIs.

---

## Backend

Use:

- Python
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- Google ADK
- Google OAuth libraries
- Google Gmail API

---

## Database

Use:

- Supabase
- PostgreSQL
- SQLAlchemy ORM
- Alembic migrations

Supabase is primarily used as the PostgreSQL database.

The backend should connect to PostgreSQL using SQLAlchemy.

---

## AI

Use:

- Google ADK
- LiteLLM
- Groq
- `llama-3.3-70b-versatile`

The AI model is responsible for understanding user requests, composing email drafts, deciding when a tool is necessary, and interacting with the email tool.

---

## Email

Use:

- Google OAuth 2.0
- Gmail API

Required Gmail scope:

```text
https://www.googleapis.com/auth/gmail.send
```

---

## Deployment

Deploy the backend on:

- Render

Deploy the frontend separately using a suitable frontend hosting provider such as:

- Vercel

The application should communicate through HTTPS.

---

# 4. Application Modules

The implementation is divided into the following modules:

```text
Module 1 — Authentication
Module 2 — Database
Module 3 — Google OAuth & Gmail
Module 4 — Google ADK Integration
Module 5 — Email Workflow
Module 6 — Chat Frontend
Module 7 — FastAPI Backend
Module 8 — Deployment
Module 9 — Production Scaling
```

---

# 5. Module 1 — Authentication

Implement application-level authentication.

Users need their own account in the application.

Recommended architecture:

```text
Browser
   │
   ▼
Authentication API
   │
   ▼
User table
```

Each user receives a unique:

```text
user_id
```

The `user_id` becomes the central identity used throughout the system.

---

## Authentication requirements

The backend must be able to determine:

```text
Who is making this request?
```

For every authenticated request.

Example:

```python
current_user.id
```

The authenticated user's ID must then be used when:

- loading chats
- loading messages
- loading OAuth accounts
- accessing Gmail
- creating ADK sessions
- saving messages
- sending emails

Never trust a `user_id` supplied directly by the frontend when it can be obtained from the authenticated session/JWT.

---

# 6. Module 2 — Database

Use PostgreSQL through Supabase.

SQLAlchemy is the ORM.

Alembic handles schema migrations.

Suggested structure:

```text
backend/
│
├── app/
│   ├── database/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── models/
│   │       ├── user_model.py
│   │       ├── oauthaccount_model.py
│   │       ├── chat_model.py
│   │       └── message_model.py
│   │
│   └── ...
│
├── alembic/
│   ├── env.py
│   └── versions/
│
└── alembic.ini
```

---

# 7. Database Models

## 7.1 User

Represents an application user.

Suggested fields:

```text
users
--------------------------------
id
email
name
password_hash       (if local authentication is supported)
created_at
updated_at
```

`id` is the primary key.

---

## 7.2 OAuthAccount

Stores OAuth information associated with a user.

Suggested structure:

```text
oauth_accounts
--------------------------------
id
user_id
provider
provider_account_id
access_token
refresh_token
token_uri
client_id
client_secret
expires_at
scopes
created_at
updated_at
```

Relationship:

```text
User
 │
 └── OAuthAccount
```

A user can potentially have multiple OAuth providers/accounts.

Example:

```text
User 1
 └── Google OAuth Account
```

---

## 7.3 ChatSession

Represents a conversation.

```text
chat_sessions
--------------------------------
id
user_id
title
adk_session_id
created_at
updated_at
```

Relationship:

```text
User
 └── ChatSession
       └── Messages
```

Important:

`adk_session_id` connects the application's chat with the corresponding ADK session.

---

## 7.4 Message

Stores individual chat messages.

```text
messages
--------------------------------
id
chat_session_id
role
content
created_at
```

Possible roles:

```text
user
assistant
system
tool
```

Example:

```text
ChatSession
│
├── User: "Send an email to John"
├── Assistant: "What should the email say?"
├── User: "Tell him the meeting is tomorrow."
├── Assistant: "Here is the draft..."
└── User: "Yes, send it."
```

---

# 8. Database Relationships

```text
User
 │
 ├───────────────┐
 │               │
 ▼               ▼
OAuthAccount   ChatSession
                 │
                 ▼
              Message
```

More specifically:

```text
users.id
   │
   ├── oauth_accounts.user_id
   │
   └── chat_sessions.user_id
             │
             └── messages.chat_session_id
```

---

# 9. Module 3 — Google OAuth & Gmail

This module connects the application user to their Gmail account.

The OAuth flow should be:

```text
User
 │
 │ Click "Connect Gmail"
 ▼
Backend
 │
 │ Generate Google authorization URL
 ▼
Google
 │
 │ User grants permission
 ▼
Google Callback
 │
 ▼
Backend
 │
 │ Exchange authorization code
 ▼
OAuth Tokens
 │
 ▼
oauth_accounts table
```

---

# 10. Google OAuth Security

Never store:

```text
credentials.json
token.json
```

in GitHub.

`credentials.json` contains the Google application's OAuth client information.

User-specific OAuth tokens should be stored securely in the database.

For production:

```text
Google OAuth
     ↓
OAuth tokens
     ↓
Encrypted/secure database storage
```

Do not expose OAuth tokens to:

- frontend
- browser
- LLM
- logs
- GitHub

---

# 11. Gmail Service

Create a dedicated service:

```text
app/services/gmail_service.py
```

The Gmail service should NOT use a single global:

```text
token.json
```

Instead it should receive:

```python
user_id
```

Example conceptual API:

```python
def get_gmail_service(
    db: Session,
    user_id: int
):
    ...
```

The function:

1. Finds the user's `OAuthAccount`.
2. Loads their Google credentials.
3. Refreshes the token if necessary.
4. Builds the Gmail API client.
5. Returns the Gmail service.

---

# 12. Gmail Service Flow

```text
Authenticated User
        │
        ▼
     user_id
        │
        ▼
OAuthAccount
        │
        ▼
Google Credentials
        │
        ▼
Refresh if expired
        │
        ▼
Gmail API Client
        │
        ▼
Gmail
```

This ensures:

```text
User A → Gmail A
User B → Gmail B
User C → Gmail C
```

and never:

```text
User A → Gmail B
```

---

# 13. Module 4 — Google ADK Integration

The AI agent is built using Google ADK.

Basic architecture:

```text
FastAPI
   │
   ▼
ADK Runner
   │
   ▼
ADK Session
   │
   ▼
Root Agent
   │
   ▼
LLM
   │
   ├── Reasoning
   ├── Conversation
   └── Tool selection
             │
             ▼
         send_email()
```

---

# 14. Agent

The root agent should be responsible for email-related conversations.

Example:

```python
root_agent = Agent(
    name="email_agent",
    model=LiteLlm(
        model="groq/llama-3.3-70b-versatile"
    ),
    description=(
        "An AI email assistant that composes "
        "and sends emails through Gmail."
    ),
    instruction="...",
    tools=[send_email],
)
```

---

# 15. ADK Tool

The main tool is:

```python
send_email()
```

The tool should receive:

```python
to
subject
body
tool_context
```

Example:

```python
def send_email(
    to: str,
    subject: str,
    body: str,
    tool_context: ToolContext,
):
    ...
```

The LLM provides:

```text
to
subject
body
```

ADK provides:

```text
tool_context
```

The model should NEVER provide the authenticated `user_id`.

---

# 16. Connecting User Identity to ADK

The application must put the authenticated user's identity into ADK state.

Conceptually:

```python
tool_context.state["user_id"]
```

Then the tool can retrieve:

```python
user_id = tool_context.state.get("user_id")
```

The architecture is:

```text
JWT / Authentication
       │
       ▼
current_user
       │
       ▼
current_user.id
       │
       ▼
ADK session state
       │
       ▼
state["user_id"]
       │
       ▼
ToolContext
       │
       ▼
send_email()
```

This is critical for multi-user security.

---

# 17. ADK Session vs Database Chat

There are two different concepts.

## ADK Session

Used by ADK to maintain the agent's execution/conversation state.

```text
ADK Session
 ├── events
 ├── state
 ├── conversation
 └── agent execution information
```

## Application ChatSession

Stored in PostgreSQL.

```text
ChatSession
 ├── id
 ├── user_id
 ├── title
 └── messages
```

They should be connected:

```text
ChatSession.adk_session_id
            │
            ▼
       ADK Session
```

The database is the application's persistent record.

ADK manages the agent's runtime conversation/session.

---

# 18. Module 5 — Email Workflow

The email workflow must enforce explicit user confirmation.

The agent must NOT send an email immediately after generating a draft.

Correct workflow:

```text
User:
"Send an email to John saying the meeting
is tomorrow."

             ↓

Agent collects missing information

             ↓

Agent creates draft

             ↓

Agent:
"Here is the draft:

To: John
Subject: Meeting Tomorrow

The meeting is tomorrow.

Would you like me to send it?"

             ↓

User:
"Yes"

             ↓

Agent calls send_email()

             ↓

Gmail API

             ↓

Success

             ↓

Agent:
"Email sent successfully."
```

---

# 19. Email Confirmation Rule

The agent instruction must enforce:

1. Collect recipient.
2. Collect subject.
3. Collect body.
4. Generate complete draft.
5. Show draft.
6. Ask for confirmation.
7. Wait.
8. Do NOT call Gmail before confirmation.
9. Only send after explicit confirmation.
10. Send exactly once.
11. Report the result.

Confirmation examples:

```text
yes
send
confirm
yes, send it
go ahead
```

The implementation should preferably use an explicit workflow/state rather than relying entirely on natural-language interpretation.

---

# 20. Prevent Duplicate Email Sending

A major production requirement is preventing accidental duplicate sends.

The backend should track the email-send operation.

Possible state:

```text
draft
awaiting_confirmation
sending
sent
failed
```

Example:

```text
awaiting_confirmation
        │
        │ user confirms
        ▼
      sending
        │
        ├── success → sent
        │
        └── failure → failed
```

The same confirmation must not cause two Gmail API calls.

---

# 21. Module 6 — Chat Frontend

The frontend should contain:

```text
Login Page
     │
     ▼
Dashboard
     │
     ├── Gmail connection status
     │
     ├── Chat list
     │
     └── Chat interface
```

---

# 22. Chat UI

Example:

```text
┌───────────────────────────────────────────┐
│ AI Email Assistant                        │
├───────────────┬───────────────────────────┤
│ Conversations │                           │
│               │   Assistant               │
│ Chat 1        │   What email would you    │
│ Chat 2        │   like to send?           │
│ Chat 3        │                           │
│               │   User                    │
│ + New Chat    │   Send an email to John   │
│               │                           │
│               │   Assistant               │
│               │   Here is the draft...    │
│               │                           │
│               │   [Send] [Edit]           │
├───────────────┴───────────────────────────┤
│ Type a message...                    [➤]  │
└───────────────────────────────────────────┘
```

---

# 23. Frontend Authentication

The frontend must never directly access Gmail credentials.

The frontend only knows:

```text
authenticated user
```

and communicates with:

```text
FastAPI
```

Example:

```text
Frontend
   │
   │ Authorization
   ▼
FastAPI
   │
   ▼
Authenticated user
```

---

# 24. Gmail Connection UI

Provide a page/button:

```text
Gmail
────────────────────────

Status: Connected

Gmail account:
user@gmail.com

[Disconnect Gmail]
```

If disconnected:

```text
Gmail
────────────────────────

Status: Not connected

[Connect Gmail]
```

---

# 25. Module 7 — FastAPI Backend

FastAPI should act as the main application backend.

Suggested structure:

```text
backend/
│
├── app/
│   │
│   ├── main.py
│   │
│   ├── agent/
│   │   ├── agent.py
│   │   ├── runner.py
│   │   └── tools/
│   │       └── email_tools.py
│   │
│   ├── auth/
│   │   ├── dependencies.py
│   │   ├── routes.py
│   │   └── service.py
│   │
│   ├── database/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── models/
│   │       ├── user_model.py
│   │       ├── oauthaccount_model.py
│   │       ├── chat_model.py
│   │       └── message_model.py
│   │
│   ├── oauth/
│   │   ├── google.py
│   │   └── routes.py
│   │
│   ├── services/
│   │   └── gmail_service.py
│   │
│   └── api/
│       ├── chat.py
│       ├── users.py
│       └── gmail.py
│
├── alembic/
│   ├── env.py
│   └── versions/
│
├── alembic.ini
├── requirements.txt
└── .env
```

---

# 26. API Endpoints

Suggested endpoints:

## Authentication

```text
POST /auth/register
POST /auth/login
POST /auth/logout
GET  /auth/me
```

---

## Google OAuth

```text
GET /oauth/google
GET /oauth/google/callback
DELETE /oauth/google
GET /oauth/google/status
```

---

## Chat

```text
POST /api/chats
GET  /api/chats
GET  /api/chats/{chat_id}
DELETE /api/chats/{chat_id}
```

---

## Messages

```text
POST /api/chats/{chat_id}/messages
GET  /api/chats/{chat_id}/messages
```

---

## Agent

The frontend should send a message to:

```text
POST /api/chats/{chat_id}/messages
```

The backend:

1. Authenticates the user.
2. Gets `user_id`.
3. Gets/creates the ADK session.
4. Adds user identity to state.
5. Sends the message to ADK.
6. Runs the agent.
7. Handles tool calls.
8. Saves the resulting messages.
9. Returns the assistant response.

---

# 27. Complete Chat Request Flow

```text
Browser
   │
   │ POST /api/chats/123/messages
   │
   │ "Send an email to John"
   ▼
FastAPI
   │
   ├── Validate JWT
   │
   ├── Get current_user
   │
   ├── user_id = current_user.id
   │
   ├── Load ChatSession
   │
   ├── Verify chat belongs to user
   │
   ├── Get/create ADK session
   │
   ├── Set state["user_id"]
   │
   ▼
ADK Runner
   │
   ▼
Root Agent
   │
   ▼
LLM
   │
   ▼
Response
```

If an email must be sent:

```text
LLM
 │
 ▼
send_email()
 │
 ▼
ToolContext
 │
 ▼
user_id
 │
 ▼
OAuthAccount
 │
 ▼
Google credentials
 │
 ▼
Gmail API
 │
 ▼
Email sent
```

---

# 28. Security Model

Security is extremely important because the application can send emails.

## Rule 1 — User isolation

Every database query involving user-owned resources must filter by:

```python
user_id
```

For example:

```python
chat = (
    db.query(ChatSession)
    .filter(
        ChatSession.id == chat_id,
        ChatSession.user_id == current_user.id
    )
    .first()
)
```

Never:

```python
db.query(ChatSession).filter(
    ChatSession.id == chat_id
).first()
```

without checking ownership.

---

## Rule 2 — Never trust frontend user IDs

Do not accept:

```json
{
    "user_id": 25
}
```

from the frontend to determine the current user.

Instead:

```python
current_user.id
```

must come from authentication.

---

## Rule 3 — Never expose OAuth tokens

Never return:

```text
access_token
refresh_token
client_secret
```

through API responses.

---

## Rule 4 — Never put secrets in GitHub

`.gitignore` must include:

```text
.env
credentials.json
token.json
.venv/
__pycache__/
```

---

# 29. Environment Variables

Local development:

```text
DATABASE_URL=postgresql://...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GROQ_API_KEY=...
JWT_SECRET=...
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
```

Production:

```text
DATABASE_URL=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GROQ_API_KEY=...
JWT_SECRET=...
FRONTEND_URL=https://frontend-domain.com
BACKEND_URL=https://backend-domain.onrender.com
```

Do not hard-code these values.

---

# 30. Google OAuth Redirect URI

Local:

```text
http://localhost:8000/oauth/google/callback
```

Production:

```text
https://your-backend-domain.com/oauth/google/callback
```

The production callback URL must also be registered in Google Cloud Console.

---

# 31. Module 8 — Deployment

## Backend

Deploy FastAPI on Render.

The production server must bind to:

```text
0.0.0.0
```

and Render's port:

```text
$PORT
```

Example:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

If using ADK's development UI, it may be started using:

```bash
adk web --host 0.0.0.0 --port $PORT .
```

However, the production application should eventually expose the application's own FastAPI API rather than relying on the ADK development UI.

---

# 32. Important ADK Production Consideration

`adk web` is primarily useful for development/testing.

Production architecture should preferably be:

```text
Frontend
   │
   ▼
FastAPI
   │
   ▼
ADK Runner
   │
   ▼
Agent
```

rather than:

```text
Frontend
   │
   ▼
ADK Dev UI
```

The frontend should communicate with our own application API.

---

# 33. Render Deployment

Render environment variables must contain:

```text
DATABASE_URL
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
GROQ_API_KEY
JWT_SECRET
FRONTEND_URL
BACKEND_URL
```

Never upload:

```text
.env
credentials.json
token.json
```

to GitHub.

---

# 34. Database Migration Deployment

Alembic should be used for schema changes.

Typical process:

```bash
alembic revision --autogenerate -m "create users and oauth tables"
```

Then:

```bash
alembic upgrade head
```

Production deployment should run:

```bash
alembic upgrade head
```

before starting the application when appropriate.

---

# 35. Module 9 — Production Scaling

Once the application works, address:

### Session persistence

ADK sessions should not rely on local filesystem/in-memory storage in a multi-instance production environment.

Use a persistent session/state strategy.

---

### Database connection pooling

Configure SQLAlchemy appropriately for Supabase/PostgreSQL.

---

### OAuth token encryption

OAuth tokens should ideally be encrypted at rest.

---

### Background jobs

Long-running tasks should eventually use:

```text
Redis
Celery
RQ
or another job system
```

if required.

---

### Rate limiting

Prevent abuse:

```text
User → API → rate limiter → agent
```

---

### Logging

Log:

```text
request ID
user ID
chat ID
agent execution
tool execution
error
latency
```

Never log:

```text
access_token
refresh_token
client_secret
Gmail credentials
```

---

# 36. Recommended Final Architecture

```text
                         INTERNET
                             │
                             ▼
                    ┌─────────────────┐
                    │    Frontend     │
                    │                 │
                    │ React / Next.js │
                    └────────┬────────┘
                             │
                             │ HTTPS
                             ▼
                 ┌────────────────────────┐
                 │        FastAPI         │
                 │                        │
                 │ Authentication        │
                 │ Chat API              │
                 │ OAuth API             │
                 │ User API              │
                 └───────────┬────────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
            ▼                ▼                ▼
     ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
     │  Supabase   │  │ Google ADK   │  │ Google OAuth │
     │ PostgreSQL  │  │              │  │              │
     │             │  │ Runner       │  │ Gmail        │
     │ Users       │  │ Sessions     │  │              │
     │ OAuth       │  │ State        │  │ OAuth tokens │
     │ Chats       │  │ Agent        │  │              │
     │ Messages    │  │ Tools        │  │              │
     └─────────────┘  └──────┬───────┘  └──────┬───────┘
                             │                 │
                             │                 │
                             ▼                 │
                       ┌──────────────┐        │
                       │ send_email() │────────┘
                       └──────┬───────┘
                              │
                              ▼
                       ┌──────────────┐
                       │ User's Gmail │
                       └──────────────┘
```

---

# 37. End-to-End Example

Suppose Alice logs into the application.

Her user ID is:

```text
user_id = 42
```

She connects:

```text
Alice's Gmail
alice@gmail.com
```

The OAuth account is stored:

```text
oauth_accounts
--------------------------------
user_id = 42
provider = google
access_token = ...
refresh_token = ...
```

Alice opens:

```text
Chat #17
```

The database contains:

```text
chat_sessions
--------------------------------
id = 17
user_id = 42
adk_session_id = abc123
```

Alice sends:

```text
Send an email to John saying our meeting
has been moved to 3 PM tomorrow.
```

FastAPI authenticates Alice:

```python
current_user.id == 42
```

FastAPI verifies:

```text
Chat #17 belongs to user 42
```

Then ADK state becomes:

```python
state["user_id"] = 42
```

The agent creates the draft.

```text
To: John

Subject: Meeting Time Update

Hi John,

Our meeting has been moved to 3 PM tomorrow.

Best,
Alice
```

The agent asks:

```text
Would you like me to send this email?
```

Alice responds:

```text
Yes, send it.
```

The agent calls:

```python
send_email(
    to="john@example.com",
    subject="Meeting Time Update",
    body="...",
    tool_context=tool_context
)
```

The tool retrieves:

```python
user_id = tool_context.state["user_id"]
```

Result:

```text
42
```

Then:

```text
OAuthAccount
     │
     ▼
Alice's Gmail credentials
     │
     ▼
Gmail API
     │
     ▼
John receives email
```

---

# 38. Critical Multi-User Rule

The most important security property of this entire application is:

```text
Authenticated User
        ↓
       user_id
        ↓
Everything belongs to that user
```

Never use global Gmail credentials.

Never use a global `token.json`.

Never allow the LLM to choose the user ID.

Never trust a user ID supplied by the frontend.

Instead:

```text
Authentication
      ↓
current_user.id
      ↓
ADK state
      ↓
ToolContext
      ↓
OAuthAccount
      ↓
Gmail credentials
      ↓
Gmail API
```

---

# 39. Implementation Order

The coding AI should implement the project in this exact order:

```text
PHASE 1
Authentication
    ↓
PHASE 2
Database + SQLAlchemy
    ↓
PHASE 3
Alembic migrations
    ↓
PHASE 4
Google OAuth
    ↓
PHASE 5
OAuthAccount persistence
    ↓
PHASE 6
Gmail service
    ↓
PHASE 7
Google ADK integration
    ↓
PHASE 8
Authenticated user → ADK state
    ↓
PHASE 9
ADK tool → OAuthAccount
    ↓
PHASE 10
Email confirmation workflow
    ↓
PHASE 11
FastAPI chat endpoints
    ↓
PHASE 12
Chat frontend
    ↓
PHASE 13
Frontend/backend authentication
    ↓
PHASE 14
Testing
    ↓
PHASE 15
Deployment
    ↓
PHASE 16
Production hardening
```

---

# 40. Coding Rules for the AI Implementing This Project

When generating code, follow these rules:

### Rule 1

Do not rewrite working code unnecessarily.

Modify the existing project incrementally.

### Rule 2

Use SQLAlchemy models for database access.

Do not mix raw SQL and ORM unnecessarily.

### Rule 3

Use Alembic for schema changes.

Do not manually create production tables from application startup.

### Rule 4

Keep Gmail functionality inside a Gmail service.

Do not put Gmail API logic directly inside FastAPI routes.

### Rule 5

Keep ADK tools thin.

The tool should coordinate:

```text
ToolContext
    ↓
user_id
    ↓
Gmail service
```

rather than containing the entire application architecture.

### Rule 6

Keep authentication separate from agent logic.

The agent should not authenticate users itself.

FastAPI handles authentication.

### Rule 7

Never expose secrets.

### Rule 8

Every user-owned resource must be scoped by `user_id`.

### Rule 9

The LLM must never determine authorization.

The backend determines authorization.

### Rule 10

Email sending requires explicit confirmation.

---

# 41. Expected Final User Experience

The final application should feel like:

```text
┌────────────────────────────────────────────┐
│              AI EMAIL ASSISTANT            │
├────────────────────────────────────────────┤
│                                            │
│  Welcome, Nijesh                           │
│                                            │
│  Gmail: ✓ Connected                        │
│                                            │
│  ┌──────────────────────────────────────┐  │
│  │ You                                  │  │
│  │ Send an email to John about          │  │
│  │ tomorrow's meeting.                  │  │
│  └──────────────────────────────────────┘  │
│                                            │
│  ┌──────────────────────────────────────┐  │
│  │ AI                                   │  │
│  │                                      │  │
│  │ Here's the draft:                    │  │
│  │                                      │  │
│  │ To: John                             │  │
│  │ Subject: Meeting Tomorrow            │  │
│  │                                      │  │
│  │ Hi John,                             │  │
│  │ Our meeting is tomorrow...           │  │
│  │                                      │  │
│  │ Would you like me to send it?       │  │
│  └──────────────────────────────────────┘  │
│                                            │
│  ┌──────────────────────────────────────┐  │
│  │ Yes, send it.                        │  │
│  └──────────────────────────────────────┘  │
│                                            │
│  ┌──────────────────────────────────────┐  │
│  │ ✓ Email sent successfully            │  │
│  └──────────────────────────────────────┘  │
│                                            │
└────────────────────────────────────────────┘
```

---

# 42. Definition of Done

The project is considered complete when:

- [ ] User can register/login.
- [ ] Authenticated requests identify the correct user.
- [ ] Users can connect Google accounts.
- [ ] Google OAuth tokens are stored per user.
- [ ] Gmail credentials are never stored globally.
- [ ] Users can disconnect Google accounts.
- [ ] Users can create conversations.
- [ ] Conversations belong to individual users.
- [ ] Messages are persisted.
- [ ] ADK sessions are associated with application chats.
- [ ] Authenticated `user_id` is available to ADK.
- [ ] ADK tools cannot choose another user.
- [ ] Agent can compose email drafts.
- [ ] Agent requires explicit confirmation.
- [ ] Agent does not send before confirmation.
- [ ] Gmail API sends from the correct user's Gmail account.
- [ ] Duplicate sending is prevented.
- [ ] Frontend provides a usable chat interface.
- [ ] Backend exposes secure APIs.
- [ ] Secrets are stored in environment variables/secrets management.
- [ ] Alembic migrations work.
- [ ] Application works locally.
- [ ] Application works on Render.
- [ ] Production OAuth redirect URLs are configured.
- [ ] Database connections work in production.
- [ ] Logging does not expose secrets.
- [ ] User data is isolated.
- [ ] Production session/state persistence is configured.
- [ ] Error handling is implemented.
- [ ] Rate limiting and other production protections are considered.

---

# 43. Primary Objective

The final system should implement this exact principle:

**The user authenticates with the application → the application knows who the user is → Google OAuth connects that user to Gmail → ADK operates on behalf of that authenticated user → ADK tools retrieve that user's OAuth credentials → Gmail API operates only on that user's Gmail account.**

The LLM is responsible for **understanding and reasoning about the user's request**.

FastAPI is responsible for **authentication and authorization**.

PostgreSQL/Supabase is responsible for **persistent application data**.

Google OAuth is responsible for **Gmail authorization**.

Google ADK is responsible for **agent execution, sessions, state, and tools**.

The Gmail service is responsible for **communicating with Gmail**.

The frontend is responsible for **user interaction**.

Render/Vercel are responsible for **hosting**.