import os
import json
import threading
import time
import xbmc
import xbmcgui
from bs4 import BeautifulSoup
from .constants import _ADDON
from .utils import find_player_value, log, parse_video_description

# Guards the cache file against concurrent read-modify-write from parallel
# video-detail fetches (see menu.add_video_directory_items)
_cache_lock = threading.Lock()

# Cached entries are good for 7 days
_CACHE_TTL = 604800

# In-memory copy of the cache file for lookups within this invocation, so a
# listing reads the file once instead of once per video. Writes still go
# through a fresh read of the file, since another Kodi invocation may have
# written to it in the meantime.
_cache_snapshot = None

def get_cache_path():
    """
    Get the path to the cache file.

    Returns:
        str: The full path to the cache file
    """

    import xbmcvfs
    profile_path = xbmcvfs.translatePath(_ADDON.getAddonInfo('profile'))

    os.makedirs(profile_path, exist_ok=True)

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

    global _cache_snapshot

    cache_path = get_cache_path()
    _cache_snapshot = None
    if os.path.exists(cache_path):
        try:
            os.remove(cache_path)
            log("Cache cleared successfully", xbmc.LOGINFO)
        except OSError as e:
            log(f"Error clearing cache: {str(e)}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification('Chyba', 'Chyba při mazání mezipaměti', time=5000)
            return False
    else:
        log("Cache already empty", xbmc.LOGINFO)

    # Confirm either way - an already empty cache is still a successful clear,
    # and a button press with no feedback reads as broken
    xbmcgui.Dialog().notification('Cache', 'Mezipaměť byla vymazána')
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

    global _cache_snapshot

    # Check if caching is enabled in settings
    use_cache = _ADDON.getSettingBool('use_cache')

    if use_cache and not need_resume:
        with _cache_lock:
            if _cache_snapshot is None:
                _cache_snapshot = load_cache()
            cached_data = _cache_snapshot.get(video_url)

        if cached_data and time.time() - cached_data.get('timestamp', 0) < _CACHE_TTL:
            return cached_data.get('description', ''), cached_data.get('date', ''), 0.0

    try:
        log(f"Fetching details for video: {video_url}", xbmc.LOGDEBUG)
        video_response = session.get(video_url, timeout=10)
        video_soup = BeautifulSoup(video_response.text, 'html.parser')

        date, description = parse_video_description(video_soup)

        resume_position = 0.0
        if need_resume:
            web_position = find_player_value(video_soup, 'ssVideoPos')
            if web_position:
                resume_position = float(web_position)

        # Save to cache if enabled
        if use_cache and (description or date):
            now = time.time()
            with _cache_lock:
                cache = load_cache()

                # Drop expired entries while we are rewriting the file anyway,
                # otherwise it grows for every video ever listed
                cutoff = now - _CACHE_TTL
                cache = {url: entry for url, entry in cache.items()
                         if entry.get('timestamp', 0) >= cutoff}

                cache[video_url] = {
                    'description': description,
                    'date': date,
                    'timestamp': now
                }
                save_cache(cache)
                _cache_snapshot = cache

        return description, date, resume_position

    except Exception as e:
        log(f"Error fetching video details: {str(e)}", xbmc.LOGERROR)
        return '', '', 0.0