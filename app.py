import os
import caldav
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

mcp = FastMCP("caldav-manager")

def get_client():
    """Helper to establish connection to the CalDAV server."""
    url = os.getenv("CALDAV_URL")
    username = os.getenv("CALDAV_USERNAME")
    password = os.getenv("CALDAV_PASSWORD")

    if not all([url, username, password]):
        raise ValueError("Missing CALDAV credentials in environment variables.")

    return caldav.DAVClient(
        url=url,
        username=username,
        password=password
    )

def ensure_local_tz(dt_str: str) -> datetime:
    """
    Parses an ISO string. If it lacks timezone info, attaches 
    the system's local timezone.
    """
    try:
        dt = datetime.fromisoformat(dt_str)
        # Get system local timezone
        local_tz = datetime.now().astimezone().tzinfo
        
        # If the datetime object is "naive" (no timezone), set it to local
        if dt.tzinfo is None:
            return dt.replace(tzinfo=local_tz)
        return dt
    except ValueError:
        raise ValueError(f"Date format must be ISO 8601 (YYYY-MM-DDTHH:MM:SS). Received: {dt_str}")

@mcp.tool()
def get_current_time() -> dict:
    """
    Get the current local system time.
    Use this to calculate relative dates.
    """
    # astimezone() ensures we get the system's local config
    now = datetime.now().astimezone()
    return {
        "iso_format": now.isoformat(),
        "day_of_week": now.strftime("%A"),
        "timezone_name": str(now.tzinfo),
        "hour_24_format": now.strftime("%H:%M")
    }

@mcp.tool()
def list_calendars() -> list[dict]:
    """Lists all available calendars."""
    client = get_client()
    principal = client.principal()
    calendars = principal.calendars()
    
    return [
        {
            "name": cal.name or "Unknown",
            "url": str(cal.url),
            "id": str(cal.id)
        }
        for cal in calendars
    ]

@mcp.tool()
def create_event(
    calendar_name: str,
    summary: str,
    start_time: str,
    end_time: str,
    description: str = "",
    location: str = ""
) -> str:
    """
    Creates a new calendar event using the LOCAL system timezone.

    Args:
        calendar_name: The display name of the calendar.
        summary: Title of the event.
        start_time: ISO 8601 format in 24h time (e.g., '2023-12-01T14:30:00'). 
                    Do NOT use AM/PM. 
        end_time: ISO 8601 format in 24h time (e.g., '2023-12-01T15:30:00').
        description: Details about the event.
        location: Physical location or URL.
    """
    client = get_client()
    principal = client.principal()
    calendars = principal.calendars()
    
    target_cal = next((c for c in calendars if c.name == calendar_name), None)
    
    if not target_cal:
        available = ", ".join([c.name or "Unknown" for c in calendars])
        raise ValueError(f"Calendar '{calendar_name}' not found. Available: {available}")

    # Process times to ensure they are 24h localized datetime objects
    dt_start = ensure_local_tz(start_time)
    dt_end = ensure_local_tz(end_time)

    # Save event
    event = target_cal.save_event(
        dtstart=dt_start,
        dtend=dt_end,
        summary=summary,
        description=description,
        location=location
    )
    
    return f"Event created successfully: {summary} at {dt_start.strftime('%Y-%m-%d %H:%M')} (Local Time)"

@mcp.tool()
def get_events(
    calendar_name: str,
    start_time: str,
    end_time: str
) -> list[dict]:
    """
    Get events within a time range.
    Args:
        start_time: ISO 8601 string (start of search range).
        end_time: ISO 8601 string (end of search range).
    """
    client = get_client()
    principal = client.principal()
    calendars = principal.calendars()
    
    target_cal = next((c for c in calendars if c.name == calendar_name), None)
    if not target_cal:
        raise ValueError(f"Calendar '{calendar_name}' not found.")

    # Convert strings to localized datetimes for searching
    dt_start = ensure_local_tz(start_time)
    dt_end = ensure_local_tz(end_time)

    results = target_cal.date_search(
        start=dt_start,
        end=dt_end,
        expand=True
    )
    
    events_data = []
    
    for event in results:
        event.load()
        for component in event.icalendar_component.walk():
            if component.name == "VEVENT":
                def get_str(key, default=''):
                    val = component.get(key)
                    if val is None: return default
                    # If it's a date object, format it closely to our input style
                    if hasattr(val, 'dt'): 
                        return val.dt.isoformat()
                    return str(val)

                events_data.append({
                    "summary": get_str('summary', 'No Title'),
                    "start": get_str('dtstart'),
                    "end": get_str('dtend'),
                    "description": get_str('description'),
                    "location": get_str('location'),
                })

    return events_data

if __name__ == "__main__":
    mcp.run()
