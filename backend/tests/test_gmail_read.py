from app.services.gmail_service import read_emails


class FakeList:
    def __init__(self, query_results):
        self.query_results = query_results
        self.calls = []

    def list(self, **kwargs):
        self.calls.append(kwargs)
        return self

    def execute(self):
        return {"messages": self.query_results}


class FakeGet:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, **kwargs):
        self.calls.append(kwargs)
        return self

    def execute(self):
        return self.payload


class FakeService:
    def __init__(self):
        self.users_calls = []
        self.message_ids = ["msg-1", "msg-2", "msg-3"]
        self.message_payloads = {
            "msg-1": {
                "id": "msg-1",
                "snippet": "First email",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Welcome"},
                        {"name": "From", "value": "alice@example.com"},
                        {"name": "Date", "value": "Mon, 01 Aug 2026 10:00:00 +0000"},
                    ]
                },
            },
            "msg-2": {
                "id": "msg-2",
                "snippet": "Second email",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Follow up"},
                        {"name": "From", "value": "bob@example.com"},
                        {"name": "Date", "value": "Tue, 02 Aug 2026 09:00:00 +0000"},
                    ]
                },
            },
            "msg-3": {
                "id": "msg-3",
                "snippet": "Third email",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Another"},
                        {"name": "From", "value": "alice@example.com"},
                        {"name": "Date", "value": "Wed, 03 Aug 2026 12:00:00 +0000"},
                    ]
                },
            },
        }

    def users(self):
        self.users_calls.append("users")
        return self

    def messages(self):
        return self

    def list(self, **kwargs):
        query = kwargs.get("q", "")
        if "alice@example.com" in query:
            return FakeList([{"id": "msg-1"}, {"id": "msg-3"}])
        return FakeList([{"id": "msg-2"}])

    def get(self, **kwargs):
        return FakeGet(self.message_payloads[kwargs["id"]])


def test_read_emails_returns_filtered_messages_for_dates_and_limit():
    service = FakeService()

    result = read_emails(
        service,
        user_email="alice@example.com",
        of_user="alice@example.com",
        dates=["2026-08-01", "2026-08-03"],
        amount=2,
    )

    assert result["status"] == "success"
    assert result["count"] == 2
    assert [email["id"] for email in result["emails"]] == ["msg-1", "msg-3"]
    assert result["emails"][0]["from"] == "alice@example.com"
