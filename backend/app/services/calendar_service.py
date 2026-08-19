"""Google Calendar service for interacting with the Calendar API."""

from datetime import datetime, timezone
from typing import Tuple

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.services.google_oauth_service import get_google_credentials


def get_calendar_service(db, user_id: int):
    """Build and return a Google Calendar service instance."""
    creds = get_google_credentials(db, user_id)
    return build("calendar", "v3", credentials=creds)


def get_calendar_events(
    db,
    user_id: int,
    time_min: str | None = None,
    time_max: str | None = None,
    max_results: int = 10,
    calendar_id: str = "primary",
) -> Tuple[bool, dict]:
    """Retrieve events from the user's Google Calendar.

    Args:
        db: Database session
        user_id: The user's ID
        time_min: ISO format datetime string for start of range (optional)
        time_max: ISO format datetime string for end of range (optional)
        max_results: Maximum number of events to return (default: 10)
        calendar_id: Calendar ID to query (default: 'primary')

    Returns:
        Tuple of (success, result_dict)
    """
    try:
        service = get_calendar_service(db, user_id)

        # Parse time boundaries
        time_min_dt = None
        time_max_dt = None

        if time_min:
            try:
                time_min_dt = datetime.fromisoformat(time_min.replace("Z", "+00:00"))
            except ValueError:
                return False, {"error": f"Invalid time_min format: {time_min}"}

        if time_max:
            try:
                time_max_dt = datetime.fromisoformat(time_max.replace("Z", "+00:00"))
            except ValueError:
                return False, {"error": f"Invalid time_max format: {time_max}"}

        # Default to today if no time range specified
        if not time_min_dt:
            time_min_dt = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

        if not time_max_dt:
            # Default to 7 days from time_min
            time_max_dt = time_min_dt.replace(
                hour=23, minute=59, second=59
            )  # End of same day

        # Call the Calendar API
        events_result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min_dt.isoformat(),
                timeMax=time_max_dt.isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = events_result.get("items", [])

        formatted_events = []
        for event in events:
            start = event.get("start", {})
            end = event.get("end", {})

            # Handle all-day events vs timed events
            start_time = start.get("dateTime", start.get("date", ""))
            end_time = end.get("dateTime", end.get("date", ""))

            formatted_events.append({
                "id": event.get("id"),
                "summary": event.get("summary", "(No title)"),
                "description": event.get("description", ""),
                "location": event.get("location", ""),
                "start": start_time,
                "end": end_time,
                "status": event.get("status", ""),
                "html_link": event.get("htmlLink", ""),
                "creator": event.get("creator", {}).get("email", ""),
                "organizer": event.get("organizer", {}).get("email", ""),
            })

        return True, {
            "success": True,
            "count": len(formatted_events),
            "calendar_id": calendar_id,
            "time_min": time_min_dt.isoformat(),
            "time_max": time_max_dt.isoformat(),
            "events": formatted_events,
        }

    except HttpError as e:
        return False, {
            "success": False,
            "error": e.content.decode() if hasattr(e, "content") else str(e),
        }
    except Exception as e:
        return False, {"success": False, "error": str(e)}


def get_event_by_date(
    db,
    user_id: int,
    date: str,
    calendar_id: str = "primary",
) -> Tuple[bool, dict]:
    """Retrieve events for a specific date.

    Args:
        db: Database session
        user_id: The user's ID
        date: Date in ISO format (YYYY-MM-DD)
        calendar_id: Calendar ID to query (default: 'primary')

    Returns:
        Tuple of (success, result_dict)
    """
    try:
        # Parse the date and set time boundaries
        target_date = datetime.strptime(date, "%Y-%m-%d")
        time_min = target_date.replace(hour=0, minute=0, second=0, tzinfo=timezone.utc)
        time_max = target_date.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)

        return get_calendar_events(
            db,
            user_id,
            time_min=time_min.isoformat(),
            time_max=time_max.isoformat(),
            max_results=50,
            calendar_id=calendar_id,
        )
    except ValueError as e:
        return False, {"success": False, "error": f"Invalid date format: {date}. Use YYYY-MM-DD."}


def get_upcoming_events(
    db,
    user_id: int,
    days: int = 7,
    max_results: int = 20,
    calendar_id: str = "primary",
) -> Tuple[bool, dict]:
    """Retrieve upcoming events for the next N days.

    Args:
        db: Database session
        user_id: The user's ID
        days: Number of days to look ahead (default: 7)
        max_results: Maximum number of events to return (default: 20)
        calendar_id: Calendar ID to query (default: 'primary')

    Returns:
        Tuple of (success, result_dict)
    """
    from datetime import timedelta

    time_min = datetime.now(timezone.utc)
    time_max = time_min + timedelta(days=days)

    return get_calendar_events(
        db,
        user_id,
        time_min=time_min.isoformat(),
        time_max=time_max.isoformat(),
        max_results=max_results,
        calendar_id=calendar_id,
    )


def list_calendars(db, user_id: int) -> Tuple[bool, dict]:
    """List all calendars the user has access to.

    Args:
        db: Database session
        user_id: The user's ID

    Returns:
        Tuple of (success, result_dict)
    """
    try:
        service = get_calendar_service(db, user_id)

        calendar_list = service.calendarList().list().execute()
        calendars = calendar_list.get("items", [])

        formatted_calendars = []
        for cal in calendars:
            formatted_calendars.append({
                "id": cal.get("id"),
                "summary": cal.get("summary", ""),
                "description": cal.get("description", ""),
                "primary": cal.get("primary", False),
                "access_role": cal.get("accessRole", ""),
                "time_zone": cal.get("timeZone", ""),
            })

        return True, {
            "success": True,
            "count": len(formatted_calendars),
            "calendars": formatted_calendars,
        }

    except HttpError as e:
        return False, {
            "success": False,
            "error": e.content.decode() if hasattr(e, "content") else str(e),
        }
    except Exception as e:
        return False, {"success": False, "error": str(e)}
