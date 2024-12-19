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
    # Login to talktv.cz with browser-like request
    email = _ADDON.getSetting('email')
    password = _ADDON.getSetting('password')

    if not email or not password:
        log("Missing login credentials", xbmc.LOGERROR)
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

        log("Attempting login...", xbmc.LOGINFO)

        # Get login page
        login_page_response = session.get('https://www.talktv.cz/prihlasit', headers=headers)
        log(f"Login page status code: {login_page_response.status_code}", xbmc.LOGINFO)

        if login_page_response.status_code != 200:
            log(f"Failed to load login page: {login_page_response.status_code}", xbmc.LOGERROR)
            return False

        # Parse login page
        soup = BeautifulSoup(login_page_response.text, 'html.parser')
        csrf_input = soup.find('input', {'name': 'csrf'})

        if not csrf_input or not csrf_input.get('value'):
            log("CSRF token not found", xbmc.LOGERROR)
            return False

        csrf_token = csrf_input['value']
        log(f"Found CSRF token: {csrf_token[:10]}...", xbmc.LOGDEBUG)

        # Update headers for POST request
        headers.update({
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.talktv.cz',
            'referer': 'https://www.talktv.cz/prihlasit',
            'sec-fetch-site': 'same-origin',
            'cache-control': 'max-age=0'
        })

        login_data = {
            'csrf': csrf_token,
            'email': email,
            'password': password
        }

        # Perform login
        log("Submitting login credentials...", xbmc.LOGDEBUG)
        login_response = session.post(
            'https://www.talktv.cz/prihlasit',
            data=login_data,
            headers=headers,
            allow_redirects=True
        )

        log(f"Login response status code: {login_response.status_code}", xbmc.LOGINFO)
        log(f"Login response URL: {login_response.url}", xbmc.LOGDEBUG)

        # Check if login was successful
        soup = BeautifulSoup(login_response.text, 'html.parser')
        user_menu = soup.find('div', class_='popup-account__header-email')

        if user_menu and email in user_menu.text:
            log("Login successful!", xbmc.LOGINFO)
            return session

        log("Login validation failed - checking for error messages", xbmc.LOGERROR)
        # Try to find error message if any
        error_msg = soup.find('div', class_='error-message')
        if error_msg:
            error_text = error_msg.text.strip()
            log(f"Error message found: {error_text}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification('Login Failed', error_text)
        else:
            log("No specific error message found", xbmc.LOGERROR)
            xbmcgui.Dialog().notification('Login Failed', 'Invalid credentials or reCAPTCHA required')

        return False

    except Exception as e:
        log(f"Login process failed", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Login Error', str(e))
        return False

def get_session():
    # Get a requests session with authentication cookie
    session_cookie = _ADDON.getSetting('session_cookie')

    if not session_cookie:
        log("No session cookie configured", xbmc.LOGERROR)
        xbmcgui.Dialog().ok('Session Required', 'Please configure your session cookie in the addon settings.')
        return False

    session = requests.Session()
    log("Creating new session with cookie", xbmc.LOGDEBUG)

    # Set the session cookie
    session.cookies.set('PHPSESSID', session_cookie, domain='www.talktv.cz')

    try:
        # Test the session by requesting the main page
        log("Testing session validity...", xbmc.LOGDEBUG)
        response = session.get('https://www.talktv.cz/videa')

        # Check if we're properly authenticated
        if 'popup-account__header-email' in response.text:
            log("Session cookie valid", xbmc.LOGINFO)
            return session
        else:
            log("Session cookie invalid - authentication failed", xbmc.LOGERROR)
            xbmcgui.Dialog().notification('Auth Error', 'Session cookie is invalid or expired')
            return False

    except Exception as e:
        log("Session validation failed", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Session Error', str(e))
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
            'description': 'Vyhledávání v obsahu [COLOR green]TALK TV[/COLOR]',
            'image': 'search.png'
        },
        {
            'name': 'POSLEDNÍ VIDEA',
            'url': 'https://www.talktv.cz/videa',
            'description': 'Nejnovější videa na [COLOR green]TALK TV[/COLOR]',
            'image': 'latest.png'
        },
        {
            'name': 'POPULÁRNÍ VIDEA',
            'url': 'popular',
            'description': 'Nejsledovanější videa na [COLOR green]TALK TV[/COLOR]\n\n[I](Zatím moc nefunguje, protože plugin dostává z nějakého důvodu špatná data v HTML.)[/I]',
            'image': 'popular.png'
        },
        {
            'name': 'TVŮRCI',
            'url': 'creators',
            'description': 'Všichni tvůrci na [COLOR green]TALK TV[/COLOR] a jejich pořady',
            'image': 'creators.png'
        },
        {
            'name': 'ARCHIV',
            'url': 'archive',
            'description': 'Archiv pořadů [COLOR green]TALK TV[/COLOR] a speciálních sérií',
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

def list_popular(page=None):
    # Get a session for making HTTP requests
    session = get_session()
    if not session:
        return

    try:
        if page:
            # Handle paginated request
            response = session.get(f'https://www.talktv.cz/?pages={page}')
        else:
            # Initial request
            response = session.get('https://www.talktv.cz/')

        soup = BeautifulSoup(response.text, 'html.parser')

        # Specifically look for the homePopular container first
        popular_container = soup.find('div', id='homePopular')
        log(f"popular_container: {popular_container}", xbmc.LOGINFO) # <div id="homePopular" class="list__container is-visible">...</div>
        if not popular_container:
            log("Popular videos container not found", xbmc.LOGERROR)
            return

        # Then find the videoListContainer within homePopular
        video_container = popular_container.find('div', id='videoListContainer')
        if not video_container:
            log("Video list container not found", xbmc.LOGERROR)
            return

        xbmcplugin.setPluginCategory(_HANDLE, 'Populární videa')
        xbmcplugin.setContent(_HANDLE, 'videos')

        # Get all list items in order
        list_items = video_container.find_all('div', class_='list__item')

        for list_item_div in list_items:
            # Get the media link element
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

            duration_seconds = convert_duration_to_seconds(duration_text)

            info_tag = list_item.getVideoInfoTag()
            info_tag.setTitle(title)
            info_tag.setDuration(duration_seconds)
            info_tag.setMediaType('video')

            context_menu = [
                ('Přehrát (zeptat se na kvalitu)',
                 f'RunPlugin({get_url(action="select_quality", video_url=video_url)})')
            ]
            list_item.addContextMenuItems(context_menu)

            url = get_url(action='play', video_url=video_url)
            xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, False)

        # Check for "Load More" button
        load_more = popular_container.find('div', id='butLoadNext')
        if load_more:
            next_page = page + 1 if page else 1
            next_item = xbmcgui.ListItem(label='Načíst další')
            next_item.setArt({
                'icon': get_image_path('foldernext.png'),
                'thumb': get_image_path('foldernext.png')
            })
            url = get_url(action='popular', page=next_page)
            xbmcplugin.addDirectoryItem(_HANDLE, url, next_item, True)

        # End the directory listing
        xbmcplugin.endOfDirectory(_HANDLE)

    except Exception as e:
        log("Error in list_popular", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Error', str(e))

def list_creators():
    # Define the creators and their details
    creators = [
        {
            'name': 'STANDASHOW',
            'url': 'https://www.talktv.cz/standashow',
            'description': 'Výstup z vaší názorové bubliny. Politika, společnost, kauzy a Bruntál. Obsahují minimálně jednoho [COLOR green]Standu[/COLOR].',
            'image': 'show-standashow.jpg'
        },
        {
            'name': 'TECH GUYS',
            'url': 'https://www.talktv.cz/techguys',
            'description': 'Kde unboxingy končí, my začínáme. Apple, kryptoměny, umělá inteligence a pak zase Apple. Každý týden s [COLOR green]Honzou Březinou[/COLOR], [COLOR green]Kicomem[/COLOR] a [COLOR green]Davidem Grudlem[/COLOR].',
            'image': 'show-tech-guys.jpg'
        },
        {
            'name': 'JADRNÁ VĚDA',
            'url': 'https://www.talktv.cz/jadrna-veda',
            'description': 'Pořad, který 9 z 10 diváků nepochopí (a ten desátý je [COLOR green]Leoš Kyša[/COLOR], který to moderuje). Diskuse se skutečnými vědci o skutečné vědě. Pyramidy, kvantová fyzika nebo objevování vesmíru.',
            'image': 'show-jadrna-veda.jpg'
        },
        {
            'name': 'ZA HRANICÍ',
            'url': 'https://www.talktv.cz/za-hranici',
            'description': 'Popelář v Londýně, letuška v Kataru nebo podnikatel v Gambii. Češi žijící v zahraničí a cestovatel [COLOR green]Vladimír Váchal[/COLOR], který ví o cestování (skoro) vše. A na zbytek se nebojí zeptat.',
            'image': 'show-za-hranici.jpg'
        },
        {
            'name': 'MOVIE WITCHES',
            'url': 'https://www.talktv.cz/moviewitches',
            'description': 'Tři holky [COLOR green]Bety[/COLOR] + [COLOR green]Baty[/COLOR] + [COLOR green]Shial[/COLOR] si povídají o filmech, které si to zaslouží. Od vzpomínek přes zajímavosti a shrnutí děje.',
            'image': 'show-movie-witches.jpg'
        },
        {
            'name': 'DESIGN TALK',
            'url': 'https://www.talktv.cz/design-talk',
            'description': '[COLOR green]Lukáš Veverka[/COLOR] a jeho hosté diskutují o věcech, kterým většina diváků vůbec nevěnuje pozornost. Filmy, grafika, motion design i největší faily v dějinách designu a kinematografie.',
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
            'description': 'Minutu po minutě. Den po dni. Důležité události a exkluzívní hosté ve speciálech [COLOR green]STANDASHOW[/COLOR]. Unikátní formát, který kombinuje prvky podcastu, dokumentu a časové reality show.',
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
            'description': 'Nezapomenutelnou atmosféru a komornější povídání, jak na veřejném vysílání. Takový virtuální sraz [COLOR green]STANDASHOW[/COLOR]. Většinou prozradíme spoustu zajímavostí z backstage.',
            'image': 'archiv-hodnoceni-hostu.jpg'
        },
        {
            'name': 'CHARITA',
            'url': 'https://www.talktv.cz/seznam-videi/charita',
            'description': 'Pomáháme. Podcast má být především zábava, ale někde je třeba probrat i vážné téma. A díky skvělé komunitě, která se kolem [COLOR green]STANDASHOW[/COLOR] vytvořila, můžeme pomoct dobré věci.',
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
            'description': 'Herní novinář [COLOR green]Jarda Möwald[/COLOR] a fanynka japonské popkultury [COLOR green]Naomi Adachi[/COLOR]. Diskuse o zajímavostech ze světa her, filmů a seriálů. Celé záznamy pro předplatitele na talktv.cz.',
            'image': 'show-jarda-vs-naomi.jpg'
        },
        {
            'name': 'ZÁKULISÍ TALKU',
            'url': 'https://www.talktv.cz/seznam-videi/zakulisi-talk-tv',
            'description': 'Toto jsme my. Váš/náš :D [COLOR green]TALK[/COLOR]. A toto jsou všechna videa ze zákulisí.',
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
        page = int(params.get('page', 0)) if 'page' in params else None
        list_popular(page)
    elif params['action'] == 'creators':
        list_creators()
    elif params['action'] == 'listing':
        list_videos(params['category_url'])
    elif params['action'] == 'archive':
        list_archive()
    elif params['action'] == 'play':
        quality = params.get('quality', None)
        play_video(params['video_url'], quality)
    elif params['action'] == 'select_quality':
        select_quality(params['video_url'])

if __name__ == '__main__':
    # Entry point for the addon, route the request based on the parameters
    router(sys.argv[2])