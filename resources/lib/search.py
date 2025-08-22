import xbmc
import xbmcgui
import xbmcplugin
from urllib.parse import quote
from bs4 import BeautifulSoup
from .auth import get_session, is_cookie_failed
from .cache import get_video_details
from .constants import _HANDLE
from .menu import process_video_item
from .utils import get_url, log, clean_text, convert_duration_to_seconds, parse_date, clean_url

def search():
    """
    Prompts the user to enter a search string and lists the search results
    """

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
    """
    Lists the search results from the given search URL

    Args:
        search_url (str): The URL to search for videos

    Example search URL:
        https://www.talktv.cz/hledani?q=terminator
    """

    # Get a session for making HTTP requests
    session = get_session()
    if not session:
        log("Failed to get valid session", xbmc.LOGERROR)
        if is_cookie_failed():
            xbmcgui.Dialog().ok('Chyba autentizace', 'Neplatná nebo prošlá session cookie.\n\nProsím aktualizujte cookie v nastavení doplňku.')
        xbmcplugin.endOfDirectory(_HANDLE, succeeded=False)
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
            # Process video item with creator names
            result = process_video_item(item, session)
            if result:
                list_item, video_url = result
                url = get_url(action='play', video_url=video_url, search_url=search_url)
                xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, False)

        # Set the plugin category and content type
        xbmcplugin.setPluginCategory(_HANDLE, 'Výsledky hledání') # Výsledky hledání
        xbmcplugin.setContent(_HANDLE, 'videos')
        xbmcplugin.endOfDirectory(_HANDLE)

    except Exception as e:
        log(f"Error in list_search_results: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Chyba', 'Chyba při vyhledávání')