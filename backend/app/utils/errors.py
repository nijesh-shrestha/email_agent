"""Custom application errors."""

class InsufficientCalendarScopeError(Exception):
    """Raised when the user's Google OAuth token lacks the required Calendar scope."""

    def __init__(self, message: str = "Google Calendar access requires additional permissions. Please reconnect your Google account."):
        self.message = message
        super().__init__(self.message)