import xbmc
import xbmcgui
import xbmcplugin
from bs4 import BeautifulSoup
from .constants import _HANDLE, _ADDON, ADDON_ID  # type: ignore[unused-import]
from .utils import get_url, get_image_path, log, clean_text, convert_duration_to_seconds, parse_date
from .auth import get_session
from .cache import get_video_details

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
            'description': 'Všichni tvůrci na [COLOR springgreen]TALK TV[/COLOR] a jejich pořady.\n\n[COLOR springgreen]STANDASHOW[/COLOR]\n[COLOR springgreen]TECH GUYS[/COLOR]\n[COLOR springgreen]JADRNÁ VĚDA[/COLOR]\n[COLOR springgreen]ZA HRANICÍ[/COLOR]\n[COLOR springgreen]MOVIE WITCHES[/COLOR]\n[COLOR springgreen]DESIGN TALK[/COLOR]',
            'image': 'creators.png'
        },
        {
            'name': 'ARCHIV',
            'url': 'archive',
            'description': 'Archiv pořadů [COLOR springgreen]TALK TV[/COLOR] a speciálních sérií.\n\n[COLOR springgreen]IRL STREAMY[/COLOR]\n[COLOR springgreen]HODNOCENÍ HOSTŮ[/COLOR]\n[COLOR springgreen]JARDA VS. NAOMI[/COLOR]\na další...',
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

            # Get video details from cache or fetch them
            description, date = get_video_details(session, video_url)

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

            # Get video details from cache or fetch them
            description, date = get_video_details(session, video_url)

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

            # Get video details from cache or fetch them
            description, date = get_video_details(session, video_url)

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

            # Get video details from cache or fetch them
            description, date = get_video_details(session, video_url)

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