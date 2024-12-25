import xbmc
import xbmcgui
import xbmcplugin
from urllib.parse import quote
from bs4 import BeautifulSoup
from .constants import _HANDLE
from .utils import get_url, log, clean_text, convert_duration_to_seconds, parse_date, clean_url
from .auth import get_session
from .cache import get_video_details

def search():
    # Prompts the user to enter a search string and lists the search results

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
    else:
        # User cancelled the search, return to main menu
        from .menu import list_menu
        list_menu()

def list_search_results(search_url):
    # Lists the search results from the given search URL

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

        for item in video_items:
            # Get the title of the video
            title_element = item.find('div', class_='media__name')
            if not title_element or not title_element.p:
                continue

            title = clean_text(title_element.p.text)
            video_url = clean_url('https://www.talktv.cz' + item['href'])

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
                ('Přehrát (zeptat se na kvalitu)', f'RunPlugin({get_url(action="select_quality", video_url=video_url, search_url=search_url)})')
            ]
            list_item.addContextMenuItems(context_menu)

            # Add the directory item to the Kodi plugin with search_url included
            url = get_url(action='play', video_url=video_url, search_url=search_url)
            xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, False)

        # Set the plugin category and content type
        xbmcplugin.setPluginCategory(_HANDLE, 'Výsledky hledání')
        xbmcplugin.setContent(_HANDLE, 'videos')
        xbmcplugin.endOfDirectory(_HANDLE)

    except Exception as e:
        log("Error in list_search_results", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Chyba', str(e))