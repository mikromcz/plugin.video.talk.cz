import xbmc
import xbmcgui
import xbmcplugin
from bs4 import BeautifulSoup
from .auth import require_session
from concurrent.futures import ThreadPoolExecutor
from .cache import get_video_details
from .constants import _HANDLE, MENU_CATEGORIES, CREATOR_CATEGORIES, ARCHIVE_CATEGORIES
from .utils import get_url, get_image_path, log, normalize_title, convert_duration_to_seconds, parse_date, get_category_name, clean_url, get_creator_name_from_coloring, get_creator_cast, get_creator_url, get_creator_clearlogo

# Category URLs that render their whole contents in one HTML page: the archive's
# "seznam-videi" lists hold a fixed number of videos, and the "Ostatní" filter is
# not paginated either. Offering a next page on these always lands on an empty
# listing, so it is suppressed.
_UNPAGINATED_URL_MARKERS = ('/seznam-videi/', 'filter=ostatni')

# Common headers for TALK.cz API requests
_API_HEADERS = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://www.talktv.cz/'
}

def _add_next_page_item(url):
    """
    Add the shared "next page" directory item pointing at the given URL.
    Used by every paginated listing so the label and icon stay identical.

    Args:
        url (str): Plugin URL the item navigates to.
    """

    image_path = get_image_path('fa-folder-next-solid-full.png')
    next_item = xbmcgui.ListItem(label='Další strana')
    next_item.setArt({
        'icon': image_path,
        'thumb': image_path
    })
    xbmcplugin.addDirectoryItem(_HANDLE, url, next_item, isFolder=True)

def _list_static_categories(categories, category_title, url_builder, context_menu_builder=None):
    """
    Build a simple folder listing from a static category list (constants.py).
    Shared by list_menu, list_creators, and list_archive.

    Args:
        categories (list): List of category dicts (name/description/image/url).
        category_title (str): Plugin category label, or None to skip setting it.
        url_builder (callable): category -> destination URL for the directory item.
        context_menu_builder (callable): Optional category -> context menu list.
    """

    for category in categories:
        list_item = xbmcgui.ListItem(label=category['name'])
        image_path = get_image_path(category['image'])

        list_item.setArt({
            'thumb': image_path,
            'icon': image_path
        })

        info_tag = list_item.getVideoInfoTag()
        info_tag.setPlot(category['description'])
        info_tag.setTitle(category['name'])
        info_tag.setStudios(["TALK"])
        info_tag.setCountries(["Česká Republika"])
        info_tag.setGenres(['Directory'])

        if context_menu_builder:
            context_menu = context_menu_builder(category)
            if context_menu:
                list_item.addContextMenuItems(context_menu)

        url = url_builder(category)
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, isFolder=True)

    if category_title:
        xbmcplugin.setPluginCategory(_HANDLE, category_title)
    xbmcplugin.setContent(_HANDLE, 'files')
    xbmcplugin.endOfDirectory(_HANDLE)

def list_menu():
    """
    Lists the main menu categories available in the addon
    """

    def build_url(category):
        # A handful of top-level categories route to their own dedicated action
        special_actions = {'search', 'popular', 'creators', 'archive'}
        if category['url'] in special_actions:
            return get_url(action=category['url'])
        return get_url(action='listing', category_url=category['url'])

    _list_static_categories(MENU_CATEGORIES, None, build_url)

def list_creators():
    """
    Lists the creators and their content available in the addon
    """

    def build_context_menu(creator):
        yt_channel_id = creator.get('yt_channel_id')
        if not yt_channel_id:
            return None
        yt_url = f'plugin://plugin.video.youtube/channel/{yt_channel_id}'
        return [('Přejít na YouTube kanál tvůrce', f'Container.Update({yt_url})')]

    _list_static_categories(
        CREATOR_CATEGORIES, 'Tvůrci',
        lambda creator: get_url(action='listing', category_url=creator['url']),
        build_context_menu
    )

def list_archive():
    """
    Lists the archive items available in the addon
    """

    _list_static_categories(
        ARCHIVE_CATEGORIES, 'Archiv',
        lambda item: get_url(action='listing', category_url=item['url'])
    )

def list_videos(category_url):
    """
    Lists videos from the given category URL
    Handles pagination and displays video items with their details.

    Args:
        category_url (str): The URL of the category to list videos from.
    """

    # Get a session for making HTTP requests
    session = require_session()
    if not session:
        xbmcplugin.endOfDirectory(_HANDLE, succeeded=False)
        return

    try:
        log(f"Listing videos for category: {category_url}", xbmc.LOGINFO)
        is_paginated = 'page=' in category_url

        # Determine if we should show creator names
        # Show creator names only for the main videos section
        show_creator = 'talktv.cz/videa' in category_url
        log(f"Show creator names: {show_creator} for URL: {category_url}", xbmc.LOGINFO)

        # Make the HTTP GET request
        response = session.get(category_url, timeout=10)
        if response.status_code != 200:
            log(f"Failed to fetch category page: {response.status_code}", xbmc.LOGERROR)
            xbmcplugin.endOfDirectory(_HANDLE, succeeded=False)
            return

        video_items = []
        has_next = False
        page_number = 1

        if is_paginated:
            # Extract current page number from the URL
            try:
                page_number = int(category_url.split('page=')[1].split('&')[0])
            except (IndexError, ValueError):
                page_number = 1

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
                    xbmcplugin.endOfDirectory(_HANDLE, succeeded=False)
                    return
            except Exception as e:
                log(f"Failed to parse JSON response for paginated content: {str(e)}", xbmc.LOGERROR)
                xbmcplugin.endOfDirectory(_HANDLE, succeeded=False)
                return
        else:
            log("Processing regular HTML response", xbmc.LOGDEBUG)
            # Parse the HTML response
            soup = BeautifulSoup(response.text, 'html.parser')
            container = soup.find('div', id='videoListContainer')
            if container:
                video_items = container.find_all('a', class_='media')
                # The HTML first page carries no "is there more" flag (only the
                # JSON pages that follow do), so assume more unless this is a
                # listing we know renders in full (see the check further down)
                has_next = bool(video_items)
                log(f"Found {len(video_items)} videos in container", xbmc.LOGDEBUG)
            else:
                log("Could not find video container in HTML", xbmc.LOGERROR)
                xbmcplugin.endOfDirectory(_HANDLE, succeeded=False)
                return

        # Process video items with creator names only for the main videos section
        add_video_directory_items(video_items, session, show_creator_in_title=show_creator)

        if any(marker in category_url for marker in _UNPAGINATED_URL_MARKERS):
            has_next = False

        if has_next:
            # Calculate next page and construct a clean URL (no query parameters)
            next_page = page_number + 1 if is_paginated else 1
            next_url = f"{clean_url(category_url)}?page={next_page}"

            log(f"Adding next page item: page {next_page}", xbmc.LOGDEBUG)
            _add_next_page_item(get_url(action='listing', category_url=next_url))

        # Set the content type and sort method for the directory
        xbmcplugin.setPluginCategory(_HANDLE, get_category_name(category_url))
        xbmcplugin.setContent(_HANDLE, 'videos')
        xbmcplugin.endOfDirectory(_HANDLE)

    except Exception as e:
        log(f"Error in list_videos: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Chyba', 'Chyba při načítání videi')
        xbmcplugin.endOfDirectory(_HANDLE, succeeded=False)

def _list_home_section(section_key, category_title, auto_resume=False, paginate=False, page=1):
    """
    Fetch a section (c1/c2/c3) from the /srv/videos/home API and list its videos.
    Shared by list_popular, list_top, and list_continue.

    Args:
        section_key (str): Key of the section in the API response ('c1'/'c2'/'c3').
        category_title (str): Plugin category label to show for this listing.
        auto_resume (bool): Whether to auto-set resume point from the web position.
        paginate (bool): Whether to slice the section client-side into pages of 24.
        page (int): Current page number, only used when paginate is True.
    """

    # Get a session for making HTTP requests
    session = require_session()
    if not session:
        xbmcplugin.endOfDirectory(_HANDLE, succeeded=False)
        return

    try:
        api_url = f'https://www.talktv.cz/srv/videos/home?pages={page}' if paginate else 'https://www.talktv.cz/srv/videos/home'
        log(f"Fetching {section_key} videos from API: {api_url}", xbmc.LOGINFO)

        response = session.get(api_url, headers=_API_HEADERS, timeout=10)
        if response.status_code != 200:
            log(f"API request failed: {response.status_code}", xbmc.LOGERROR)
            xbmcplugin.endOfDirectory(_HANDLE, succeeded=False)
            return

        data = response.json()
        if section_key not in data:
            log(f"No {section_key} section in response", xbmc.LOGERROR)
            xbmcplugin.endOfDirectory(_HANDLE, succeeded=False)
            return

        soup = BeautifulSoup(data[section_key], 'html.parser')
        all_items = soup.find_all('div', class_='list__item')

        has_next_page = False
        if paginate:
            ITEMS_PER_PAGE = 24
            total_items = len(all_items)
            start_idx = (page - 1) * ITEMS_PER_PAGE
            end_idx = start_idx + ITEMS_PER_PAGE
            list_item_divs = all_items[start_idx:end_idx]
            # The API is cumulative (?pages=N returns everything up to N), so a
            # full page may or may not have more behind it - but a partial page
            # definitely does not, which is what this rules out
            has_next_page = len(list_item_divs) == ITEMS_PER_PAGE
            log(f"Page {page}: Processing items {start_idx} to {end_idx} out of {total_items}, has next: {has_next_page}", xbmc.LOGDEBUG)
        else:
            list_item_divs = all_items

        video_items = [a for div in list_item_divs if (a := div.find('a', class_='media'))]
        add_video_directory_items(video_items, session, auto_resume=auto_resume)

        if has_next_page:  # Add next page only if there are more items available
            _add_next_page_item(get_url(action='popular', page=page + 1))

        # Set the plugin category and content type
        xbmcplugin.setPluginCategory(_HANDLE, category_title)
        xbmcplugin.setContent(_HANDLE, 'videos')
        xbmcplugin.endOfDirectory(_HANDLE)

    except Exception as e:
        log(f"Error listing {section_key}: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Chyba', str(e))
        xbmcplugin.endOfDirectory(_HANDLE, succeeded=False)

def list_popular(page=1):
    """
    Lists the most popular videos, paginated client-side with 24 items per page.
    c2 in https://www.talktv.cz/srv/videos/home
    """
    _list_home_section('c2', 'Populární videa', paginate=True, page=page)

def list_top():
    """
    Lists the top videos (no pagination as there are only 16 items).
    c3 in https://www.talktv.cz/srv/videos/home
    """
    _list_home_section('c3', 'Nejlepší videa')

def list_continue():
    """
    Lists the videos that the user can continue watching (no pagination).
    c1 in https://www.talktv.cz/srv/videos/home
    """
    _list_home_section('c1', 'Pokračovat v přehrávání', auto_resume=True)

def process_video_item(item, session, show_creator_in_title=True, auto_resume=False):
    """
    Helper function to process a video item and create a ListItem.

    This function extracts the title, thumbnail, and other details from the item.
    It also sets the context menu for the item and returns the ListItem and video URL.

    Args:
        item (BeautifulSoup object): The video item to process.
        session (requests.Session): The session for making HTTP requests.
        show_creator_in_title (bool): Whether to show the creator in the title.
        auto_resume (bool): Whether to automatically set resume point from web (for continue watching).
    """

    title_element = item.find('div', class_='media__name')
    if not title_element or not title_element.p:
        return None

    # Get coloring class from the media element itself
    coloring_class = next((c for c in item.get('class', []) if 'coloring-' in c), None)

    # Get creator name from coloring class
    creator_name = get_creator_name_from_coloring(coloring_class)
    creator_label = f"[COLOR limegreen]{creator_name}[/COLOR]"

    # Get basic video info
    raw_title = normalize_title(title_element.p.text)

    # Show the creator alongside the title only where the caller asked for it
    display_title = f"{creator_label} • {raw_title}" if show_creator_in_title and creator_name else raw_title

    video_url = clean_url('https://www.talktv.cz' + item['href'])

    # Get duration
    duration_element = item.find('p', class_='duration')
    duration_text = duration_element.text.strip() if duration_element else "0:00"

    # Create list item
    list_item = xbmcgui.ListItem(display_title)
    list_item.setProperty('IsPlayable', 'true')
    list_item.setIsFolder(False)

    # Set thumbnail (lazy-loaded images keep the real URL in data-src)
    img_element = item.find('img')
    thumbnail = (img_element.get('data-src') or img_element.get('src', '')) if img_element else ''

    # Set art for the list item
    list_item.setArt({
        'thumb': thumbnail,
        'icon': thumbnail,
        'clearlogo': get_creator_clearlogo(creator_name)
    })

    # Get additional details (a single fetch also covers the web resume position
    # when auto_resume is enabled, instead of fetching the same page twice)
    description, date, resume_position = get_video_details(session, video_url, need_resume=auto_resume)
    duration_seconds = convert_duration_to_seconds(duration_text)

    # Set video info
    info_tag = list_item.getVideoInfoTag()
    info_tag.setTitle(raw_title)
    info_tag.setTvShowTitle(creator_label)
    info_tag.setPlot(description)
    info_tag.setDuration(duration_seconds)
    info_tag.setMediaType('episode')
    info_tag.setStudios(["TALK"])
    info_tag.setCountries(["Česká Republika"])
    info_tag.setGenres(['Podcast', 'Talk Show'])
    info_tag.setTags(['Czech', 'Interview', 'TALKTV', 'Bruntal'])

    # Extract year from date if available
    parsed_date = parse_date(date) if date else ''
    if parsed_date:
        info_tag.setPremiered(parsed_date)
        try:
            info_tag.setYear(int(parsed_date.split('-')[0]))
        except (ValueError, IndexError):
            pass

    # Get cast information
    cast = get_creator_cast(creator_name, title=raw_title)
    if cast:
        try:
            info_tag.setCast(cast)
            #log(f"Cast set successfully for {creator_name}: {[a.getAsString() for a in cast]}", xbmc.LOGINFO)
        except Exception as e:
            log(f"Error setting cast for {creator_name}: {str(e)}", xbmc.LOGERROR)

    # Add useful properties for Kodi integration
    # Note: TotalTime is deprecated - using setResumePoint() instead
    #
    # Only stamp a resume point when we actually have one from the web (that is,
    # in "Pokračovat v přehrávání", the only listing fetched with need_resume).
    # Calling setResumePoint(0, ...) on every item overwrites the resume position
    # Kodi tracks by itself, which hides the partially-watched icon and makes
    # playback restart from the beginning.
    if resume_position > 0:
        log(f"Setting web resume position to {resume_position}s for {video_url}", xbmc.LOGINFO)
        info_tag.setResumePoint(resume_position, duration_seconds)  # Resume from position, with total duration

    list_item.setProperty('Creator', creator_name)
    list_item.setProperty('Duration', duration_text)  # Original format like "1h42m"

    # Set unique ID for the video
    video_id = video_url.split('/')[-1]  # Extract from URL
    info_tag.setUniqueIDs({'talktv': video_id}, 'talktv')

    # Add context menu
    context_menu = [
        ('Přeskočit YouTube část', f'RunPlugin({get_url(action="skip_yt_part", video_url=video_url)})'),
        ('Pokračovat od pozice na webu', f'RunPlugin({get_url(action="resume_web", video_url=video_url)})'),
        ('Přehrát (zeptat se na kvalitu)', f'RunPlugin({get_url(action="select_quality", video_url=video_url)})'),
        ('---', f'RunPlugin({get_url(action="notification")})')
    ]

    # Add creator navigation option if showing creator in title
    if show_creator_in_title and creator_name:
        creator_url = get_creator_url(creator_name)
        if creator_url:
            context_menu.insert(0,
                ('Přejít na tvůrce', f'Container.Update({get_url(action="listing", category_url=creator_url)})')
            )

    list_item.addContextMenuItems(context_menu)

    return list_item, video_url

def add_video_directory_items(video_items, session, show_creator_in_title=True, auto_resume=False):
    """
    Process a batch of <a class="media"> items and add them to the Kodi directory.

    Fetching each video's detail page over HTTP is the slow part of building a
    listing, so items are processed concurrently via a thread pool instead of
    one HTTP request at a time. Results are added in the original order.

    Args:
        video_items (list): BeautifulSoup <a class="media"> elements to process.
        session (requests.Session): The session for making HTTP requests.
        show_creator_in_title (bool): Whether to show the creator in the title.
        auto_resume (bool): Whether to auto-set resume point from the web position.
    """

    if not video_items:
        return

    results = [None] * len(video_items)

    def _process(index, item):
        try:
            results[index] = process_video_item(item, session, show_creator_in_title, auto_resume)
        except Exception as e:
            log(f"Error processing video item: {str(e)}", xbmc.LOGERROR)

    with ThreadPoolExecutor(max_workers=min(6, len(video_items))) as executor:
        executor.map(_process, range(len(video_items)), video_items)

    for result in results:
        if result:
            list_item, video_url = result
            url = get_url(action='play', video_url=video_url)
            xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, isFolder=False)