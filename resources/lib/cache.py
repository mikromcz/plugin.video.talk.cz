import os
import json
import time
import xbmc
import xbmcgui
#import xbmcvfs
from bs4 import BeautifulSoup
from .constants import _ADDON
from .utils import log

def get_cache_path():
    # Get the path to the cache file.
    try:
        # For Kodi 19+ use xbmcvfs.translatePath
        import xbmcvfs
        profile_path = xbmcvfs.translatePath(_ADDON.getAddonInfo('profile'))
    except ImportError:
        # Fallback for older Kodi versions
        profile_path = xbmc.translatePath(_ADDON.getAddonInfo('profile'))

    if not os.path.exists(profile_path):
        os.makedirs(profile_path)
    return os.path.join(profile_path, 'video_cache.json')

def load_cache():
    # Load the cache from file.
    cache_path = get_cache_path()
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log(f"Error loading cache: {str(e)}", xbmc.LOGWARNING)
    return {}

def save_cache(cache_data):
    # Save the cache to file.
    cache_path = get_cache_path()
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"Error saving cache: {str(e)}", xbmc.LOGWARNING)

def clear_cache():
    # Clear the video description cache.
    cache_path = get_cache_path()
    if os.path.exists(cache_path):
        try:
            os.remove(cache_path)
            xbmcgui.Dialog().notification('Cache', 'Mezipaměť byla vymazána')
            log("Cache cleared successfully", xbmc.LOGINFO)
            return True
        except Exception as e:
            log(f"Error clearing cache: {str(e)}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification('Cache', 'Chyba při mazání mezipaměti')
            return False
    return True

def get_video_details(session, video_url):
    # Get video details with caching support.
    # Check if caching is enabled in settings
    use_cache = _ADDON.getSettingBool('use_cache')

    if use_cache:
        # Load cache
        cache = load_cache()

        # Check if we have cached data
        if video_url in cache:
            cached_data = cache[video_url]
            # Cache data for 7 days (604800 seconds)
            if time.time() - cached_data.get('timestamp', 0) < 604800:
                return cached_data.get('description', ''), cached_data.get('date', '')

    try:
        log(f"Fetching details for video: {video_url}", xbmc.LOGDEBUG)
        video_response = session.get(video_url)
        video_soup = BeautifulSoup(video_response.text, 'html.parser')
        details_element = video_soup.find('div', class_='details__info')

        if details_element:
            description = details_element.text.strip()
            parts = description.split('                -', 1)
            if len(parts) == 2:
                date = parts[0].strip()
                content = parts[1].strip()
                description = content
            else:
                date = ''
                content = description

            # Save to cache if enabled
            if use_cache:
                cache = load_cache()
                cache[video_url] = {
                    'description': description,
                    'date': date,
                    'timestamp': time.time()
                }
                save_cache(cache)

            return description, date
        else:
            log(f"No details found for video: {video_url}", xbmc.LOGWARNING)
            return '', ''

    except Exception as e:
        log(f"Error fetching video details: {str(e)}", xbmc.LOGERROR)
        return '', ''