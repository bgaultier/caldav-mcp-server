import os
import caldav
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables if present
load_dotenv()

# Initialize the MCP server
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

def parse_iso_date(date_str: str) -> datetime:
    """Parses an ISO 8601 string to a datetime object."""
    try:
        # handle 'Z' for UTC
        if date_str.endswith('Z'):
            date_str = date_str[:-1]
        return datetime.fromisoformat(date_str)
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Please use ISO 8601 (YYYY-MM-DDTHH:MM:SS)")

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
        calendar_name: The display name of the calendar to add to (e.g., "Personal").
        summary: The title of the event.
        start_time: ISO 8601 format (YYYY-MM-DDTHH:MM:SS).
        end_time: ISO 8601 format (YYYY-MM-DDTHH:MM:SS).
        description: Optional details.
        location: Optional location.
    
    Returns:
        Confirmation string with the new event URL.
    """
    client = get_client()
    principal = client.principal()
    
    # transform iso strings to datetime objects
    dt_start = parse_iso_date(start_time)
    dt_end = parse_iso_date(end_time)

    # Find the correct calendar
    calendars = principal.calendars()
    target_cal = next((c for c in calendars if c.name == calendar_name), None)

    if not target_cal:
        return f"Error: Calendar named '{calendar_name}' not found. Available: {[c.name for c in calendars]}"

    # Create the event
    event = target_cal.save_event(
        dtstart=dt_start,
        dtend=dt_end,
        summary=summary,
        description=description,
        location=location
    )

    return f"Successfully created event '{summary}' in '{calendar_name}' (ID: {event.id})"

@mcp.tool()
def get_events(
    calendar_name: str,
    start_range: str,
    end_range: str
) -> list[dict]:
    """
    Get events from a specific calendar within a date range.
    
    Args:
        calendar_name: The name of the calendar to search.
        start_range: ISO 8601 format start of search window.
        end_range: ISO 8601 format end of search window.
    """
    client = get_client()
    principal = client.principal()
    
    dt_start = parse_iso_date(start_range)
    dt_end = parse_iso_date(end_range)

    calendars = principal.calendars()
    target_cal = next((c for c in calendars if c.name == calendar_name), None)

    if not target_cal:
        raise ValueError(f"Calendar '{calendar_name}' not found.")

    # Fetch events
    results = target_cal.date_search(start=dt_start, end=dt_end)
    
    events_data = []
    
    for event in results:
        # Load the vObject data
        event.load()
        # Parse the ical component (VEVENT)
        for component in event.icalendar_component.walk():
            if component.name == "VEVENT":
                events_data.append({
                    "summary": str(component.get('summary', 'No Title')),
                    "start": str(component.get('dtstart').dt),
                    "end": str(component.get('dtend').dt),
                    "description": str(component.get('description', '')),
                    "location": str(component.get('location', '')),
                    "uid": str(component.get('uid', ''))
                })

    return events_data

if __name__ == "__main__":
    mcp.run()
