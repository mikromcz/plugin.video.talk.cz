# -*- coding: utf-8 -*-

import sys
import traceback
import requests
from urllib.parse import parse_qsl, quote, urlencode
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc
from bs4 import BeautifulSoup

_URL = sys.argv[0]  # Base URL of the addon
_HANDLE = int(sys.argv[1])  # Handle for the Kodi plugin instance
_ADDON = xbmcaddon.Addon()  # Instance of the addon
ADDON_ID = xbmcaddon.Addon().getAddonInfo('id')  # ID of the addon

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

def login():
    # Main login function that tries available login methods

    # First try direct login
    if try_direct_login():
        return True

    # If direct login failed, try Patreon
    #if try_patreon_login():
    #    return True

    # Both methods failed
    return False

def try_direct_login():
    # Attempt direct login with form submission
    email = _ADDON.getSetting('email')
    password = _ADDON.getSetting('password')

    if not email or not password:
        return False

    session = requests.Session()

    try:
        # Get login page and CSRF token
        login_page = session.get('https://www.talktv.cz/prihlasit')
        soup = BeautifulSoup(login_page.text, 'html.parser')

        csrf_token = soup.find('input', {'name': 'csrf'})['value']
        recaptcha_div = soup.find('div', {'class': 'g-recaptcha'})
        site_key = recaptcha_div['data-sitekey']

        # Get reCAPTCHA token
        recaptcha_token = get_recaptcha_token(site_key)
        if not recaptcha_token:
            return False

        # Submit login
        login_data = {
            'email': email,
            'password': password,
            'csrf': csrf_token,
            'g-recaptcha-response': recaptcha_token
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.talktv.cz',
            'Referer': 'https://www.talktv.cz/prihlasit'
        }

        response = session.post('https://www.talktv.cz/prihlasit',
                              data=login_data,
                              headers=headers)

        if 'popup-account__header-email' in response.text:
            # Store session cookie
            session_cookie = session.cookies.get('PHPSESSID')
            if session_cookie:
                _ADDON.setSetting('session_cookie', session_cookie)
                return True

    except Exception as e:
        log(f"Direct login failed: {str(e)}", xbmc.LOGERROR)

    return False

def try_patreon_login():
    # Attempt login via Patreon OAuth
    session = requests.Session()

    try:
        # Start Patreon OAuth flow
        response = session.get('https://www.talktv.cz/srv/patreon-login')

        # This should redirect to Patreon's OAuth page
        if 'patreon.com/oauth2/authorize' in response.url:
            dialog = xbmcgui.Dialog()
            dialog.ok('Patreon Login',
                     'Pro přihlášení přes Patreon prosím:\n'
                     '1. Přihlaste se na talktv.cz přes Patreon ve webovém prohlížeči\n'
                     '2. Zkopírujte cookie PHPSESSID do nastavení doplňku')
            return False

    except Exception as e:
        log(f"Patreon login failed: {str(e)}", xbmc.LOGERROR)

    return False

def get_recaptcha_token(site_key):
    # Get reCAPTCHA token via Kodi GUI.
    dialog = xbmcgui.Dialog()
    dialog.ok('reCAPTCHA Required',
              'Pro přihlášení je potřeba vyřešit reCAPTCHA.\n'
              'Prosím navštivte stránku talktv.cz ve webovém prohlížeči,\n'
              'přihlaste se tam a pak zkopírujte cookie PHPSESSID do nastavení doplňku.')
    return None

def get_session():
    # Get a requests session with authentication cookie.
    # Attempts login if no valid session exists.
    session_cookie = _ADDON.getSetting('session_cookie')

    if not session_cookie:
        # No session cookie - try to login
        if not login():
            return False
        session_cookie = _ADDON.getSetting('session_cookie')

    session = requests.Session()
    session.cookies.set('PHPSESSID', session_cookie, domain='www.talktv.cz')

    try:
        # Test the session
        response = session.get('https://www.talktv.cz/videa')

        if 'popup-account__header-email' in response.text:
            log("Session cookie valid", xbmc.LOGINFO)
            return session
        else:
            # Session invalid - try to login again
            log("Session cookie invalid - attempting new login", xbmc.LOGWARNING)
            if login():
                # Recreate session with new cookie
                session = requests.Session()
                session.cookies.set('PHPSESSID', _ADDON.getSetting('session_cookie'), domain='www.talktv.cz')
                return session
            else:
                return False

    except Exception as e:
        log(f"Session validation failed: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Session Error', str(e))
        return False

def test_credentials():
    # Temporary function to test login credentials
    email = _ADDON.getSetting('email')
    password = _ADDON.getSetting('password')

    log(f"Testing credentials - Email length: {len(email) if email else 0}", xbmc.LOGINFO)
    log(f"Testing credentials - Password length: {len(password) if password else 0}", xbmc.LOGINFO)

    if not email or not password:
        xbmcgui.Dialog().ok('Test', 'Missing credentials in settings')
        return

    try:
        session = requests.Session()

        # Test basic connectivity
        response = session.get('https://www.talktv.cz/')
        log(f"Basic request status: {response.status_code}", xbmc.LOGINFO)

        # Get login page and CSRF token
        login_response = session.get('https://www.talktv.cz/prihlasit')
        login_soup = BeautifulSoup(login_response.text, 'html.parser')
        csrf_input = login_soup.find('input', {'name': 'csrf'})

        if csrf_input and csrf_input.get('value'):
            log(f"Found CSRF token: {csrf_input['value'][:10]}...", xbmc.LOGINFO)
        else:
            log("No CSRF token found", xbmc.LOGERROR)

        # Test XHR request
        headers = {'X-Requested-With': 'XMLHttpRequest'}
        xhr_response = session.get('https://www.talktv.cz/srv/getLoginStatus', headers=headers)
        log(f"XHR test response: {xhr_response.status_code}", xbmc.LOGINFO)

        xbmcgui.Dialog().ok('Test Results',
                           #f'email: {email}\n'
                           #f'password: {password}\n'
                           f'Basic request: {response.status_code}\n'
                           f'Login page: {login_response.status_code}\n'
                           f'CSRF token: {"Found" if csrf_input else "Not found"}\n'
                           f'XHR test: {xhr_response.status_code}')

    except Exception as e:
        log(f"Test failed: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok('Test Error', str(e))

def test_session():
    # Test if the current session cookie is valid
    session_cookie = _ADDON.getSetting('session_cookie')

    if not session_cookie:
        xbmcgui.Dialog().ok('Test Session', 'No session cookie configured. Please enter your session cookie in settings.')
        return False

    session = requests.Session()
    log("Testing session cookie...", xbmc.LOGINFO)

    try:
        # Set up the session cookie
        session.cookies.set('PHPSESSID', session_cookie, domain='www.talktv.cz')

        # Test the session by requesting the videos page
        response = session.get('https://www.talktv.cz/videa')

        # Check if we're properly authenticated
        if 'popup-account__header-email' in response.text:
            log("Session cookie is valid", xbmc.LOGINFO)
            xbmcgui.Dialog().ok('Test Session', 'Session cookie is valid! You are logged in.')
            return True
        else:
            log("Session cookie is invalid", xbmc.LOGERROR)
            xbmcgui.Dialog().ok('Test Session', 'Session cookie is invalid or expired. Please get a new cookie from your browser.')
            return False

    except Exception as e:
        log(f"Session test failed: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok('Test Session Error', str(e))
        return False

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

def select_quality(video_url):
    # Handle quality selection via dialog
    qualities = ['Auto', '1080p', '720p', '480p', '360p', '240p']
    dialog = xbmcgui.Dialog()
    selected = dialog.select('Vyberte kvalitu', qualities)

    if selected >= 0:  # If user didn't cancel
        quality = qualities[selected]
        # Create a new list item and play it
        play_item = xbmcgui.ListItem(path=get_url(action='play', video_url=video_url, quality=quality))
        xbmc.Player().play(item=get_url(action='play', video_url=video_url, quality=quality), listitem=play_item)

def search():
    # Create a dialog for user input
    keyboard = xbmcgui.Dialog()
    # Prompt the user to enter a search string
    search_string = keyboard.input('Hledat', type=xbmcgui.INPUT_ALPHANUM)

    if search_string:
        log(f"Searching for: {search_string}", xbmc.LOGINFO)
        # Construct the search URL with the encoded search string
        search_url = f'https://www.talktv.cz/hledani?q={quote(search_string)}'
        # List the search results from the constructed URL
        list_search_results(search_url)

def list_search_results(search_url):
    # Get a session for making HTTP requests
    session = get_session()
    if not session:
        return

    try:
        log(f"Searching with URL: {search_url}", xbmc.LOGINFO)
        # Make the HTTP GET request
        response = session.get(search_url)
        if response.status_code != 200:
            log(f"Search request failed: {response.status_code}", xbmc.LOGERROR)
            return

        # Parse the HTML response
        soup = BeautifulSoup(response.text, 'html.parser')
        # Find the container with search results
        results_container = soup.find('div', id='mainSearchListContainer')
        if not results_container:
            log("No search results container found", xbmc.LOGWARNING)
            xbmcgui.Dialog().notification('Hledání', 'Žádné výsledky nenalezeny')
            return

        # Find all video items in the results container
        video_items = results_container.find_all('a', class_='media')
        if not video_items:
            log("No search results found", xbmc.LOGINFO)
            xbmcgui.Dialog().notification('Hledání', 'Žádné výsledky nenalezeny')
            return

        # Set the plugin category and content type
        xbmcplugin.setPluginCategory(_HANDLE, 'Výsledky hledání')
        xbmcplugin.setContent(_HANDLE, 'videos')

        for item in video_items:
            # Get the title of the video
            title_element = item.find('div', class_='media__name')
            if not title_element or not title_element.p:
                continue

            title = clean_text(title_element.p.text)
            video_url = 'https://www.talktv.cz' + item['href']

            # Get the duration of the video
            duration_element = item.find('p', class_='duration')
            duration_text = duration_element.text.strip() if duration_element else "0:00"

            # Create a list item for the video
            list_item = xbmcgui.ListItem(label=title)
            list_item.setProperty('IsPlayable', 'true')
            list_item.setIsFolder(False)

            # Get the thumbnail image for the video
            img_element = item.find('img')
            thumbnail = img_element.get('data-src', '') if img_element else ''
            if not thumbnail and img_element:
                thumbnail = img_element.get('src', '')

            list_item.setArt({
                'thumb': thumbnail,
                'icon': thumbnail
            })

            # Convert the duration to seconds
            duration_seconds = convert_duration_to_seconds(duration_text)

            # Set video info tags
            info_tag = list_item.getVideoInfoTag()
            info_tag.setTitle(title)
            info_tag.setDuration(duration_seconds)
            info_tag.setMediaType('video')

            # Add context menu items
            context_menu = [
                ('Přehrát (zeptat se na kvalitu)',
                 f'RunPlugin({get_url(action="select_quality", video_url=video_url)})')
            ]
            list_item.addContextMenuItems(context_menu)

            # Add the directory item to the Kodi plugin
            url = get_url(action='play', video_url=video_url)
            xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, False)

        # End the directory listing
        xbmcplugin.endOfDirectory(_HANDLE)

    except Exception as e:
        log("Error in list_search_results", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Error', str(e))

def list_menu():
    # Define the categories for the menu
    categories = [
        {
            'name': 'HLEDAT',
            'url': 'search',
            'description': 'Vyhledávání v obsahu [COLOR springgreen]TALK TV[/COLOR].',
            'image': 'search.png'
        },
        {
            'name': 'POSLEDNÍ VIDEA',
            'url': 'https://www.talktv.cz/videa',
            'description': 'Nejnovější videa na [COLOR springgreen]TALK TV[/COLOR].',
            'image': 'latest.png'
        },
        {
            'name': 'POPULÁRNÍ VIDEA',
            'url': 'popular',
            'description': 'Trendující videa na [COLOR springgreen]TALK TV[/COLOR].',
            'image': 'popular.png'
        },
        {
            'name': 'NEJLEPŠÍ VIDEA',
            'url': 'top',
            'description': 'Nejsledovanější videa na [COLOR springgreen]TALK TV[/COLOR].\n\n[COLOR slategrey]Poznámka: Tato kategorie není dostupná ve webovém rozhraní.[/COLOR]',
            'image': 'top.png'
        },
        {
            'name': 'POKRAČOVAT V PŘEHRÁVÁNÍ',
            'url': 'continue',
            'description': 'Rozkoukaná videa na [COLOR springgreen]TALK TV[/COLOR].\n\n[COLOR slategrey]Poznámka: Tato kategorie se neaktualizuje při přehrávání přes Kodi.[/COLOR]',
            'image': 'continue-watching.png'
        },
        {
            'name': 'TVŮRCI',
            'url': 'creators',
            'description': 'Všichni tvůrci na [COLOR springgreen]TALK TV[/COLOR] a jejich pořady.\n\n[COLOR springgreen]STANDASHOW[/COLOR],\n[COLOR springgreen]TECH GUYS[/COLOR],\n[COLOR springgreen]JADRNÁ VĚDA[/COLOR],\n[COLOR springgreen]ZA HRANICÍ[/COLOR],\n[COLOR springgreen]MOVIE WITCHES[/COLOR],\n[COLOR springgreen]DESIGN TALK[/COLOR]',
            'image': 'creators.png'
        },
        {
            'name': 'ARCHIV',
            'url': 'archive',
            'description': 'Archiv pořadů [COLOR springgreen]TALK TV[/COLOR] a speciálních sérií.\n\n[COLOR springgreen]IRL STREAMY[/COLOR],\n[COLOR springgreen]HODNOCENÍ HOSTŮ[/COLOR],\n[COLOR springgreen]JARDA VS. NAOMI[/COLOR],\n...',
            'image': 'archive.png'
        }
    ]

    # Set the plugin category and content type
    xbmcplugin.setPluginCategory(_HANDLE, 'Categories')
    xbmcplugin.setContent(_HANDLE, 'files')

    for category in categories:
        # Create a list item for each category
        list_item = xbmcgui.ListItem(label=category['name'])
        image_path = get_image_path(category['image'])

        list_item.setArt({
            'thumb': image_path,
            'icon': image_path
        })

        info_tag = list_item.getVideoInfoTag()
        info_tag.setPlot(category['description'])
        info_tag.setTitle(category['name'])

        # Determine the URL for the category action
        if category['url'] == 'search':
            url = get_url(action='search')
        elif category['url'] == 'popular':
            url = get_url(action='popular')
        elif category['url'] == 'creators':
            url = get_url(action='creators')
        elif category['url'] == 'archive':
            url = get_url(action='archive')
        else:
            url = get_url(action='listing', category_url=category['url'])

        is_folder = True
        # Add the directory item to the Kodi plugin
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)

    # End the directory listing
    xbmcplugin.endOfDirectory(_HANDLE)

def list_popular(page=1):
    # Get a session for making HTTP requests
    session = get_session()
    if not session:
        return

    try:
        # Always include pages parameter
        api_url = f'https://www.talktv.cz/srv/videos/home?pages={page}'

        log(f"Fetching popular videos from API: {api_url}", xbmc.LOGINFO)

        # Add necessary headers for AJAX request
        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://www.talktv.cz/'
        }

        response = session.get(api_url, headers=headers)
        if response.status_code != 200:
            log(f"API request failed: {response.status_code}", xbmc.LOGERROR)
            return

        # Parse JSON response
        data = response.json()
        if 'c2' not in data:
            log("No popular videos section in response", xbmc.LOGERROR)
            return

        # Parse the HTML content from c2 section
        soup = BeautifulSoup(data['c2'], 'html.parser')

        xbmcplugin.setPluginCategory(_HANDLE, 'Populární videa')
        xbmcplugin.setContent(_HANDLE, 'videos')

        # Find all video items
        list_items = soup.find_all('div', class_='list__item')

        for list_item_div in list_items:
            item = list_item_div.find('a', class_='media')
            if not item:
                continue

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
                'icon': thumbnail
            })

            try:
                log(f"Fetching details for video: {video_url}", xbmc.LOGDEBUG)
                # Make the HTTP GET request for video details
                video_response = session.get(video_url)
                video_soup = BeautifulSoup(video_response.text, 'html.parser')
                details_element = video_soup.find('div', class_='details__info')
                if details_element:
                    # Extract and clean the description and date
                    description = details_element.text.strip()
                    parts = description.split('                -', 1)
                    if len(parts) == 2:
                        date = parts[0].strip()
                        content = parts[1].strip()
                        description = content  # Only content without date
                    else:
                        date = ''
                        content = description
                else:
                    description = ''
                    date = ''
                    log(f"No details found for video: {video_url}", xbmc.LOGWARNING)
            except Exception as e:
                description = ''
                date = ''
                log(f"Error fetching video details: {video_url}", xbmc.LOGWARNING)

            # Convert the duration to seconds
            duration_seconds = convert_duration_to_seconds(duration_text)

            # Set video info tags
            info_tag = list_item.getVideoInfoTag()
            info_tag.setTitle(title)
            info_tag.setPlot(description)
            info_tag.setDuration(duration_seconds)
            info_tag.setMediaType('video')

            # Add context menu items
            context_menu = [
                ('Přehrát (zeptat se na kvalitu)',
                 f'RunPlugin({get_url(action="select_quality", video_url=video_url)})')
            ]
            list_item.addContextMenuItems(context_menu)

            url = get_url(action='play', video_url=video_url)
            xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, False)

        # Add 'Next Page' item
        next_page = page + 1
        next_item = xbmcgui.ListItem(label='Další stránka')
        next_item.setArt({
            'icon': get_image_path('foldernext.png'),
            'thumb': get_image_path('foldernext.png')
        })
        url = get_url(action='popular', page=next_page)
        xbmcplugin.addDirectoryItem(_HANDLE, url, next_item, True)

        xbmcplugin.endOfDirectory(_HANDLE)

    except Exception as e:
        log("Error in list_popular", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Error', str(e))

def list_top(page=1):
    # Get a session for making HTTP requests
    session = get_session()
    if not session:
        return

    try:
        # Always include pages parameter
        api_url = f'https://www.talktv.cz/srv/videos/home?pages={page}'

        log(f"Fetching top videos from API: {api_url}", xbmc.LOGINFO)

        # Add necessary headers for AJAX request
        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://www.talktv.cz/'
        }

        response = session.get(api_url, headers=headers)
        if response.status_code != 200:
            log(f"API request failed: {response.status_code}", xbmc.LOGERROR)
            return

        # Parse JSON response
        data = response.json()
        if 'c3' not in data:
            log("No top videos section in response", xbmc.LOGERROR)
            return

        # Parse the HTML content from c3 section
        soup = BeautifulSoup(data['c3'], 'html.parser')

        xbmcplugin.setPluginCategory(_HANDLE, 'Nejlepší videa')
        xbmcplugin.setContent(_HANDLE, 'videos')

        # Find all video items
        list_items = soup.find_all('div', class_='list__item')

        for list_item_div in list_items:
            item = list_item_div.find('a', class_='media')
            if not item:
                continue

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
                'icon': thumbnail
            })

            try:
                log(f"Fetching details for video: {video_url}", xbmc.LOGDEBUG)
                # Make the HTTP GET request for video details
                video_response = session.get(video_url)
                video_soup = BeautifulSoup(video_response.text, 'html.parser')
                details_element = video_soup.find('div', class_='details__info')
                if details_element:
                    # Extract and clean the description and date
                    description = details_element.text.strip()
                    parts = description.split('                -', 1)
                    if len(parts) == 2:
                        date = parts[0].strip()
                        content = parts[1].strip()
                        description = content  # Only content without date
                    else:
                        date = ''
                        content = description
                else:
                    description = ''
                    date = ''
                    log(f"No details found for video: {video_url}", xbmc.LOGWARNING)
            except Exception as e:
                description = ''
                date = ''
                log(f"Error fetching video details: {video_url}", xbmc.LOGWARNING)

            # Convert the duration to seconds
            duration_seconds = convert_duration_to_seconds(duration_text)

            # Set video info tags
            info_tag = list_item.getVideoInfoTag()
            info_tag.setTitle(title)
            info_tag.setPlot(description)
            info_tag.setDuration(duration_seconds)
            info_tag.setMediaType('video')

            # Add context menu items
            context_menu = [
                ('Přehrát (zeptat se na kvalitu)',
                 f'RunPlugin({get_url(action="select_quality", video_url=video_url)})')
            ]
            list_item.addContextMenuItems(context_menu)

            url = get_url(action='play', video_url=video_url)
            xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, False)

        # Add 'Next Page' item if there are more items
        if list_items:  # Only add next page if we have items on current page
            next_page = page + 1
            next_item = xbmcgui.ListItem(label='Další stránka')
            next_item.setArt({
                'icon': get_image_path('foldernext.png'),
                'thumb': get_image_path('foldernext.png')
            })
            url = get_url(action='top', page=next_page)
            xbmcplugin.addDirectoryItem(_HANDLE, url, next_item, True)

        xbmcplugin.endOfDirectory(_HANDLE)

    except Exception as e:
        log("Error in list_top", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Error', str(e))

def list_continue(page=1):
    # Get a session for making HTTP requests
    session = get_session()
    if not session:
        return

    try:
        # Always include pages parameter
        api_url = f'https://www.talktv.cz/srv/videos/home?pages={page}'

        log(f"Fetching continue watching videos from API: {api_url}", xbmc.LOGINFO)

        # Add necessary headers for AJAX request
        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://www.talktv.cz/'
        }

        response = session.get(api_url, headers=headers)
        if response.status_code != 200:
            log(f"API request failed: {response.status_code}", xbmc.LOGERROR)
            return

        # Parse JSON response
        data = response.json()
        if 'c1' not in data:
            log("No continue watching section in response", xbmc.LOGERROR)
            return

        # Parse the HTML content from c1 section
        soup = BeautifulSoup(data['c1'], 'html.parser')

        xbmcplugin.setPluginCategory(_HANDLE, 'Pokračovat v přehrávání')
        xbmcplugin.setContent(_HANDLE, 'videos')

        # Find all video items
        list_items = soup.find_all('div', class_='list__item')

        for list_item_div in list_items:
            item = list_item_div.find('a', class_='media')
            if not item:
                continue

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
                'icon': thumbnail
            })

            try:
                log(f"Fetching details for video: {video_url}", xbmc.LOGDEBUG)
                # Make the HTTP GET request for video details
                video_response = session.get(video_url)
                video_soup = BeautifulSoup(video_response.text, 'html.parser')
                details_element = video_soup.find('div', class_='details__info')
                if details_element:
                    # Extract and clean the description and date
                    description = details_element.text.strip()
                    parts = description.split('                -', 1)
                    if len(parts) == 2:
                        date = parts[0].strip()
                        content = parts[1].strip()
                        description = content  # Only content without date
                    else:
                        date = ''
                        content = description
                else:
                    description = ''
                    date = ''
                    log(f"No details found for video: {video_url}", xbmc.LOGWARNING)
            except Exception as e:
                description = ''
                date = ''
                log(f"Error fetching video details: {video_url}", xbmc.LOGWARNING)

            # Convert the duration to seconds
            duration_seconds = convert_duration_to_seconds(duration_text)

            # Set video info tags
            info_tag = list_item.getVideoInfoTag()
            info_tag.setTitle(title)
            info_tag.setPlot(description)
            info_tag.setDuration(duration_seconds)
            info_tag.setMediaType('video')

            # Add context menu items
            context_menu = [
                ('Přehrát (zeptat se na kvalitu)',
                 f'RunPlugin({get_url(action="select_quality", video_url=video_url)})')
            ]
            list_item.addContextMenuItems(context_menu)

            url = get_url(action='play', video_url=video_url)
            xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, False)

        # Add 'Next Page' item if there are more items
        if list_items:  # Only add next page if we have items on current page
            next_page = page + 1
            next_item = xbmcgui.ListItem(label='Další stránka')
            next_item.setArt({
                'icon': get_image_path('foldernext.png'),
                'thumb': get_image_path('foldernext.png')
            })
            url = get_url(action='continue', page=next_page)
            xbmcplugin.addDirectoryItem(_HANDLE, url, next_item, True)

        xbmcplugin.endOfDirectory(_HANDLE)

    except Exception as e:
        log("Error in list_continue", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Error', str(e))

def list_creators():
    # Define the creators and their details
    creators = [
        {
            'name': 'STANDASHOW',
            'url': 'https://www.talktv.cz/standashow',
            'description': 'Výstup z vaší názorové bubliny. Politika, společnost, kauzy a Bruntál. Obsahují minimálně jednoho [COLOR springgreen]Standu[/COLOR].',
            'image': 'show-standashow.jpg'
        },
        {
            'name': 'TECH GUYS',
            'url': 'https://www.talktv.cz/techguys',
            'description': 'Kde unboxingy končí, my začínáme. Apple, kryptoměny, umělá inteligence a pak zase Apple. Každý týden s [COLOR springgreen]Honzou Březinou[/COLOR], [COLOR springgreen]Kicomem[/COLOR] a [COLOR springgreen]Davidem Grudlem[/COLOR].',
            'image': 'show-tech-guys.jpg'
        },
        {
            'name': 'JADRNÁ VĚDA',
            'url': 'https://www.talktv.cz/jadrna-veda',
            'description': 'Pořad, který 9 z 10 diváků nepochopí (a ten desátý je [COLOR springgreen]Leoš Kyša[/COLOR], který to moderuje). Diskuse se skutečnými vědci o skutečné vědě. Pyramidy, kvantová fyzika nebo objevování vesmíru.',
            'image': 'show-jadrna-veda.jpg'
        },
        {
            'name': 'ZA HRANICÍ',
            'url': 'https://www.talktv.cz/za-hranici',
            'description': 'Popelář v Londýně, letuška v Kataru nebo podnikatel v Gambii. Češi žijící v zahraničí a cestovatel [COLOR springgreen]Vladimír Váchal[/COLOR], který ví o cestování (skoro) vše. A na zbytek se nebojí zeptat.',
            'image': 'show-za-hranici.jpg'
        },
        {
            'name': 'MOVIE WITCHES',
            'url': 'https://www.talktv.cz/moviewitches',
            'description': 'Tři holky [COLOR springgreen]Bety[/COLOR] + [COLOR springgreen]Baty[/COLOR] + [COLOR springgreen]Shial[/COLOR] si povídají o filmech, které si to zaslouží. Od vzpomínek přes zajímavosti a shrnutí děje.',
            'image': 'show-movie-witches.jpg'
        },
        {
            'name': 'DESIGN TALK',
            'url': 'https://www.talktv.cz/design-talk',
            'description': '[COLOR springgreen]Lukáš Veverka[/COLOR] a jeho hosté diskutují o věcech, kterým většina diváků vůbec nevěnuje pozornost. Filmy, grafika, motion design i největší faily v dějinách designu a kinematografie.',
            'image': 'show-design-talk.jpg'
        }
    ]

    # Set the plugin category and content type
    xbmcplugin.setPluginCategory(_HANDLE, 'Tvůrci')
    xbmcplugin.setContent(_HANDLE, 'files')

    for creator in creators:
        # Create a list item for each creator
        list_item = xbmcgui.ListItem(label=creator['name'])
        image_path = get_image_path(creator['image'])

        list_item.setArt({
            'thumb': image_path,
            'icon': image_path
        })

        info_tag = list_item.getVideoInfoTag()
        info_tag.setPlot(creator['description'])
        info_tag.setTitle(creator['name'])

        # Determine the URL for the creator's content
        url = get_url(action='listing', category_url=creator['url'])
        is_folder = True
        # Add the directory item to the Kodi plugin
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)

    # End the directory listing
    xbmcplugin.endOfDirectory(_HANDLE)

def list_archive():
    # Define the archive items and their details
    archive_items = [
        {
            'name': 'STANDASHOW SPECIÁLY',
            'url': 'https://www.talktv.cz/seznam-videi/seznam-hejktqzt',
            'description': 'Minutu po minutě. Den po dni. Důležité události a exkluzívní hosté ve speciálech [COLOR springgreen]STANDASHOW[/COLOR]. Unikátní formát, který kombinuje prvky podcastu, dokumentu a časové reality show.',
            'image': 'archiv-standashow-specialy.jpg'
        },
        {
            'name': 'IRL PROCHÁZKY Z TERÉNU',
            'url': 'https://www.talktv.cz/seznam-videi/irl-prochazky-z-terenu',
            'description': 'Kamera, baťoh, mikrofony, sim karta, power banky, hromadu kabelů... to jsou IRL streamy. Procházky z terénu. Živé vysílání skoro odkukoli. Mix podcastu, dokumentu a reality show.',
            'image': 'archiv-irl-prochazky.jpg'
        },
        {
            'name': 'HODNOCENÍ HOSTŮ',
            'url': 'https://www.talktv.cz/seznam-videi/hodnoceni-hostu',
            'description': 'Nezapomenutelnou atmosféru a komornější povídání, jak na veřejném vysílání. Takový virtuální sraz [COLOR springgreen]STANDASHOW[/COLOR]. Většinou prozradíme spoustu zajímavostí z backstage.',
            'image': 'archiv-hodnoceni-hostu.jpg'
        },
        {
            'name': 'CHARITA',
            'url': 'https://www.talktv.cz/seznam-videi/charita',
            'description': 'Pomáháme. Podcast má být především zábava, ale někde je třeba probrat i vážné téma. A díky skvělé komunitě, která se kolem [COLOR springgreen]STANDASHOW[/COLOR] vytvořila, můžeme pomoct dobré věci.',
            'image': 'archiv-charita.jpg'
        },
        {
            'name': 'PREZIDENTSKÉ VOLBY 2023',
            'url': 'https://www.talktv.cz/seznam-videi/seznam-bxmzs6zw',
            'description': 'Volba prezidenta České republiky 2023. Pozvali jsme všechny kandidáty a takhle to dopadlo...',
            'image': 'archiv-prezidentske-volby-2023.jpg'
        },
        {
            'name': 'NEJMLADŠÍ POLITICI',
            'url': 'https://www.talktv.cz/seznam-videi/nejmladsi-politici',
            'description': 'Pozvali jsme si ty nejmladší politiky ze všech politických stran zastoupených v parlamentu. A tady je výsledek.',
            'image': 'archiv-nejmladsi-politici.jpg'
        },
        {
            'name': 'VOLBY 2021',
            'url': 'https://www.talktv.cz/seznam-videi/volby-2021',
            'description': '8 politických podcastů, více jak 13 hodin materiálu. V každém rozhovoru se probírají kontroverzní, ale také obyčejná lidská témata.',
            'image': 'archiv-volby-2021.jpg'
        },
        {
            'name': 'JARDA VS. NAOMI',
            'url': 'https://www.talktv.cz/jarda-a-naomi',
            'description': 'Herní novinář [COLOR springgreen]Jarda Möwald[/COLOR] a fanynka japonské popkultury [COLOR springgreen]Naomi Adachi[/COLOR]. Diskuse o zajímavostech ze světa her, filmů a seriálů. Celé záznamy pro předplatitele na talktv.cz.',
            'image': 'show-jarda-vs-naomi.jpg'
        },
        {
            'name': 'ZÁKULISÍ TALKU',
            'url': 'https://www.talktv.cz/seznam-videi/zakulisi-talk-tv',
            'description': 'Toto jsme my. Váš/náš :D [COLOR springgreen]TALK[/COLOR]. A toto jsou všechna videa ze zákulisí.',
            'image': 'archiv-zakulisi-talku.jpg'
        }
    ]

    # Set the plugin category and content type
    xbmcplugin.setPluginCategory(_HANDLE, 'ARCHIV')
    xbmcplugin.setContent(_HANDLE, 'files')

    for item in archive_items:
        # Create a list item for each archive item
        list_item = xbmcgui.ListItem(label=item['name'])
        image_path = get_image_path(item['image'])

        list_item.setArt({
            'thumb': image_path,
            'icon': image_path
        })

        info_tag = list_item.getVideoInfoTag()
        info_tag.setPlot(item['description'])
        info_tag.setTitle(item['name'])

        # Determine the URL for the archive item's content
        url = get_url(action='listing', category_url=item['url'])
        is_folder = True
        # Add the directory item to the Kodi plugin
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)

    # End the directory listing
    xbmcplugin.endOfDirectory(_HANDLE)

def list_videos(category_url):
    # Get a session for making HTTP requests
    session = get_session()
    if not session:
        log("Failed to get valid session", xbmc.LOGERROR)
        return

    try:
        log(f"Listing videos for category: {category_url}", xbmc.LOGINFO)
        original_url = category_url
        is_paginated = 'page=' in category_url

        # Make the HTTP GET request
        response = session.get(category_url)
        if response.status_code != 200:
            log(f"Failed to fetch category page: {response.status_code}", xbmc.LOGERROR)
            return

        video_items = []
        has_next = False

        if is_paginated:
            log("Processing paginated response", xbmc.LOGDEBUG)
            try:
                # Parse the JSON response for paginated content
                data = response.json()
                if 'content' in data:
                    soup = BeautifulSoup(data['content'], 'html.parser')
                    video_items = soup.find_all('a', class_='media')
                    has_next = data.get('next', False)
                    log(f"Found {len(video_items)} videos in paginated response", xbmc.LOGDEBUG)
                else:
                    log("No content field in paginated response", xbmc.LOGERROR)
                    return
            except Exception as e:
                log("Failed to parse JSON response for paginated content", xbmc.LOGERROR)
                return
        else:
            log("Processing regular HTML response", xbmc.LOGDEBUG)
            # Parse the HTML response
            soup = BeautifulSoup(response.text, 'html.parser')
            container = soup.find('div', id='videoListContainer')
            if container:
                video_items = container.find_all('a', class_='media')
                has_next = True
                log(f"Found {len(video_items)} videos in container", xbmc.LOGDEBUG)
            else:
                log("Could not find video container in HTML", xbmc.LOGERROR)
                return

        for item in video_items:
            title_element = item.find('div', class_='media__name')
            if not title_element or not title_element.p:
                log("Skipping item with missing title", xbmc.LOGWARNING)
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
                'icon': thumbnail
            })

            try:
                log(f"Fetching details for video: {video_url}", xbmc.LOGDEBUG)
                # Make the HTTP GET request for video details
                video_response = session.get(video_url)
                video_soup = BeautifulSoup(video_response.text, 'html.parser')
                details_element = video_soup.find('div', class_='details__info')
                if details_element:
                    # Extract and clean the description and date
                    description = details_element.text.strip()
                    parts = description.split('                -', 1)
                    if len(parts) == 2:
                        date = parts[0].strip()
                        content = parts[1].strip()
                        description = content  # Only content without date
                    else:
                        date = ''
                        content = description
                else:
                    description = ''
                    date = ''
                    log(f"No details found for video: {video_url}", xbmc.LOGWARNING)
            except Exception as e:
                description = ''
                date = ''
                log(f"Error fetching video details: {video_url}", xbmc.LOGWARNING)

            # Convert the duration to seconds
            duration_seconds = convert_duration_to_seconds(duration_text)

            # Set video info tags
            info_tag = list_item.getVideoInfoTag()
            info_tag.setTitle(title)
            info_tag.setPlot(description)
            info_tag.setDuration(duration_seconds)
            info_tag.setMediaType('video')

            if date:
                info_tag.setPremiered(parse_date(date))

            list_item.setLabel2(duration_text)

            # Add context menu items
            context_menu = [
                ('Přehrát (zeptat se na kvalitu)',
                 f'RunPlugin({get_url(action="select_quality", video_url=video_url)})')
            ]
            list_item.addContextMenuItems(context_menu)

            # Add the directory item to the Kodi plugin
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

            log(f"Adding next page item: page {next_page}", xbmc.LOGDEBUG)
            next_item = xbmcgui.ListItem(label='Další strana')
            next_item.setArt({
                'icon': get_image_path('foldernext.png'),
                'thumb': get_image_path('foldernext.png')
            })
            xbmcplugin.addDirectoryItem(_HANDLE, get_url(action='listing', category_url=next_url), next_item, True)

        # Set the content type and sort method for the directory
        xbmcplugin.setContent(_HANDLE, 'videos')
        xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.endOfDirectory(_HANDLE)

    except Exception as e:
        log("Error in list_videos", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Error', str(e))

def play_video(video_url, requested_quality=None):
    # Get a session for making HTTP requests
    session = get_session()
    if not session:
        log("Failed to get valid session for video playback", xbmc.LOGERROR)
        return

    try:
        log(f"Attempting to play video: {video_url}", xbmc.LOGINFO)
        response = session.get(video_url)
        if response.status_code != 200:
            log(f"Failed to fetch video page: {response.status_code}", xbmc.LOGERROR)
            return

        # Parse the HTML response
        soup = BeautifulSoup(response.text, 'html.parser')
        video_element = soup.find('video-js')
        if not video_element:
            log("Video player element not found in page", xbmc.LOGERROR)
            return

        # Get quality preference if not specified
        if not requested_quality:
            quality_index = int(_ADDON.getSetting('video_quality'))
            qualities = ['Auto', '1080p', '720p', '480p', '360p', '240p']
            requested_quality = qualities[quality_index]

        # Find the best available source
        sources = video_element.find_all('source')
        selected_url = None
        use_hls = False

        # First try HLS for Auto quality
        if requested_quality.lower() == 'auto':
            for source in sources:
                if source.get('type') == 'application/x-mpegURL':
                    selected_url = source['src']
                    use_hls = True
                    log("Selected HLS stream for auto quality", xbmc.LOGINFO)
                    break

        # If no HLS or specific quality requested, try MP4
        if not selected_url:
            qualities = ['1080p', '720p', '480p', '360p', '240p']
            if requested_quality != 'Auto':
                # Start from requested quality
                start_idx = qualities.index(requested_quality)
                qualities = qualities[start_idx:]

            for quality in qualities:
                for source in sources:
                    if (source.get('type') == 'video/mp4' and
                        quality in source.get('src', '')):
                        selected_url = source['src']
                        log(f"Selected {quality} MP4 stream", xbmc.LOGINFO)
                        break
                if selected_url:
                    break

        # Fallback to first available source if nothing else matched
        if not selected_url and sources:
            selected_url = sources[0]['src']
            log("Falling back to first available source", xbmc.LOGWARNING)

        if not selected_url:
            log("No playable source found", xbmc.LOGERROR)
            xbmcplugin.setResolvedUrl(_HANDLE, False, xbmcgui.ListItem())
            return

        # Setup playback
        play_item = xbmcgui.ListItem(path=selected_url)

        # Configure inputstream
        if use_hls:
            play_item.setMimeType('application/x-mpegURL')
            play_item.setProperty('inputstream', 'inputstream.adaptive')
            play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
        else:
            play_item.setMimeType('video/mp4')

        play_item.setContentLookup(False)

        # Add metadata if available
        try:
            details = soup.find('div', class_='details__info')
            if details:
                description = details.text.strip().split('                -', 1)[-1].strip()
                title = soup.find('h1', class_='details__header')
                if title:
                    title = title.text.strip()

                info_tag = play_item.getVideoInfoTag()
                info_tag.setMediaType('video')
                info_tag.setPlot(description)

                if title:
                    info_tag.setTitle(title)

        except Exception as e:
            log(f"Failed to set video metadata: {str(e)}", xbmc.LOGWARNING)

        # Start playback
        xbmcplugin.setResolvedUrl(_HANDLE, True, listitem=play_item)

    except Exception as e:
        log(f"Error during video playback setup: {str(e)}", xbmc.LOGERROR)
        xbmcplugin.setResolvedUrl(_HANDLE, False, xbmcgui.ListItem())

def router(paramstring):
    # Parse the query parameters from the URL
    params = dict(parse_qsl(paramstring[1:]))
    log(f"Router received params: {params}", xbmc.LOGINFO)

    if not params:
        # If no parameters, list the main menu
        list_menu()
        return

    # Route to the appropriate function based on the 'action' parameter
    if params['action'] == 'search':
        search()
    elif params['action'] == 'popular':
        # Always pass a page number, default to 1 if not specified
        page = int(params.get('page', 1))
        list_popular(page)
    elif params['action'] == 'top':
        # Handle top videos listing
        page = int(params.get('page', 1))
        list_top(page)
    elif params['action'] == 'continue':
        # Handle continue watching listing
        page = int(params.get('page', 1))
        list_continue(page)
    elif params['action'] == 'creators':
        list_creators()
    elif params['action'] == 'listing':
        # If it's a regular URL, use list_videos
        if params['category_url'].startswith('http'):
            list_videos(params['category_url'])
        # If it's 'top', use list_top
        elif params['category_url'] == 'top':
            list_top(1)
        # If it's 'continue', use list_continue
        elif params['category_url'] == 'continue':
            list_continue(1)
        else:
            log(f"Invalid category URL: {params['category_url']}", xbmc.LOGERROR)
            return
    elif params['action'] == 'archive':
        list_archive()
    elif params['action'] == 'play':
        quality = params.get('quality', None)
        play_video(params['video_url'], quality)
    elif params['action'] == 'select_quality':
        select_quality(params['video_url'])
    elif params['action'] == 'test_credentials':
        test_credentials()
    elif params['action'] == 'test_session':
        test_session()

if __name__ == '__main__':
    # Entry point for the addon, route the request based on the parameters
    router(sys.argv[2])
