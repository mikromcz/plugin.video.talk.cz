import requests
import xbmc
import xbmcgui
from bs4 import BeautifulSoup
from .constants import _ADDON
from .utils import log

def login():
    # Main login function that tries available login methods

    # First try direct login
    if try_direct_login():
        return True

    # If direct login failed, try Patreon
    #if try_patreon_login():
    #    return True

    # Both methods failed
    return False

def try_direct_login():
    # Attempt direct login with form submission
    email = _ADDON.getSetting('email')
    password = _ADDON.getSetting('password')

    if not email or not password:
        return False

    session = requests.Session()

    try:
        # Get login page and CSRF token
        login_page = session.get('https://www.talktv.cz/prihlasit')
        soup = BeautifulSoup(login_page.text, 'html.parser')

        csrf_token = soup.find('input', {'name': 'csrf'})['value']
        recaptcha_div = soup.find('div', {'class': 'g-recaptcha'})
        site_key = recaptcha_div['data-sitekey']

        # Get reCAPTCHA token
        recaptcha_token = get_recaptcha_token(site_key)
        if not recaptcha_token:
            return False

        # Submit login
        login_data = {
            'email': email,
            'password': password,
            'csrf': csrf_token,
            'g-recaptcha-response': recaptcha_token
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.talktv.cz',
            'Referer': 'https://www.talktv.cz/prihlasit'
        }

        response = session.post('https://www.talktv.cz/prihlasit',
                              data=login_data,
                              headers=headers)

        if 'popup-account__header-email' in response.text:
            # Store session cookie
            session_cookie = session.cookies.get('PHPSESSID')
            if session_cookie:
                _ADDON.setSetting('session_cookie', session_cookie)
                return True

    except Exception as e:
        log(f"Direct login failed: {str(e)}", xbmc.LOGERROR)

    return False

def try_patreon_login():
    # Attempt login via Patreon OAuth
    session = requests.Session()

    try:
        # Start Patreon OAuth flow
        response = session.get('https://www.talktv.cz/srv/patreon-login')

        # This should redirect to Patreon's OAuth page
        if 'patreon.com/oauth2/authorize' in response.url:
            dialog = xbmcgui.Dialog()
            dialog.ok('Patreon Login',
                     'Pro přihlášení přes Patreon prosím:\n'
                     '1. Přihlaste se na talktv.cz přes Patreon ve webovém prohlížeči\n'
                     '2. Zkopírujte cookie PHPSESSID do nastavení doplňku')
            return False

    except Exception as e:
        log(f"Patreon login failed: {str(e)}", xbmc.LOGERROR)

    return False

def get_recaptcha_token(site_key):
    # Get reCAPTCHA token via Kodi GUI.
    dialog = xbmcgui.Dialog()
    dialog.ok('reCAPTCHA Required',
              'Pro přihlášení je potřeba vyřešit reCAPTCHA.\n'
              'Prosím navštivte stránku talktv.cz ve webovém prohlížeči,\n'
              'přihlaste se tam a pak zkopírujte cookie PHPSESSID do nastavení doplňku.')
    return None

def get_session():
    # Get a requests session with authentication cookie.
    # Attempts login if no valid session exists.
    session_cookie = _ADDON.getSetting('session_cookie')

    if not session_cookie:
        # No session cookie - try to login
        if not login():
            return False
        session_cookie = _ADDON.getSetting('session_cookie')

    session = requests.Session()
    session.cookies.set('PHPSESSID', session_cookie, domain='www.talktv.cz')

    try:
        # Test the session
        response = session.get('https://www.talktv.cz/videa')

        if 'popup-account__header-email' in response.text:
            log("Session cookie valid", xbmc.LOGINFO)
            return session
        else:
            # Session invalid - try to login again
            log("Session cookie invalid - attempting new login", xbmc.LOGWARNING)
            if login():
                # Recreate session with new cookie
                session = requests.Session()
                session.cookies.set('PHPSESSID', _ADDON.getSetting('session_cookie'), domain='www.talktv.cz')
                return session
            else:
                return False

    except Exception as e:
        log(f"Session validation failed: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Session Error', str(e))
        return False

def test_credentials():
    # Temporary function to test login credentials
    email = _ADDON.getSetting('email')
    password = _ADDON.getSetting('password')

    log(f"Testing credentials - Email length: {len(email) if email else 0}", xbmc.LOGINFO)
    log(f"Testing credentials - Password length: {len(password) if password else 0}", xbmc.LOGINFO)

    if not email or not password:
        xbmcgui.Dialog().ok('Test', 'Missing credentials in settings')
        return

    try:
        session = requests.Session()

        # Test basic connectivity
        response = session.get('https://www.talktv.cz/')
        log(f"Basic request status: {response.status_code}", xbmc.LOGINFO)

        # Get login page and CSRF token
        login_response = session.get('https://www.talktv.cz/prihlasit')
        login_soup = BeautifulSoup(login_response.text, 'html.parser')
        csrf_input = login_soup.find('input', {'name': 'csrf'})

        if csrf_input and csrf_input.get('value'):
            log(f"Found CSRF token: {csrf_input['value'][:10]}...", xbmc.LOGINFO)
        else:
            log("No CSRF token found", xbmc.LOGERROR)

        # Test XHR request
        headers = {'X-Requested-With': 'XMLHttpRequest'}
        xhr_response = session.get('https://www.talktv.cz/srv/getLoginStatus', headers=headers)
        log(f"XHR test response: {xhr_response.status_code}", xbmc.LOGINFO)

        xbmcgui.Dialog().ok('Test Results',
                           #f'email: {email}\n'
                           #f'password: {password}\n'
                           f'Basic request: {response.status_code}\n'
                           f'Login page: {login_response.status_code}\n'
                           f'CSRF token: {"Found" if csrf_input else "Not found"}\n'
                           f'XHR test: {xhr_response.status_code}')

    except Exception as e:
        log(f"Test failed: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok('Test Error', str(e))

def test_session():
    # Test if the current session cookie is valid
    session_cookie = _ADDON.getSetting('session_cookie')

    if not session_cookie:
        xbmcgui.Dialog().ok('Test Session', 'No session cookie configured. Please enter your session cookie in settings.')
        return False

    session = requests.Session()
    log("Testing session cookie...", xbmc.LOGINFO)

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
            xbmcgui.Dialog().ok('Test Session', 'Session cookie is invalid or expired. Please get a new cookie from your browser.')
            return False

    except Exception as e:
        log(f"Session test failed: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok('Test Session Error', str(e))
        return False