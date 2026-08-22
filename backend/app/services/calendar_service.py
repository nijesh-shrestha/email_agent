"""Google Calendar service for interacting with the Calendar API."""

import json
from datetime import datetime, timezone
from typing import Tuple

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.services.google_oauth_service import get_google_credentials
from app.utils.timezone import NPT, parse_datetime_to_utc


def _is_insufficient_scope_error(e: HttpError) -> bool:
    """Check if an HttpError is due to insufficient OAuth scopes."""
    try:
        if e.resp.status == 403:
            content = e.content.decode() if hasattr(e, "content") else str(e)
            error_data = json.loads(content)
            errors = error_data.get("error", {}).get("errors", [])
            for err in errors:
                if err.get("reason") == "insufficientPermissions":
                    return True
    except Exception:
        pass
    return False


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
                time_min_dt = parse_datetime_to_utc(time_min)
            except ValueError:
                return False, {"error": f"Invalid time_min format: {time_min}"}

        if time_max:
            try:
                time_max_dt = parse_datetime_to_utc(time_max)
            except ValueError:
                return False, {"error": f"Invalid time_max format: {time_max}"}

        # Default to today if no time range specified
        if not time_min_dt:
            now_npt = datetime.now(NPT)
            time_min_dt = now_npt.replace(
                hour=0, minute=0, second=0, microsecond=0
            ).astimezone(timezone.utc)

        if not time_max_dt:
            # Default to 7 days from time_min
            time_max_dt = time_min_dt.replace(hour=23, minute=59, second=59)

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
        if _is_insufficient_scope_error(e):
            return False, {
                "success": False,
                "error": "insufficient_calendar_scope",
                "message": "Google Calendar access requires additional permissions. Please reconnect your Google account to grant Calendar access.",
            }
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
        target_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=NPT)
        time_min = target_date.replace(hour=0, minute=0, second=0).astimezone(timezone.utc)
        time_max = target_date.replace(hour=23, minute=59, second=59).astimezone(timezone.utc)

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

    time_min = datetime.now(NPT)
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
        if _is_insufficient_scope_error(e):
            return False, {
                "success": False,
                "error": "insufficient_calendar_scope",
                "message": "Google Calendar access requires additional permissions. Please reconnect your Google account to grant Calendar access.",
            }
        return False, {
            "success": False,
            "error": e.content.decode() if hasattr(e, "content") else str(e),
        }
    except Exception as e:
        return False, {"success": False, "error": str(e)}


def create_calendar_event(
    db,
    user_id: int,
    summary: str,
    start_datetime: str,
    end_datetime: str,
    description: str = "",
    location: str = "",
    calendar_id: str = "primary",
    attendees: list[str] | None = None,
) -> Tuple[bool, dict]:
    """Create a new calendar event.

    Args:
        db: Database session
        user_id: The user's ID
        summary: Event title/summary
        start_datetime: ISO format datetime string for event start
        end_datetime: ISO format datetime string for event end
        description: Event description (optional)
        location: Event location (optional)
        calendar_id: Calendar ID to create event in (default: 'primary')
        attendees: List of attendee email addresses (optional)

    Returns:
        Tuple of (success, result_dict)
    """
    try:
        service = get_calendar_service(db, user_id)

        # Parse datetime strings
        start_dt = parse_datetime_to_utc(start_datetime)
        end_dt = parse_datetime_to_utc(end_datetime)

        # Validate that end is after start
        if end_dt <= start_dt:
            return False, {"success": False, "error": "End time must be after start time"}

        # Build event object
        event = {
            "summary": summary,
            "description": description,
            "location": location,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "UTC",
            },
        }

        if attendees:
            event["attendees"] = [{"email": email} for email in attendees]

        # Create the event
        created_event = (
            service.events()
            .insert(calendarId=calendar_id, body=event, sendUpdates="all" if attendees else "none")
            .execute()
        )

        return True, {
            "success": True,
            "event": {
                "id": created_event.get("id"),
                "summary": created_event.get("summary"),
                "description": created_event.get("description", ""),
                "location": created_event.get("location", ""),
                "start": created_event.get("start", {}).get("dateTime", ""),
                "end": created_event.get("end", {}).get("dateTime", ""),
                "html_link": created_event.get("htmlLink", ""),
                "status": created_event.get("status", ""),
            },
            "message": f"Event '{summary}' created successfully",
        }

    except HttpError as e:
        if _is_insufficient_scope_error(e):
            return False, {
                "success": False,
                "error": "insufficient_calendar_scope",
                "message": "Google Calendar access requires additional permissions. Please reconnect your Google account to grant Calendar access.",
            }
        return False, {
            "success": False,
            "error": e.content.decode() if hasattr(e, "content") else str(e),
        }
    except Exception as e:
        return False, {"success": False, "error": str(e)}


def get_tasks_service(db, user_id: int):
    """Build and return a Google Tasks service instance."""
    creds = get_google_credentials(db, user_id)
    return build("tasks", "v1", credentials=creds)


def create_task(
    db,
    user_id: int,
    title: str,
    notes: str = "",
    due_datetime: str | None = None,
    task_list_id: str = "@default",
) -> Tuple[bool, dict]:
    """Create a new Google Task.

    Args:
        db: Database session
        user_id: The user's ID
        title: Task title
        notes: Task notes/description (optional)
        due_datetime: ISO format datetime string for due date (optional)
        task_list_id: Task list ID (default: '@default' for default list)

    Returns:
        Tuple of (success, result_dict)
    """
    try:
        service = get_tasks_service(db, user_id)

        task = {
            "title": title,
            "notes": notes,
        }

        if due_datetime:
            due_dt = parse_datetime_to_utc(due_datetime)
            task["due"] = due_dt.isoformat()

        created_task = (
            service.tasks()
            .insert(tasklist=task_list_id, body=task)
            .execute()
        )

        return True, {
            "success": True,
            "task": {
                "id": created_task.get("id"),
                "title": created_task.get("title"),
                "notes": created_task.get("notes", ""),
                "due": created_task.get("due", ""),
                "status": created_task.get("status", ""),
                "updated": created_task.get("updated", ""),
            },
            "message": f"Task '{title}' created successfully",
        }

    except HttpError as e:
        if _is_insufficient_scope_error(e):
            return False, {
                "success": False,
                "error": "insufficient_tasks_scope",
                "message": "Google Tasks access requires additional permissions. Please reconnect your Google account to grant Tasks access.",
            }
        return False, {
            "success": False,
            "error": e.content.decode() if hasattr(e, "content") else str(e),
        }
    except Exception as e:
        return False, {"success": False, "error": str(e)}


def list_task_lists(db, user_id: int) -> Tuple[bool, dict]:
    """List all task lists the user has access to.

    Args:
        db: Database session
        user_id: The user's ID

    Returns:
        Tuple of (success, result_dict)
    """
    try:
        service = get_tasks_service(db, user_id)

        task_lists_result = service.tasklists().list().execute()
        task_lists = task_lists_result.get("items", [])

        formatted_lists = []
        for tl in task_lists:
            formatted_lists.append({
                "id": tl.get("id"),
                "title": tl.get("title", ""),
                "updated": tl.get("updated", ""),
            })

        return True, {
            "success": True,
            "count": len(formatted_lists),
            "task_lists": formatted_lists,
        }

    except HttpError as e:
        if _is_insufficient_scope_error(e):
            return False, {
                "success": False,
                "error": "insufficient_tasks_scope",
                "message": "Google Tasks access requires additional permissions. Please reconnect your Google account to grant Tasks access.",
            }
        return False, {
            "success": False,
            "error": e.content.decode() if hasattr(e, "content") else str(e),
        }
    except Exception as e:
        return False, {"success": False, "error": str(e)}


def get_tasks(
    db,
    user_id: int,
    task_list_id: str = "@default",
    max_results: int = 20,
    show_completed: bool = False,
) -> Tuple[bool, dict]:
    """Retrieve tasks from a task list.

    Args:
        db: Database session
        user_id: The user's ID
        task_list_id: Task list ID (default: '@default')
        max_results: Maximum number of tasks to return (default: 20)
        show_completed: Whether to show completed tasks (default: False)

    Returns:
        Tuple of (success, result_dict)
    """
    try:
        service = get_tasks_service(db, user_id)

        tasks_result = (
            service.tasks()
            .list(tasklist=task_list_id, maxResults=max_results, showCompleted=show_completed)
            .execute()
        )
        tasks = tasks_result.get("items", [])

        formatted_tasks = []
        for task in tasks:
            formatted_tasks.append({
                "id": task.get("id"),
                "title": task.get("title", ""),
                "notes": task.get("notes", ""),
                "due": task.get("due", ""),
                "status": task.get("status", ""),
                "updated": task.get("updated", ""),
            })

        return True, {
            "success": True,
            "count": len(formatted_tasks),
            "task_list_id": task_list_id,
            "tasks": formatted_tasks,
        }

    except HttpError as e:
        if _is_insufficient_scope_error(e):
            return False, {
                "success": False,
                "error": "insufficient_tasks_scope",
                "message": "Google Tasks access requires additional permissions. Please reconnect your Google account to grant Tasks access.",
            }
        return False, {
            "success": False,
            "error": e.content.decode() if hasattr(e, "content") else str(e),
        }
    except Exception as e:
        return False, {"success": False, "error": str(e)}
