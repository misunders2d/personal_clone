from datetime import datetime
import pytz


def get_current_date():
    """
    Returns the current date and time in YYYY-MM-DD HH:MM:SS format
    for Kiev and New York timezones.
    """
    # Define timezones
    kiev_tz = pytz.timezone("Europe/Kiev")
    new_york_tz = pytz.timezone("America/New_York")

    # Get current UTC time
    utc_now = datetime.now(pytz.utc)

    # Convert to Kiev time
    kiev_time = utc_now.astimezone(kiev_tz)

    # Convert to New York time
    new_york_time = utc_now.astimezone(new_york_tz)

    # Format times
    kiev_formatted = kiev_time.strftime("%Y-%m-%d %H:%M:%S %Z%z")
    new_york_formatted = new_york_time.strftime("%Y-%m-%d %H:%M:%S %Z%z")

    return {"kiev_time": kiev_formatted, "new_york_time": new_york_formatted}
