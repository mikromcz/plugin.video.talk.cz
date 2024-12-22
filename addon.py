import sys
from urllib.parse import parse_qsl
import xbmc
from resources.lib.auth import test_credentials, test_session
from resources.lib.cache import clear_cache
from resources.lib.constants import _HANDLE
from resources.lib.menu import list_menu, list_videos, list_popular, list_top, list_continue, list_creators, list_archive
from resources.lib.search import search
from resources.lib.utils import log
from resources.lib.video import play_video, select_quality

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
        if 'search_url' in params:
            # If search_url is provided, show previous results
            from resources.lib.search import list_search_results
            list_search_results(params['search_url'])
        else:
            # If no search_url, start new search
            from resources.lib.search import search
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
    elif params['action'] == 'clear_cache':
        clear_cache()

if __name__ == '__main__':
    # Entry point for the addon, route the request based on the parameters
    router(sys.argv[2])
