import sys
from urllib.parse import parse_qsl
import xbmc
import xbmcgui
from resources.lib.auth import test_credentials, test_session
from resources.lib.cache import clear_cache
from resources.lib.constants import _HANDLE, _ADDON
from resources.lib.menu import list_menu, list_videos, list_popular, list_top, list_continue, list_creators, list_archive
from resources.lib.search import search, list_search_results
from resources.lib.talknews import list_talknews, show_article, show_news_info
from resources.lib.utils import log, get_ip
from resources.lib.video import play_video, select_quality, skip_yt_part, yt_live, resume_from_web

def router(paramstring):
    """
    Routes the request based on the provided query parameters

    Args:
        paramstring (str): The URL query parameters
    """

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
        if action in ['creators', 'archive', 'test_credentials', 'test_session', 'clear_cache', 'get_ip', 'talknews']:
            action_map = {
                'creators': list_creators,
                'archive': list_archive,
                'test_credentials': test_credentials,
                'test_session': test_session,
                'clear_cache': clear_cache,
                'get_ip': get_ip,
                'talknews': list_talknews
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

        # Handle TALKNEWS article display
        if action == 'talknews_article':
            article_url = params.get('article_url')
            if not article_url:
                log("Missing article_url parameter", xbmc.LOGERROR)
                return
            show_article(article_url)
            return

        # Handle TALKNEWS info display
        if action == 'talknews_info':
            title = params.get('title', '')
            meta = params.get('meta', '')
            show_news_info(title, meta)
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
            elif category_url == 'talknews':
                list_talknews()
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

        # Handle resuming video from web
        if action == 'resume_web':
            video_url = params.get('video_url')
            if not video_url:
                log("Missing video_url parameter", xbmc.LOGERROR)
                return
            resume_from_web(video_url)
            return

        # Handle notification
        if params['action'] == 'notification':
            xbmcgui.Dialog().notification('TALK', 'Já nic, já jen oddělovač', time=2000)

        # If we get here, the action was not recognized
        log(f"Unrecognized action: {action}", xbmc.LOGERROR)

    except Exception as e:
        log(f"Error in router: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Chyba', str(e))

if __name__ == '__main__':
    """
    Entry point for the addon, route the request based on the parameters

    The addon can be started with the following parameters:
    - action: The action to perform
    - page: The page number to display
    - category_url: The URL of the category to list
    - video_url: The URL of the video to play
    - quality: The quality of the video to play
    - search_url: The URL to search
    """

    # Only import and start web server if enabled
    if _ADDON.getSettingBool('enable_config_page'):
        try:
            import threading
            from resources.lib.webconfig import start_server

            server_thread = threading.Thread(target=start_server)
            server_thread.daemon = True
            server_thread.start()
            log("Config web server thread started", xbmc.LOGINFO)
        except Exception as e:
            log(f"Failed to start config web server: {str(e)}", xbmc.LOGERROR)

    # Route the request based on the parameters
    router(sys.argv[2])
