import sys
import traceback
import requests
from urllib.parse import parse_qsl, urlencode, urlparse, parse_qs
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc
from bs4 import BeautifulSoup

_URL = sys.argv[0]
_HANDLE = int(sys.argv[1])
_ADDON = xbmcaddon.Addon()

def log(msg, level=xbmc.LOGDEBUG):
    # Only log if it's an error or if debug logging is enabled in addon settings
    if level == xbmc.LOGERROR or (_ADDON.getSetting('debug') == 'true'):
        plugin_id = _ADDON.getAddonInfo('id')
        xbmc.log(f"{plugin_id}: {msg}", level=level)

def get_url(**kwargs):
    return '{0}?{1}'.format(_URL, urlencode(kwargs))

def _convert_duration_to_seconds(duration_text):
    """Convert duration string (e.g., "1h42m" or "42m") to seconds"""
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

def clean_text(text):
    """Clean text from null characters and handle encoding"""
    if text is None:
        return ''
    return text.replace('\x00', '').strip()

def select_quality(video_url):
    """Handle quality selection via dialog"""
    qualities = ['Auto', '1080p', '720p', '480p', '360p', '240p']
    dialog = xbmcgui.Dialog()
    selected = dialog.select('Select Quality', qualities)

    if selected >= 0:  # If user didn't cancel
        quality = qualities[selected]
        # Create a new list item and play it
        play_item = xbmcgui.ListItem(path=get_url(action='play', video_url=video_url, quality=quality))
        xbmc.Player().play(item=get_url(action='play', video_url=video_url, quality=quality), listitem=play_item)

def add_video_quality_menu(menu, video_url):
    """Add quality selection options to the context menu"""
    qualities = ['auto', '1080p', '720p', '480p', '360p', '240p']
    for quality in qualities:
        menu.append((
            f'Play in {quality}',
            f'RunPlugin({get_url(action="play", video_url=video_url, quality=quality)})'
        ))

def login():
    """
    Login to TalkTV.cz with browser-like request
    Returns:
        requests.Session: Authenticated session if successful, False otherwise
    """
    email = _ADDON.getSetting('email')
    password = _ADDON.getSetting('password')

    if not email or not password:
        xbmcgui.Dialog().ok('Login Required', 'Please configure your login credentials in the addon settings.')
        return False

    session = requests.Session()

    try:
        # Initial headers for the first request
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'cs-CZ,cs;q=0.5',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Brave";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'sec-gpc': '1',
            'upgrade-insecure-requests': '1'
        }

        # Get login page
        login_page_response = session.get('https://www.talktv.cz/prihlasit', headers=headers)
        log(f"Login page status code: {login_page_response.status_code}", xbmc.LOGINFO)

        # Parse login page
        soup = BeautifulSoup(login_page_response.text, 'html.parser')
        csrf_input = soup.find('input', {'name': 'csrf'})

        if not csrf_input or not csrf_input.get('value'):
            log("CSRF token not found", xbmc.LOGERROR)
            return False

        csrf_token = csrf_input['value']
        log(f"Found CSRF token: {csrf_token[:10]}...", xbmc.LOGINFO)

        # Update headers for POST request
        headers.update({
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.talktv.cz',
            'referer': 'https://www.talktv.cz/prihlasit',
            'sec-fetch-site': 'same-origin',
            'cache-control': 'max-age=0'
        })

        # Since we can't execute JavaScript for reCAPTCHA, we'll need a different approach
        # For now, let's try without it and see what happens
        login_data = {
            'csrf': csrf_token,
            'email': email,
            'password': password
        }

        # Perform login
        login_response = session.post(
            'https://www.talktv.cz/prihlasit',
            data=login_data,
            headers=headers,
            allow_redirects=True
        )

        log(f"Login response status code: {login_response.status_code}", xbmc.LOGINFO)
        log(f"Login response URL: {login_response.url}", xbmc.LOGINFO)

        # Check if login was successful
        soup = BeautifulSoup(login_response.text, 'html.parser')
        user_menu = soup.find('div', class_='popup-account__header-email')

        if user_menu and email in user_menu.text:
            log("Login successful!", xbmc.LOGINFO)
            return session

        log("Login failed - checking response for error messages", xbmc.LOGERROR)
        # Try to find error message if any
        error_msg = soup.find('div', class_='error-message')
        if error_msg:
            log(f"Error message found: {error_msg.text}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification('Login Failed', error_msg.text)
        else:
            xbmcgui.Dialog().notification('Login Failed', 'Invalid credentials or reCAPTCHA required')

        return False

    except Exception as e:
        log(f"Login error: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Login Error', str(e))
        return False

def get_session():
    """
    Get a requests session with authentication cookie
    Returns:
        requests.Session: Authenticated session if successful, False otherwise
    """
    session_cookie = _ADDON.getSetting('session_cookie')

    if not session_cookie:
        xbmcgui.Dialog().ok('Session Required', 'Please configure your session cookie in the addon settings.')
        return False

    session = requests.Session()

    # Set the session cookie
    session.cookies.set('PHPSESSID', session_cookie, domain='www.talktv.cz')

    try:
        # Test the session by requesting the main page
        response = session.get('https://www.talktv.cz/videa')

        # Check if we're properly authenticated
        if 'popup-account__header-email' in response.text:
            log("Session cookie valid", xbmc.LOGINFO)
            return session
        else:
            log("Session cookie invalid", xbmc.LOGERROR)
            xbmcgui.Dialog().notification('Auth Error', 'Session cookie is invalid or expired')
            return False

    except Exception as e:
        log(f"Session error: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Session Error', str(e))
        return False

def list_categories():
    categories = [
        {'name': 'STANDASHOW', 'url': 'https://www.talktv.cz/standashow'},
        {'name': 'MOVIE WITCHES', 'url': 'https://www.talktv.cz/moviewitches'},
        {'name': 'TECHGUYS', 'url': 'https://www.talktv.cz/techguys'},
        {'name': 'JADRNÁ VĚDA', 'url': 'https://www.talktv.cz/jadrna-veda'},
        {'name': 'ZA HRANICÍ', 'url': 'https://www.talktv.cz/za-hranici'},
        {'name': 'DESIGN TALK', 'url': 'https://www.talktv.cz/design-talk'},
        {'name': 'SEZNAMY VIDEÍ & ARCHIV', 'url': None}  # Special handling for submenu
    ]

    xbmcplugin.setPluginCategory(_HANDLE, 'Categories')

    for category in categories:
        list_item = xbmcgui.ListItem(label=category['name'])
        url = get_url(action='listing', category_url=category['url']) if category['url'] else get_url(action='archive')
        is_folder = True
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)

    xbmcplugin.endOfDirectory(_HANDLE)

def list_archive():
    archive_items = [
        {'name': 'STANDASHOW SPECIÁLY', 'url': 'https://www.talktv.cz/seznam-videi/seznam-hejktqzt'},
        {'name': 'IRL PROCHÁZKY Z TERÉNU', 'url': 'https://www.talktv.cz/seznam-videi/irl-prochazky-z-terenu'},
        {'name': 'HODNOCENÍ HOSTŮ', 'url': 'https://www.talktv.cz/seznam-videi/hodnoceni-hostu'},
        {'name': 'CHARITA', 'url': 'https://www.talktv.cz/seznam-videi/charita'},
        {'name': 'PREZIDENTSKÉ VOLBY 2023', 'url': 'https://www.talktv.cz/seznam-videi/seznam-bxmzs6zw'},
        {'name': 'NEJMLADŠÍ POLITICI', 'url': 'https://www.talktv.cz/seznam-videi/nejmladsi-politici'},
        {'name': 'VOLBY 2021', 'url': 'https://www.talktv.cz/seznam-videi/volby-2021'},
        {'name': 'JARDA VS. NAOMI', 'url': 'https://www.talktv.cz/jarda-a-naomi'},
        {'name': 'ZÁKULISÍ TALKU', 'url': 'https://www.talktv.cz/seznam-videi/zakulisi-talk-tv'}
    ]

    xbmcplugin.setPluginCategory(_HANDLE, 'ARCHIV')

    for item in archive_items:
        list_item = xbmcgui.ListItem(label=item['name'])
        url = get_url(action='listing', category_url=item['url'])
        is_folder = True
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)

    xbmcplugin.endOfDirectory(_HANDLE)

def list_videos(category_url):
    session = get_session()
    if not session:
        return

    try:
        original_url = category_url
        is_paginated = 'page=' in category_url

        response = session.get(category_url)
        video_items = []
        has_next = False

        if is_paginated:
            try:
                data = response.json()
                if 'content' in data:
                    soup = BeautifulSoup(data['content'], 'html.parser')
                    video_items = soup.find_all('a', class_='media')
                    has_next = data.get('next', False)
            except:
                log("Failed to parse JSON response for paginated content", xbmc.LOGERROR)
                return
        else:
            soup = BeautifulSoup(response.text, 'html.parser')
            container = soup.find('div', id='videoListContainer')
            if container:
                video_items = container.find_all('a', class_='media')
                has_next = True
            else:
                log("Could not find video container in HTML", xbmc.LOGERROR)
                return

        for item in video_items:
            title_element = item.find('div', class_='media__name')
            if not title_element or not title_element.p:
                continue

            title = clean_text(title_element.p.text)
            video_url = 'https://www.talktv.cz' + item['href']

            duration_element = item.find('p', class_='duration')
            duration_text = duration_element.text.strip() if duration_element else "0:00"

            list_item = xbmcgui.ListItem(label=title)

            list_item.setProperty('IsPlayable', 'true')
            list_item.setIsFolder(False)

            img_element = item.find('img')
            thumbnail = img_element.get('data-src', '') if img_element else ''
            if not thumbnail and img_element:
                thumbnail = img_element.get('src', '')

            list_item.setArt({
                'thumb': thumbnail,
                'icon': thumbnail,
                'poster': thumbnail,
                'fanart': thumbnail
            })

            try:
                video_response = session.get(video_url)
                video_soup = BeautifulSoup(video_response.text, 'html.parser')
                details_element = video_soup.find('div', class_='details__info')
                if details_element:
                    description = details_element.text.strip()
                    parts = description.split('                -', 1)
                    if len(parts) == 2:
                        date = parts[0].strip()
                        content = parts[1].strip()
                        description = f"{date}\n{content}"
                else:
                    description = ''
            except:
                description = ''

            duration_seconds = _convert_duration_to_seconds(duration_text)

            # Use the modern InfoTagVideo API
            info_tag = list_item.getVideoInfoTag()
            info_tag.setTitle(title)
            info_tag.setPlot(description)
            info_tag.setDuration(duration_seconds)
            info_tag.setMediaType('video')

            list_item.setLabel2(duration_text)

            context_menu = [
                ('Play with different quality...', f'RunPlugin({get_url(action="select_quality", video_url=video_url)})')
            ]
            list_item.addContextMenuItems(context_menu)

            url = get_url(action='play', video_url=video_url)
            xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, False)

        if has_next:
            if is_paginated:
                current_page = int(category_url.split('page=')[1].split('&')[0])
                next_page = current_page + 1
            else:
                next_page = 1

            if '?' in original_url:
                next_url = f"{original_url}&page={next_page}"
            else:
                next_url = f"{original_url}?page={next_page}"

            next_item = xbmcgui.ListItem(label='Next Page')
            next_item.setArt({'icon': 'DefaultFolder.png'})
            xbmcplugin.addDirectoryItem(
                _HANDLE, get_url(action='listing', category_url=next_url), next_item, True)

        xbmcplugin.setContent(_HANDLE, 'videos')
        xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.endOfDirectory(_HANDLE)

    except Exception as e:
        log(f"Error: {str(e)}", xbmc.LOGERROR)
        log(f"Error traceback: {traceback.format_exc()}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Error', str(e))

def play_video(video_url, requested_quality=None):
    session = get_session()
    if not session:
        return

    try:
        response = session.get(video_url)
        soup = BeautifulSoup(response.text, 'html.parser')

        video_element = soup.find('video-js')
        if not video_element:
            log("Video player not found", xbmc.LOGERROR)
            return

        sources = video_element.find_all('source')
        if not sources:
            log("No video sources found", xbmc.LOGERROR)
            return

        # Get quality preference
        if not requested_quality:
            quality_index = int(_ADDON.getSetting('video_quality'))
            qualities = ['Auto', '1080p', '720p', '480p', '360p', '240p']
            requested_quality = qualities[quality_index]

        # Find best matching quality
        selected_url = None
        if requested_quality.lower() == 'auto':
            # Prefer HLS stream for auto quality
            for source in sources:
                if 'application/x-mpegURL' in source.get('type', ''):
                    selected_url = source['src']
                    break

        if not selected_url:
            # Find specific quality or fall back to next best
            qualities = ['1080p', '720p', '480p', '360p', '240p']
            if requested_quality in qualities:
                start_index = qualities.index(requested_quality)
                for quality in qualities[start_index:]:
                    for source in sources:
                        if quality in source.get('src', '') and 'video/mp4' in source.get('type', ''):
                            selected_url = source['src']
                            break
                    if selected_url:
                        break

        # If still no URL, take first available source
        if not selected_url and sources:
            selected_url = sources[0]['src']

        if not selected_url:
            log("No playable source found", xbmc.LOGERROR)
            return

        play_item = xbmcgui.ListItem(path=selected_url)

        # Set appropriate inputstream properties
        if '.m3u8' in selected_url:
            play_item.setMimeType('application/x-mpegURL')
            play_item.setContentLookup(False)
            play_item.setProperty('inputstream', 'inputstream.adaptive')
            play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
        else:
            play_item.setMimeType('video/mp4')

        # Add video info
        try:
            details_element = soup.find('div', class_='details__info')
            if details_element:
                description = details_element.text.strip()
                play_item.setInfo('video', {'plot': description})
        except:
            pass

        xbmcplugin.setResolvedUrl(_HANDLE, True, listitem=play_item)

    except Exception as e:
        log(f"Error playing video: {str(e)}", xbmc.LOGERROR)
        xbmcplugin.setResolvedUrl(_HANDLE, False, xbmcgui.ListItem())

def router(paramstring):
    params = dict(parse_qsl(paramstring[1:]))

    if not params:
        list_categories()
        return

    if params['action'] == 'listing':
        list_videos(params['category_url'])
    elif params['action'] == 'archive':
        list_archive()
    elif params['action'] == 'play':
        quality = params.get('quality', None)
        play_video(params['video_url'], quality)
    elif params['action'] == 'select_quality':
        select_quality(params['video_url'])

if __name__ == '__main__':
    router(sys.argv[2])
