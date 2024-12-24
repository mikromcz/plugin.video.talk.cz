import sys
import traceback
from urllib.parse import urlencode
import xbmc
from .constants import _URL, _ADDON, ADDON_ID, MENU_CATEGORIES, CREATOR_CATEGORIES, ARCHIVE_CATEGORIES

def log(msg, level=xbmc.LOGDEBUG):
    # Log message to Kodi log file with proper formatting and debug control.

    if (level in [xbmc.LOGERROR, xbmc.LOGWARNING] or
        (_ADDON.getSetting('debug') == 'true')):

        # Get the caller's frame info
        frame = sys._getframe(1)
        function_name = frame.f_code.co_name

        # Format the message with function context
        formatted_msg = f"{_ADDON.getAddonInfo('id')}: [{function_name}] {msg}"

        # For errors, append the traceback if available
        if level == xbmc.LOGERROR:
            exc_type, exc_value, exc_tb = sys.exc_info()
            if exc_type:
                formatted_msg += f"\nTraceback:\n{''.join(traceback.format_exception(exc_type, exc_value, exc_tb))}"

        xbmc.log(formatted_msg, level)

def get_category_name(url):
    # Extract a meaningful category name from the URL or page content

    # Go through all defined categories
    all_categories = MENU_CATEGORIES + CREATOR_CATEGORIES + ARCHIVE_CATEGORIES
    for category in all_categories:
        if category['url'] in url:
            log(f"category url: {category['url']}, category name: {category['name']}", xbmc.LOGINFO)

            if '/videa' in category['url']:
                return category['name'].capitalize() # POSLEDNÍ VIDEA -> Poslední videa

            return category['name']  # Categories already in uppercase

    # If no category found, return 'Videa' as a fallback
    return 'Videa'

def get_url(**kwargs):
    # Constructs a URL with query parameters from the given keyword arguments

    return '{0}?{1}'.format(_URL, urlencode(kwargs))

def get_image_path(image_name):
    # Convert image name to special Kodi path for addon resources

    return f'special://home/addons/{ADDON_ID}/resources/media/{image_name}'

def clean_text(text):
    # Clean text from null characters and handle encoding

    if text is None:
        return ''
    return text.replace('\x00', '').strip()

def convert_duration_to_seconds(duration_text):
    # Convert duration string (e.g., "1h42m" or "42m") to seconds

    total_seconds = 0
    try:
        if 'h' in duration_text:
            # Format: "1h42m"
            hours, minutes = duration_text.split('h')
            minutes = minutes.strip('m')
            total_seconds = int(hours) * 3600 + int(minutes) * 60
        else:
            # Format: "42m"
            minutes = duration_text.strip('m')
            total_seconds = int(minutes) * 60
    except:
        pass
    return total_seconds

def parse_date(date_str):
    # Parse Czech date string to ISO format

    CZECH_MONTHS = {
        'ledna': '1',
        'února': '2',
        'března': '3',
        'dubna': '4',
        'května': '5',
        'června': '6',
        'července': '7',
        'srpna': '8',
        'září': '9',
        'října': '10',
        'listopadu': '11',
        'prosince': '12'
    }

    if not date_str:
        return ''

    try:
        day, month, year = date_str.split(' ')
        day = day.rstrip('.')  # Remove the dot after the day
        month = CZECH_MONTHS.get(month.lower())
        if not month:
            return ''

        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    except Exception as e:
        log(f"Error parsing date {date_str}: {str(e)}", xbmc.LOGWARNING)
        return ''