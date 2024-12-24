import xbmc
import xbmcgui
import xbmcplugin
from bs4 import BeautifulSoup
from .constants import _HANDLE, _ADDON, ADDON_ID, MENU_CATEGORIES, CREATOR_CATEGORIES, ARCHIVE_CATEGORIES
from .utils import get_url, get_image_path, log, clean_text, convert_duration_to_seconds, parse_date, get_category_name, clean_url
from .auth import get_session
from .cache import get_video_details

def list_menu():
    # Lists the main menu categories available in the addon

    for category in MENU_CATEGORIES:
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

    # Set the plugin category and content type
    xbmcplugin.setPluginCategory(_HANDLE, 'Hlavní menu') # Kategorie
    xbmcplugin.setContent(_HANDLE, 'files')
    xbmcplugin.endOfDirectory(_HANDLE)

def list_creators():
    # Lists the creators and their content available in the addon

    for creator in CREATOR_CATEGORIES:
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

    # Set the plugin category and content type
    xbmcplugin.setPluginCategory(_HANDLE, 'Tvůrci') # Tvůrci
    xbmcplugin.setContent(_HANDLE, 'files')
    xbmcplugin.endOfDirectory(_HANDLE)

def list_archive():
    # Lists the archive items available in the addon

    for item in ARCHIVE_CATEGORIES:
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

    # Set the plugin category and content type
    xbmcplugin.setPluginCategory(_HANDLE, 'Archiv') # Archiv
    xbmcplugin.setContent(_HANDLE, 'files')
    xbmcplugin.endOfDirectory(_HANDLE)

def list_videos(category_url):
    # Lists videos from the given category URL

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

        # Extract current page number from URL if present
        page_number = 1
        if is_paginated:
            try:
                page_param = category_url.split('page=')[1].split('&')[0]
                page_number = int(page_param)
            except (IndexError, ValueError):
                page_number = 1

        if is_paginated:
            log(f"Processing paginated response for page {page_number}", xbmc.LOGDEBUG)
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
            video_url = clean_url('https://www.talktv.cz' + item['href'])

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

            list_item.setLabel2(duration_text)

            # Add context menu items
            context_menu = [
                ('Přehrát (zeptat se na kvalitu)', f'RunPlugin({get_url(action="select_quality", video_url=video_url)})'), # Přehrát (zeptat se na kvalitu)
                ('Přeskočit YouTube část', f'RunPlugin({get_url(action="skip_yt_part", video_url=video_url)})') # Přeskočit YouTube část
            ]
            list_item.addContextMenuItems(context_menu)

            # Add the directory item to the Kodi plugin
            url = get_url(action='play', video_url=video_url)
            xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, False)

        if has_next:
            # Get base URL without any query parameters
            base_url = original_url.split('?')[0]

            # Calculate next page and construct clean URL
            next_page = page_number + 1 if is_paginated else 1
            next_url = f"{base_url}?page={next_page}"

            log(f"Adding next page item: page {next_page}", xbmc.LOGDEBUG)
            next_item = xbmcgui.ListItem(label='Další strana') # Další strana
            next_item.setArt({
                'icon': get_image_path('foldernext.png'),
                'thumb': get_image_path('foldernext.png')
            })
            xbmcplugin.addDirectoryItem(_HANDLE, get_url(action='listing', category_url=next_url), next_item, True)

        # Set the content type and sort method for the directory
        xbmcplugin.setPluginCategory(_HANDLE, get_category_name(category_url)) # Set the plugin category based on the URL or page content
        xbmcplugin.setContent(_HANDLE, 'videos')
        xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.endOfDirectory(_HANDLE)

    except Exception as e:
        log("Error in list_videos", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Chyba', str(e))

def list_popular(page=1):
    # Lists the most popular videos, paginated with 24 items per page (24, 48, 72, ...)
    # C2 in https://www.talktv.cz/srv/videos/home

    # Get a session for making HTTP requests
    session = get_session()
    if not session:
        return

    try:
        # Construct API URL with page parameter
        api_url = f'https://www.talktv.cz/srv/videos/home?pages={page}'
        log(f"Fetching popular videos from API: {api_url}", xbmc.LOGINFO)

        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://www.talktv.cz/'
        }

        response = session.get(api_url, headers=headers)
        if response.status_code != 200:
            log(f"API request failed: {response.status_code}", xbmc.LOGERROR)
            return

        data = response.json()
        if 'c2' not in data:
            log("No popular videos section in response", xbmc.LOGERROR)
            return

        # Get all items
        soup = BeautifulSoup(data['c2'], 'html.parser')
        all_items = soup.find_all('div', class_='list__item')
        total_items = len(all_items)

        # Calculate slice indices for current page
        ITEMS_PER_PAGE = 24
        start_idx = (page - 1) * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE

        # Get only items for current page
        list_items = all_items[start_idx:end_idx]

        # We have a next page if we have any items beyond our current slice
        has_next_page = total_items > start_idx + len(list_items) - 1 # -1 otherwise there is no "Next page"

        log(f"Page {page}: Processing items {start_idx} to {end_idx}, total items: {total_items}, has next: {has_next_page}", xbmc.LOGDEBUG)
        log(f"Page {page}: Processing items {start_idx} to {end_idx} out of {len(all_items)}", xbmc.LOGDEBUG)

        for list_item_div in list_items:
            item = list_item_div.find('a', class_='media')
            if not item:
                continue

            title_element = item.find('div', class_='media__name')
            if not title_element or not title_element.p:
                continue

            title = clean_text(title_element.p.text)
            video_url = clean_url('https://www.talktv.cz' + item['href'])

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

            description, date = get_video_details(session, video_url)
            duration_seconds = convert_duration_to_seconds(duration_text)

            info_tag = list_item.getVideoInfoTag()
            info_tag.setTitle(title)
            info_tag.setPlot(description)
            info_tag.setDuration(duration_seconds)
            info_tag.setMediaType('video')

            if date:
                info_tag.setPremiered(parse_date(date))

            context_menu = [
                ('Přehrát (zeptat se na kvalitu)', f'RunPlugin({get_url(action="select_quality", video_url=video_url)})'), # Přehrát (zeptat se na kvalitu)
                ('Přeskočit YouTube část', f'RunPlugin({get_url(action="skip_yt_part", video_url=video_url)})') # Přeskočit YouTube část
            ]
            list_item.addContextMenuItems(context_menu)

            url = get_url(action='play', video_url=video_url)
            xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, False)

        if has_next_page:  # Add next page only if there are more items available
            next_page = page + 1
            next_item = xbmcgui.ListItem(label='Další stránka') # Další stránka
            next_item.setArt({
                'icon': get_image_path('foldernext.png'),
                'thumb': get_image_path('foldernext.png')
            })
            url = get_url(action='popular', page=next_page)
            xbmcplugin.addDirectoryItem(_HANDLE, url, next_item, True)

        # Set the plugin category and content type
        xbmcplugin.setPluginCategory(_HANDLE, 'Populární videa') # Populární videa
        xbmcplugin.setContent(_HANDLE, 'videos')
        xbmcplugin.endOfDirectory(_HANDLE)

    except Exception as e:
        log("Error in list_popular", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Chyba', str(e))

def list_top():
    # Lists the top videos (no pagination as there are only 16 items)
    # C3 in https://www.talktv.cz/srv/videos/home

    # Get a session for making HTTP requests
    session = get_session()
    if not session:
        return

    try:
        api_url = 'https://www.talktv.cz/srv/videos/home'
        log(f"Fetching top videos from API: {api_url}", xbmc.LOGINFO)

        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://www.talktv.cz/'
        }

        response = session.get(api_url, headers=headers)
        if response.status_code != 200:
            log(f"API request failed: {response.status_code}", xbmc.LOGERROR)
            return

        data = response.json()
        if 'c3' not in data:
            log("No top videos section in response", xbmc.LOGERROR)
            return

        # Get c3 items
        soup = BeautifulSoup(data['c3'], 'html.parser')
        list_items = soup.find_all('div', class_='list__item')
        for list_item_div in list_items:
            item = list_item_div.find('a', class_='media')
            if not item:
                continue

            title_element = item.find('div', class_='media__name')
            if not title_element or not title_element.p:
                continue

            title = clean_text(title_element.p.text)
            video_url = clean_url('https://www.talktv.cz' + item['href'])

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

            description, date = get_video_details(session, video_url)
            duration_seconds = convert_duration_to_seconds(duration_text)

            info_tag = list_item.getVideoInfoTag()
            info_tag.setTitle(title)
            info_tag.setPlot(description)
            info_tag.setDuration(duration_seconds)
            info_tag.setMediaType('video')

            if date:
                info_tag.setPremiered(parse_date(date))

            context_menu = [
                ('Přehrát (zeptat se na kvalitu)', f'RunPlugin({get_url(action="select_quality", video_url=video_url)})'), # Přehrát (zeptat se na kvalitu)
                ('Přeskočit YouTube část', f'RunPlugin({get_url(action="skip_yt_part", video_url=video_url)})') # Přeskočit YouTube část
            ]
            list_item.addContextMenuItems(context_menu)

            url = get_url(action='play', video_url=video_url)
            xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, False)

        # Set the plugin category and content type
        xbmcplugin.setPluginCategory(_HANDLE, 'Nejlepší videa') # Nejlepší videa
        xbmcplugin.setContent(_HANDLE, 'videos')
        xbmcplugin.endOfDirectory(_HANDLE)

    except Exception as e:
        log("Error in list_top", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Chyba', str(e))

def list_continue():
    # Lists the videos that the user can continue watching (no pagination)
    # C1 in https://www.talktv.cz/srv/videos/home

    # Get a session for making HTTP requests
    session = get_session()
    if not session:
        return

    try:
        api_url = 'https://www.talktv.cz/srv/videos/home'
        log(f"Fetching continue watching videos from API: {api_url}", xbmc.LOGINFO)

        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://www.talktv.cz/'
        }

        response = session.get(api_url, headers=headers)
        if response.status_code != 200:
            log(f"API request failed: {response.status_code}", xbmc.LOGERROR)
            return

        data = response.json()
        if 'c1' not in data:
            log("No continue watching section in response", xbmc.LOGERROR)
            return

        # Get c1 items
        soup = BeautifulSoup(data['c1'], 'html.parser')
        list_items = soup.find_all('div', class_='list__item')
        for list_item_div in list_items:
            item = list_item_div.find('a', class_='media')
            if not item:
                continue

            title_element = item.find('div', class_='media__name')
            if not title_element or not title_element.p:
                continue

            title = clean_text(title_element.p.text)
            video_url = clean_url('https://www.talktv.cz' + item['href'])

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

            description, date = get_video_details(session, video_url)
            duration_seconds = convert_duration_to_seconds(duration_text)

            info_tag = list_item.getVideoInfoTag()
            info_tag.setTitle(title)
            info_tag.setPlot(description)
            info_tag.setDuration(duration_seconds)
            info_tag.setMediaType('video')

            if date:
                info_tag.setPremiered(parse_date(date))

            context_menu = [
                ('Přehrát (zeptat se na kvalitu)', f'RunPlugin({get_url(action="select_quality", video_url=video_url)})'), # Přehrát (zeptat se na kvalitu)
                ('Přeskočit YouTube část', f'RunPlugin({get_url(action="skip_yt_part", video_url=video_url)})') # Přeskočit YouTube část
            ]
            list_item.addContextMenuItems(context_menu)

            url = get_url(action='play', video_url=video_url)
            xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, False)

        # Set the plugin category and content type
        xbmcplugin.setPluginCategory(_HANDLE, 'Pokračovat v přehrávání') # Pokračovat v přehrávání
        xbmcplugin.setContent(_HANDLE, 'videos')
        xbmcplugin.endOfDirectory(_HANDLE)

    except Exception as e:
        log("Error in list_continue", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Chyba', str(e))