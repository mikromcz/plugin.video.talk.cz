import sys
from urllib.parse import parse_qsl
import xbmc
import xbmcgui
from resources.lib.auth import test_credentials, test_session
from resources.lib.cache import clear_cache
from resources.lib.constants import _HANDLE
from resources.lib.menu import list_menu, list_videos, list_popular, list_top, list_continue, list_creators, list_archive
from resources.lib.search import search
from resources.lib.utils import log
from resources.lib.video import play_video, select_quality, skip_yt_part, yt_live

def router(paramstring):
    # Routes the request based on the provided query parameters

    # Import search functionality at the module level
    from resources.lib.search import search, list_search_results

    try:
        # Parse the query parameters from the URL
        params = dict(parse_qsl(paramstring[1:]))
        log(f"Router received params: {params}", xbmc.LOGINFO)

        if not params:
            # If no parameters, list the main menu
            list_menu()
            return

        # Get the action from params
        action = params.get('action', '')

        # Simple actions that don't require additional parameters
        if action in ['creators', 'archive', 'test_credentials', 'test_session', 'clear_cache']:
            action_map = {
                'creators': list_creators,
                'archive': list_archive,
                'test_credentials': test_credentials,
                'test_session': test_session,
                'clear_cache': clear_cache
            }
            action_map[action]()
            return

        # Actions that might use page parameter
        if action in ['popular']:
            page = int(params.get('page', 1))
            list_popular(page)
            return

        # Actions that don't use page parameter anymore
        if action in ['top', 'continue']:
            action_map = {
                'top': list_top,
                'continue': list_continue
            }
            action_map[action]()
            return

        # Handle search functionality
        if action == 'search':
            if 'search_url' in params:
                list_search_results(params['search_url'])
            else:
                search()
            return

        # Handle video listing
        if action == 'listing':
            category_url = params.get('category_url', '')
            if not category_url:
                log("Missing category_url parameter", xbmc.LOGERROR)
                return

            # Handle special category URLs
            if category_url == 'top':
                list_top()
                return
            elif category_url == 'continue':
                list_continue()
                return
            elif category_url == 'live':
                yt_live()
                return
            elif category_url.startswith('http'):
                list_videos(category_url)
                return
            else:
                log(f"Invalid category URL: {category_url}", xbmc.LOGERROR)
                xbmcgui.Dialog().notification('Chyba', f'Neplatné URL kategorie: {category_url}')
                return

        # Handle video playback
        if action == 'play':
            video_url = params.get('video_url')
            if not video_url:
                log("Missing video_url parameter", xbmc.LOGERROR)
                return
            quality = params.get('quality')
            play_video(video_url, quality)
            return

        # Handle video quality selection
        if action == 'select_quality':
            video_url = params.get('video_url')
            if not video_url:
                log("Missing video_url parameter", xbmc.LOGERROR)
                return
            select_quality(video_url)
            return

        # Handle YouTube part skipping
        if action == 'skip_yt_part':
            video_url = params.get('video_url')
            if not video_url:
                log("Missing video_url parameter", xbmc.LOGERROR)
                return
            skip_yt_part(video_url)
            return

        # If we get here, the action was not recognized
        log(f"Unrecognized action: {action}", xbmc.LOGERROR)

    except Exception as e:
        log(f"Error in router: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Chyba', str(e))

if __name__ == '__main__':
    # Entry point for the addon, route the request based on the parameters

    router(sys.argv[2])
