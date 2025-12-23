import os
import caldav
from datetime import datetime
import time
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

@mcp.tool()
def get_current_time() -> dict:
    """
    Get the current local system time, timezone, and day of the week.
    Use this tool immediately if the user asks for relative dates like 
    'tomorrow', 'next week', or 'this afternoon' so you can calculate 
    the correct ISO dates.
    """
    now = datetime.now().astimezone()
    return {
        "iso_format": now.isoformat(),
        "day_of_week": now.strftime("%A"),
        "timezone": str(now.tzinfo),
        "readable": now.strftime("%Y-%m-%d %H:%M:%S")
    }

@mcp.tool()
def list_calendars() -> list[dict]:
    """
    Lists all available calendars on the WebDAV/CalDAV server.
    Returns the calendar name and its URL.
    """
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
    Creates a new calendar event.
    
    Args:
        calendar_name: The display name of the calendar (e.g. "Personal").
        summary: The title of the event.
        start_time: ISO 8601 format (YYYY-MM-DDTHH:MM:SS).
        end_time: ISO 8601 format (YYYY-MM-DDTHH:MM:SS).
        description: Optional details.
        location: Optional location.
    
    Returns:
        The URL of the created event.
    """
    client = get_client()
    principal = client.principal()
    calendars = principal.calendars()
    
    target_cal = next((c for c in calendars if c.name == calendar_name), None)
    
    if not target_cal:
        available = ", ".join([c.name or "Unknown" for c in calendars])
        raise ValueError(f"Calendar '{calendar_name}' not found. Available: {available}")

    # Create the event
    event = target_cal.save_event(
        dtstart=datetime.fromisoformat(start_time),
        dtend=datetime.fromisoformat(end_time),
        summary=summary,
        description=description,
        location=location
    )
    
    return str(event.url)

@mcp.tool()
def get_events(
    calendar_name: str,
    start_time: str,
    end_time: str
) -> list[dict]:
    """
    Get events from a specific calendar within a time range.
    
    Args:
        calendar_name: The name of the calendar.
        start_time: ISO 8601 string (start of search range).
        end_time: ISO 8601 string (end of search range).
    """
    client = get_client()
    principal = client.principal()
    calendars = principal.calendars()
    
    target_cal = next((c for c in calendars if c.name == calendar_name), None)
    
    if not target_cal:
        available = ", ".join([c.name or "Unknown" for c in calendars])
        raise ValueError(f"Calendar '{calendar_name}' not found. Available: {available}")

    # Search for events
    results = target_cal.date_search(
        start=datetime.fromisoformat(start_time),
        end=datetime.fromisoformat(end_time),
        expand=True 
    )
    
    events_data = []
    
    for event in results:
        event.load()
        for component in event.icalendar_component.walk():
            if component.name == "VEVENT":
                # Helper to safely serialize datetime objects
                def get_str(key, default=''):
                    val = component.get(key)
                    if val is None: return default
                    # If it's a proprietary object (like vText), cast to str
                    if hasattr(val, 'dt'): return str(val.dt)
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
