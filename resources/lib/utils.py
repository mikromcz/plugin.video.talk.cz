import sys
import traceback
from urllib.parse import urlencode
import xbmc
import xbmcgui
from .constants import _URL, _ADDON, ADDON_ID, MENU_CATEGORIES, CREATOR_CATEGORIES, ARCHIVE_CATEGORIES

def log(msg, level=xbmc.LOGDEBUG):
    """
    Log message to Kodi log file with proper formatting and debug control.

    Args:
        msg (str): Message to log
        level (int): Log level (default: xbmc.LOGDEBUG)

    Example:
        log('This is a debug message', xbmc.LOGDEBUG)
        log('This is an error message', xbmc.LOGERROR)
    """

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
    """
    Extract a meaningful category name from the URL or page content

    Args:
        url (str): URL to clean

    Returns:
        str: Category name or 'Videa' if not found

    Example:
        get_category_name('https://www.talktv.cz/posledni-videa?page=2') -> 'POSLEDNÍ VIDEA'
        get_category_name('https://www.talktv.cz/standashow') -> 'STANDASHOW'
    """

    # Go through all defined categories
    all_categories = MENU_CATEGORIES + CREATOR_CATEGORIES + ARCHIVE_CATEGORIES
    for category in all_categories:
        if category['url'] in url:
            log(f"category url: {category['url']}, category name: {category['name']}", xbmc.LOGINFO)
            return category['name']

    # If no category found, return 'Videa' as a fallback
    return 'Videa'

def get_url(**kwargs):
    """
    Constructs a URL with query parameters from the given keyword arguments

    Args:
        **kwargs: Query parameters as keyword arguments

    Returns:
        str: Constructed URL

    Example:
        get_url(category='posledni-videa', page=2) -> 'https://www.talktv.cz/posledni-videa?page=2'
    """

    return '{0}?{1}'.format(_URL, urlencode(kwargs))

def clean_url(url):
    """
    Clean URL by removing unnecessary query parameters
    Links from JSON API contain unnecessary query parameters that mess up the watched status in Kodi

    Args:
        url (str): URL to clean

    Returns:
        str: Cleaned URL

    Example:
        clean_url('https://www.talktv.cz/video/byvala-letuska-marika-mikusova-indove-na-palube-nejhorsi-zazitky-z-letadla-sex-s-piloty-obezita-v-letadle-instagram-keGzpmtA?tc=r-4f5d6302f489bb45edc0e7d6eb4e5ad1')
        -> 'https://www.talktv.cz/video/byvala-letuska-marika-mikusova-indove-na-palube-nejhorsi-zazitky-z-letadla-sex-s-piloty-obezita-v-letadle-instagram-keGzpmtA'
    """

    if '?' in url:
        base_url = url.split('?')[0]
        return base_url
    return url

def get_image_path(image_name):
    """
    Convert image name to special Kodi path for addon resources

    Args:
        image_name (str): Image name to convert

    Returns:
        str: Special path for the image
    """

    return f'special://home/addons/{ADDON_ID}/resources/media/{image_name}'

def clean_text(text):
    """
    Clean text from null characters and handle encoding

    Args:
        text (str): Text to clean

    Returns:
        str: Cleaned text or empty string if None

    Example:
        clean_text('Hello\x00') -> 'Hello'
    """

    if text is None:
        return ''
    return text.replace('\x00', '').strip()

def convert_duration_to_seconds(duration_text):
    """
    Convert duration string (e.g., "1h42m" or "42m") to seconds

    Args:
        duration_text (str): Duration string like "1h42m" or "42m"

    Returns:
        int: Duration in seconds or 0 if parsing failed

    Example:
        convert_duration_to_seconds("1h42m") -> 6120
        convert_duration_to_seconds("42m") -> 2520
    """

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
    """
    Parse Czech date string to ISO format

    Args:
        date_str (str): Date string in Czech format like "1. ledna 2021"

    Returns:
        str: Date in ISO format like "2021-01-01" or empty string if parsing failed

    Example:
        parse_date("1. ledna 2021") -> "2021-01-01"
    """

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

def get_creator_name_from_coloring(coloring_class):
    """
    Get creator name based on the coloring class from HTML.

    Args:
        coloring_class (str): HTML class like 'coloring-1', 'coloring-2', etc.

    Returns:
        str: Creator name or empty string if not found

    Example:
        get_creator_name_from_coloring('coloring-1') -> 'STANDASHOW'
    """
    if not coloring_class or not isinstance(coloring_class, str):
        return ''

    # Extract number from coloring-X
    try:
        coloring_number = coloring_class.split('-')[1]
        for creator in CREATOR_CATEGORIES:
            if creator['coloring'] == coloring_number:
                return creator['name']
    except (IndexError, KeyError):
        pass

    return ''

def get_creator_cast(creator_name):
    """
    Get cast list as xbmc.Actor objects for a given creator name
    """

    cast_list = []

    if not creator_name:
        return cast_list

    for creator in CREATOR_CATEGORIES:
        if creator['name'] == creator_name:
            # Create proper Actor objects
            for i, actor_name in enumerate(creator.get('cast', [])):
                try:
                    # Create Actor object with required name
                    actor = xbmc.Actor(actor_name, 'Moderátor', i, '')
                    cast_list.append(actor)
                except Exception as e:
                    log(f"Error creating actor {actor_name}: {str(e)}", xbmc.LOGERROR)
            break

    return cast_list

def get_creator_url(creator_name):
    """
    Get the creator's URL from CREATOR_CATEGORIES based on creator name

    Args:
        creator_name (str): Name of the creator

    Returns:
        str: URL of the creator's page or None if not found
    """
    if not creator_name:
        return None

    for creator in CREATOR_CATEGORIES:
        if creator['name'] == creator_name:
            return creator['url']
    return None

def get_ip():
    """
    Show dialog with IP addresses and config page URL.
    This is useful for users who want to access the config page on a different
    device than the one running Kodi.
    """

    try:
        import xbmcgui
        import socket
        port = _ADDON.getSettingInt('config_port')

        # Get all IP addresses
        hostname = socket.gethostname()
        ips = []

        # Try IPv4
        try:
            ip = socket.gethostbyname(hostname)
            ips.append(ip)
        except:
            pass

        # Try getting all addresses including IPv6
        try:
            for info in socket.getaddrinfo(hostname, None):
                ip = info[4][0]
                if ip not in ips:
                    ips.append(ip)
        except:
            pass

        # Fallback to getting local IP
        if not ips:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('8.8.8.8', 80))
                ip = s.getsockname()[0]
                ips.append(ip)
            except:
                pass
            finally:
                s.close()

        if ips:
            message = 'Konfigurační stránka je dostupná na adresách:\n\n'
            for ip in ips:
                message += f'http://{ip}:{port}/talk\n'
        else:
            message = 'Nepodařilo se zjistit IP adresu'

        xbmcgui.Dialog().ok('IP Adresy', message)

    except Exception as e:
        log(f"Error getting IP: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Chyba', 'Nepodařilo se zjistit IP adresu')
