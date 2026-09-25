import sys
from urllib.parse import parse_qsl
import xbmc
import xbmcgui
import xbmcplugin
from resources.lib.auth import test_session
from resources.lib.cache import clear_cache
from resources.lib.constants import _ADDON, _HANDLE
from resources.lib.menu import list_menu, list_videos, list_popular, list_top, list_continue, list_creators, list_archive
from resources.lib.search import search, list_search_results
from resources.lib.talknews import list_talknews, show_article, show_news_info
from resources.lib.utils import log, get_ip
from resources.lib.video import play_video, select_quality, skip_yt_part, yt_live, yt_vip_stream, resume_from_web
from resources.lib.monitor import start_monitor, reset_monitor

# Actions that take no parameters. A handful of these are also reachable as
# 'listing' category_urls from the main menu (see constants.MENU_CATEGORIES),
# which is why the listing branch below dispatches through this same table.
_SIMPLE_ACTIONS = {
    'creators': list_creators,
    'archive': list_archive,
    'test_session': test_session,
    'clear_cache': clear_cache,
    'get_ip': get_ip,
    'talknews': list_talknews,
    'reset_monitor': reset_monitor,
    'vip_stream': yt_vip_stream,
    'top': list_top,
    'continue': list_continue,
    'live': yt_live
}

# Actions that take a single video_url parameter and call func(video_url)
_VIDEO_URL_ACTIONS = {
    'select_quality': select_quality,
    'skip_yt_part': skip_yt_part,
    'resume_web': resume_from_web
}

def _end_failed_directory():
    """
    Close the directory as failed so Kodi doesn't sit on a busy spinner.

    Only meaningful when the addon was invoked to build a listing; RunPlugin()
    calls get handle -1, where endOfDirectory() has nothing to close.
    """

    if _HANDLE >= 0:
        xbmcplugin.endOfDirectory(_HANDLE, succeeded=False)

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
        if action in _SIMPLE_ACTIONS:
            _SIMPLE_ACTIONS[action]()
            return

        # The only paginated listing
        if action == 'popular':
            list_popular(int(params.get('page', 1)))
            return

        # Handle TALKNEWS article display
        if action == 'talknews_article':
            article_url = params.get('article_url')
            if not article_url:
                log("Missing article_url parameter", xbmc.LOGERROR)
                _end_failed_directory()
                return
            show_article(article_url)
            return

        # Handle TALKNEWS info display
        if action == 'talknews_info':
            show_news_info(params.get('title', ''), params.get('meta', ''))
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
                _end_failed_directory()
            elif category_url.startswith('http'):
                list_videos(category_url)
            elif category_url in _SIMPLE_ACTIONS:
                # Special menu entries (top, continue, live, talknews) that are
                # listings to the user but have their own dedicated handler
                _SIMPLE_ACTIONS[category_url]()
            else:
                log(f"Invalid category URL: {category_url}", xbmc.LOGERROR)
                xbmcgui.Dialog().notification('Chyba', f'Neplatné URL kategorie: {category_url}')
                _end_failed_directory()
            return

        # Handle video playback
        if action == 'play':
            video_url = params.get('video_url')
            if not video_url:
                log("Missing video_url parameter", xbmc.LOGERROR)
                xbmcplugin.setResolvedUrl(_HANDLE, False, xbmcgui.ListItem())
                return

            start_time = params.get('start_time')
            if start_time is not None:
                try:
                    start_time = int(start_time)
                except ValueError:
                    start_time = None
            play_video(video_url, params.get('quality'), start_time)
            return

        # Actions that take a single video_url parameter and call func(video_url)
        if action in _VIDEO_URL_ACTIONS:
            video_url = params.get('video_url')
            if not video_url:
                log("Missing video_url parameter", xbmc.LOGERROR)
                return
            _VIDEO_URL_ACTIONS[action](video_url)
            return

        # Handle notification (context menu separator trick)
        if action == 'notification':
            xbmcgui.Dialog().notification('TALK', 'Já nic, já jen oddělovač', time=2000)
            return

        # If we get here, the action was not recognized
        log(f"Unrecognized action: {action}", xbmc.LOGERROR)
        _end_failed_directory()

    except Exception as e:
        log(f"Error in router: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Chyba', 'Chyba při zpracování požadavku')
        _end_failed_directory()

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

    # Start TALKNEWS monitor if enabled
    try:
        start_monitor()
    except Exception as e:
        log(f"Failed to start TALKNEWS monitor: {str(e)}", xbmc.LOGERROR)

    # Route the request based on the parameters
    router(sys.argv[2])
