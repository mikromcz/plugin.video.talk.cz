import os
import json
import re
import threading
import time
import xbmc
import xbmcgui
from bs4 import BeautifulSoup
from .constants import _ADDON
from .utils import log

# Guards the cache file against concurrent read-modify-write from parallel
# video-detail fetches (see menu.add_video_directory_items)
_cache_lock = threading.Lock()

def get_cache_path():
    """
    Get the path to the cache file.

    Returns:
        str: The full path to the cache file
    """

    import xbmcvfs
    profile_path = xbmcvfs.translatePath(_ADDON.getAddonInfo('profile'))

    if not os.path.exists(profile_path):
        os.makedirs(profile_path)

    return os.path.join(profile_path, 'video_cache.json')

def load_cache():
    """
    Load the cache from file.

    Returns:
        dict: The cache data
    """

    cache_path = get_cache_path()
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log(f"Error loading cache: {str(e)}", xbmc.LOGWARNING)

    return {}

def save_cache(cache_data):
    """
    Save the cache to file.

    Args:
        cache_data (dict): The cache data to save
    """

    cache_path = get_cache_path()
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"Error saving cache: {str(e)}", xbmc.LOGWARNING)

def clear_cache():
    """
    Clear the video description cache.
    """

    cache_path = get_cache_path()
    if os.path.exists(cache_path):
        try:
            os.remove(cache_path)
            xbmcgui.Dialog().notification('Cache', 'Mezipaměť byla vymazána')
            log("Cache cleared successfully", xbmc.LOGINFO)
            return True
        except Exception as e:
            log(f"Error clearing cache: {str(e)}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification('Chyba', 'Chyba při mazání mezipaměti', time=5000)
            return False

    return True

def get_video_details(session, video_url, need_resume=False):
    """
    Get video details with caching support.

    Args:
        session (requests.Session): The session to use for the request
        video_url (str): The URL of the video
        need_resume (bool): If True, always fetch the page live (bypassing the
            cache) and also extract the web resume position from it. Resume
            position changes constantly, so it is never read from or written
            to the cache; requesting it just means the description/date are
            re-fetched on the same trip instead of a separate one.

    Returns:
        tuple: (description, date, resume_position). resume_position is 0.0
        when not requested or not found.
    """

    # Check if caching is enabled in settings
    use_cache = _ADDON.getSettingBool('use_cache')

    if use_cache and not need_resume:
        with _cache_lock:
            cache = load_cache()
            cached_data = cache.get(video_url)

        # Cache data for 7 days (604800 seconds)
        if cached_data and time.time() - cached_data.get('timestamp', 0) < 604800:
            return cached_data.get('description', ''), cached_data.get('date', ''), 0.0

    try:
        log(f"Fetching details for video: {video_url}", xbmc.LOGDEBUG)
        video_response = session.get(video_url, timeout=10)
        video_soup = BeautifulSoup(video_response.text, 'html.parser')

        # Get the main details info
        details_element = video_soup.find('div', class_='details__info')
        description = ''
        date = ''

        if details_element:
            main_content = details_element.text.strip()
            parts = main_content.split('                -', 1)

            if len(parts) == 2:
                date = parts[0].strip()
                description = parts[1].strip()
            else:
                description = main_content

        # Get additional description if available
        description_element = video_soup.find('div', class_='details__description-text')
        if description_element:
            additional_description = description_element.text.strip()
            if additional_description:

                # Only add newline if we have both descriptions
                if description:
                    description += '\n' + additional_description
                else:
                    description = additional_description

        resume_position = 0.0
        if need_resume:
            for script in video_soup.find_all('script'):
                if script.string and 'initPlayerComponent' in script.string:
                    pos_match = re.search(r'"ssVideoPos":(\d+)', script.string)
                    if pos_match:
                        resume_position = float(pos_match.group(1))
                    break

        # Save to cache if enabled
        if use_cache and (description or date):
            with _cache_lock:
                cache = load_cache()
                cache[video_url] = {
                    'description': description,
                    'date': date,
                    'timestamp': time.time()
                }
                save_cache(cache)

        return description, date, resume_position

    except Exception as e:
        log(f"Error fetching video details: {str(e)}", xbmc.LOGERROR)
        return '', '', 0.0