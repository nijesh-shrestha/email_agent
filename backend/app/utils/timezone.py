from datetime import datetime, timezone
from zoneinfo import ZoneInfo

NPT = ZoneInfo("Asia/Kathmandu")
UTC = timezone.utc


def now_npt() -> datetime:
    return datetime.now(NPT)


def parse_datetime_to_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=NPT)
    return parsed.astimezone(UTC)
