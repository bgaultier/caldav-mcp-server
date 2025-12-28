import os
import caldav
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# We need these to construct proper invitation objects
from icalendar import Calendar, Event, vCalAddress, vText

# Load environment variables
load_dotenv()

mcp = FastMCP("caldav-mcp-server")

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
    """Parses ISO string and attaches local system timezone if missing."""
    try:
        dt = datetime.fromisoformat(dt_str)
        local_tz = datetime.now().astimezone().tzinfo
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
    now = datetime.now().astimezone()
    # We use strftime to strictly define the string format
    # %A = Full weekday name (Monday)
    # %d = Day of month
    # %B = Full month name
    # %Y = Year
    
    # Result example: "Monday, January 05, 2026"
    formatted_date = now.strftime("%A, %B %d, %Y") 
    iso_time = now.isoformat()
    
    # We provide BOTH the human string and the ISO string
    response_text = f"Current Date: {formatted_date}\nISO format: {iso_time}"
    
    return response_text

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
    attendees: list[str] = [],
    description: str = "",
    location: str = ""
) -> str:
    """
    Creates a new calendar event with optional attendees.

    Args:
        calendar_name: The display name of the calendar.
        summary: Title of the event.
        start_time: ISO 8601 24h format (e.g., '2023-12-01T14:30:00').
        end_time: ISO 8601 24h format (e.g., '2023-12-01T15:30:00').
        attendees: A list of email addresses to invite (e.g. ['bob@example.com']).
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

    # 1. Prepare Times
    dt_start = ensure_local_tz(start_time)
    dt_end = ensure_local_tz(end_time)

    # 2. Build the iCalendar Object manually
    # We do this instead of target_cal.save_event(summary=...) because 
    # we need granular control over the Attendee properties for invites to work.
    cal = Calendar()
    cal.add('prodid', '-//MCP CalDAV Assistant//mxm.dk//')
    cal.add('version', '2.0')

    event = Event()
    event.add('summary', summary)
    event.add('dtstart', dt_start)
    event.add('dtend', dt_end)
    event.add('dtstamp', datetime.now().astimezone())
    
    if description:
        event.add('description', description)
    if location:
        event.add('location', location)

    # 3. Add Attendees with RSVP
    for email in attendees:
        # Create a vCal formatted address (mailto:email@ex.com)
        attendee = vCalAddress(f'mailto:{email}')
        
        # Add parameters required for an invitation
        attendee.params['CN'] = vText(email) # Common Name
        attendee.params['ROLE'] = vText('REQ-PARTICIPANT') # Required attendee
        attendee.params['RSVP'] = vText('TRUE') # Request a response
        attendee.params['PARTSTAT'] = vText('NEEDS-ACTION') # Status
        
        # Add to event
        event.add('attendee', attendee, encode=0)

    cal.add_component(event)

    # 4. Save via CalDAV
    # We pass the raw ical string to the library
    target_cal.save_event(ical=cal.to_ical())
    
    attendee_msg = f" with {len(attendees)} guests" if attendees else ""
    return f"Event created: '{summary}'{attendee_msg} on {dt_start.strftime('%Y-%m-%d %H:%M')}"

@mcp.tool()
def get_events(calendar_name: str, start_time: str, end_time: str) -> list[dict]:
    """Get events within a time range."""
    client = get_client()
    principal = client.principal()
    calendars = principal.calendars()
    
    target_cal = next((c for c in calendars if c.name == calendar_name), None)
    if not target_cal:
        raise ValueError(f"Calendar '{calendar_name}' not found.")

    dt_start = ensure_local_tz(start_time)
    dt_end = ensure_local_tz(end_time)

    results = target_cal.date_search(start=dt_start, end=dt_end, expand=True)
    
    events_data = []
    for event in results:
        event.load()
        for component in event.icalendar_component.walk():
            if component.name == "VEVENT":
                def get_str(key, default=''):
                    val = component.get(key)
                    if val is None: return default
                    if hasattr(val, 'dt'): return val.dt.isoformat()
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
