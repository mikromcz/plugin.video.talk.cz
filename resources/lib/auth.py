import time
import requests
import xbmc
import xbmcgui
from .constants import _ADDON
from .utils import log

# Session caching
_session_cache = {
    'session': None,
    'validated_at': 0,
    'ttl': 3600,  # 1 hour cache
    'failed_cookie': None,  # Track failed cookies to show error each time
    'network_error': False  # Track if last failure was network-related (not cookie)
}

def get_session():
    """
    Get a requests session with authentication cookie.
    Uses caching to avoid repeated validation requests.

    Returns:
        requests.Session: A session object with authentication cookie set
        False: Authentication failed (invalid cookie or network error)
    """
    global _session_cache
    
    current_time = time.time()
    session_cookie = _ADDON.getSetting('session_cookie')

    # Check if this is the same cookie that failed before
    if (session_cookie and session_cookie == _session_cache['failed_cookie']):
        log("Using previously failed cookie", xbmc.LOGDEBUG)
        return False

    # Check if we have a valid cached session
    if (_session_cache['session'] and 
        _session_cache['validated_at'] > 0 and 
        current_time - _session_cache['validated_at'] < _session_cache['ttl'] and
        session_cookie):
        log("Using cached session", xbmc.LOGDEBUG)
        return _session_cache['session']

    if not session_cookie:
        log("No session cookie configured", xbmc.LOGWARNING)
        return False

    session = requests.Session()
    session.cookies.set('PHPSESSID', session_cookie, domain='www.talktv.cz')

    # Retry once on network error (transient failures)
    for attempt in range(2):
        try:
            response = session.get('https://www.talktv.cz/videa', timeout=10)

            if 'popup-account__header-email' in response.text:
                log("Session cookie valid", xbmc.LOGINFO)
                _session_cache['session'] = session
                _session_cache['validated_at'] = current_time
                _session_cache['failed_cookie'] = None
                _session_cache['network_error'] = False
                return session
            else:
                # Session invalid - mark cookie as failed
                log("Session cookie invalid", xbmc.LOGWARNING)
                _session_cache['failed_cookie'] = session_cookie
                _session_cache['session'] = None
                _session_cache['validated_at'] = 0
                _session_cache['network_error'] = False
                return False

        except requests.exceptions.ConnectionError as e:
            if attempt == 0:
                log(f"Network error, retrying in 2s: {str(e)}", xbmc.LOGWARNING)
                time.sleep(2)
                continue
            log(f"Session validation failed (network error): {str(e)}", xbmc.LOGERROR)
            _session_cache['session'] = None
            _session_cache['validated_at'] = 0
            _session_cache['network_error'] = True
            return False

        except Exception as e:
            log(f"Session validation failed: {str(e)}", xbmc.LOGERROR)
            _session_cache['failed_cookie'] = session_cookie
            _session_cache['session'] = None
            _session_cache['validated_at'] = 0
            _session_cache['network_error'] = False
            return False

    return False

def require_session():
    """
    Get session, showing auth error dialog if failed.

    Returns:
        requests.Session: A valid session object
        None: Authentication failed (error dialog already shown)
    """
    session = get_session()
    if not session:
        log("Failed to get valid session", xbmc.LOGERROR)
        if is_cookie_failed():
            xbmcgui.Dialog().ok('Chyba autentizace', 'Neplatná nebo prošlá session cookie.\n\nProsím aktualizujte cookie v nastavení doplňku.')
        elif _session_cache.get('network_error'):
            xbmcgui.Dialog().notification('Chyba sítě', 'Nelze se připojit k TALK.cz', xbmcgui.NOTIFICATION_ERROR, time=5000)
        return None
    return session

def is_cookie_failed():
    """
    Check if the current session cookie is the one that previously failed
    
    Returns:
        bool: True if current cookie is marked as failed
    """
    session_cookie = _ADDON.getSetting('session_cookie')
    return session_cookie and session_cookie == _session_cache.get('failed_cookie')

def test_session():
    """
    Test if the current session cookie is valid
    """
    
    # Get the session cookie
    session_cookie = _ADDON.getSetting('session_cookie')
    log("Testing session cookie", xbmc.LOGINFO)

    if not session_cookie:
        # Inform user they need to save settings first if no cookie is found
        dialog_result = xbmcgui.Dialog().yesno(
            'Test Session', 
            'No session cookie found. Make sure you have entered the session cookie and saved the settings.\n\nDo you want to open settings now?'
        )
        if dialog_result:
            _ADDON.openSettings()
        return False

    session = requests.Session()

    try:
        # Set up the session cookie
        session.cookies.set('PHPSESSID', session_cookie, domain='www.talktv.cz')

        # Test the session by requesting the videos page
        response = session.get('https://www.talktv.cz/videa')

        # Check if we're properly authenticated
        if 'popup-account__header-email' in response.text:
            log("Session cookie is valid", xbmc.LOGINFO)
            xbmcgui.Dialog().ok('Test Session', 'Session cookie is valid! You are logged in.')
            return True
        else:
            log("Session cookie is invalid", xbmc.LOGERROR)
            xbmcgui.Dialog().ok('Test Session', 'Session cookie is invalid or expired.\n\nIf you just entered a new cookie, make sure to SAVE the settings first before testing.\n\nOtherwise, please get a new cookie from your browser.')
            return False

    except Exception as e:
        log(f"Session test failed: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok('Test Session Error', str(e))
        return False