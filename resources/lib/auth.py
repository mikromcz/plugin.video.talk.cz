import os
import time
import requests
import xbmc
import xbmcgui
from bs4 import BeautifulSoup
from .constants import _ADDON
from .utils import log

def get_session():
    """
    Get a requests session with authentication cookie.

    Returns:
        requests.Session: A session object with authentication cookie set
    """

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

def login():
    """
    Main login function that tries available login methods

    Returns:
        bool: True if login was successful, False otherwise
    """

    # First try direct login
    if try_direct_login():
        return True

    # If direct login failed, try Patreon
    #if try_patreon_login():
    #    return True

    # Both methods failed
    return False

def try_direct_login():
    """
    Attempt direct login with form submission and reCAPTCHA bypass.

    Returns:
        bool: True if login was successful, False otherwise
    """

    email = _ADDON.getSetting('email')
    password = _ADDON.getSetting('password')

    if not email or not password:
        log("Missing email or password", xbmc.LOGWARNING)
        return False

    session = requests.Session()

    try:
        # Step 1: First load the login page to get initial cookies
        log("Loading initial login page...", xbmc.LOGDEBUG)
        initial_response = session.get('https://www.talktv.cz/prihlasit')
        log(f"Initial cookies: {dict(session.cookies.items())}", xbmc.LOGDEBUG)

        # Step 2: Set cookie consent
        log("Setting cookie consent...", xbmc.LOGDEBUG)
        consent_response = session.get(
            'https://www.talktv.cz/srv/setCookiesConsent',
            params={'consent': '1'},
            headers={
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': 'https://www.talktv.cz/prihlasit'
            }
        )
        log(f"Cookie consent response: {consent_response.status_code}", xbmc.LOGDEBUG)
        log(f"Cookies after consent: {dict(session.cookies.items())}", xbmc.LOGDEBUG)

        # Step 3: Load recaptcha.js to get grecaptcha cookie
        log("Loading reCAPTCHA script...", xbmc.LOGDEBUG)
        recaptcha_js = session.get(
            'https://www.google.com/recaptcha/api.js',
            params={'v': '2024-12-16-175'},
            headers={
                'Referer': 'https://www.talktv.cz/prihlasit'
            }
        )
        log(f"Cookies after reCAPTCHA script: {dict(session.cookies.items())}", xbmc.LOGDEBUG)

        # Step 4: Get CSRF token from a fresh page load
        log("Getting fresh CSRF token...", xbmc.LOGDEBUG)
        login_page = session.get('https://www.talktv.cz/prihlasit')
        soup = BeautifulSoup(login_page.text, 'html.parser')
        csrf_element = soup.find('input', {'name': 'csrf'})

        if not csrf_element:
            log("Could not find CSRF token", xbmc.LOGERROR)
            return False

        csrf_token = csrf_element['value']
        log(f"Found CSRF token: {csrf_token}", xbmc.LOGDEBUG)

        # Step 5: Get reCAPTCHA site key
        recaptcha_div = soup.find('div', {'class': 'g-recaptcha'})
        if not recaptcha_div:
            log("Could not find reCAPTCHA div", xbmc.LOGERROR)
            return False

        site_key = recaptcha_div['data-sitekey']
        log(f"Found reCAPTCHA site key: {site_key}", xbmc.LOGDEBUG)

        # Step 6: Get reCAPTCHA token
        recaptcha_token = get_recaptcha_token(site_key)
        if not recaptcha_token:
            log("Failed to get reCAPTCHA token", xbmc.LOGERROR)
            return False

        # Step 7: Submit login with all cookies intact
        post_data = {
            'csrf': csrf_token,
            'email': email,
            'password': password,
            'g-recaptcha-response': recaptcha_token
        }

        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "accept-language": "cs-CZ,cs;q=0.8",
            "cache-control": "max-age=0",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://www.talktv.cz",
            "referer": "https://www.talktv.cz/prihlasit",
            "sec-ch-ua": '"Brave";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1"
        }

        log(f"Submitting login with cookies: {dict(session.cookies.items())}", xbmc.LOGDEBUG)
        response = session.post(
            'https://www.talktv.cz/prihlasit',
            data=post_data,
            headers=headers,
            allow_redirects=True
        )

        # Check response and set cookie if successful
        if 'popup-account__header-email' in response.text:
            session_cookie = session.cookies.get('PHPSESSID')
            if session_cookie:
                _ADDON.setSetting('session_cookie', session_cookie)
                log("Login successful", xbmc.LOGINFO)
                return True
            else:
                log("Login seemed successful but no session cookie", xbmc.LOGERROR)
                return False

        error_soup = BeautifulSoup(response.text, 'html.parser')
        error_container = error_soup.find('div', {'class': 'error-container'})
        if error_container and error_container.text.strip():
            error_text = error_container.text.strip()
            log(f"Login error message found: {error_text}", xbmc.LOGERROR)
            return False

        log("Login failed - could not find account header", xbmc.LOGWARNING)
        return False

    except Exception as e:
        log(f"Login failed with error: {str(e)}", xbmc.LOGERROR)
        return False

def try_patreon_login():
    """
    Attempt login via Patreon OAuth

    Returns:
        bool: True if login was successful, False otherwise
    """

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

def test_credentials():
    """
    Test login credentials with full debug output.

    This function is used to test the login credentials and provide detailed debug output.
    It is useful for troubleshooting login issues and reCAPTCHA token generation.
    """

    email = _ADDON.getSetting('email')
    password = _ADDON.getSetting('password')

    log(f"Testing credentials - Email length: {len(email) if email else 0}", xbmc.LOGINFO)
    log(f"Testing credentials - Password length: {len(password) if password else 0}", xbmc.LOGINFO)

    if not email or not password:
        xbmcgui.Dialog().ok('Test', 'Missing credentials in settings')
        return

    session = requests.Session()

    try:
        # First, handle cookie consent
        log("Setting cookie consent...", xbmc.LOGDEBUG)
        consent_response = session.get(
            'https://www.talktv.cz/srv/setCookiesConsent',
            params={'consent': '1'},
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        log(f"Cookie consent response: {consent_response.status_code}", xbmc.LOGDEBUG)

        # Get login page and CSRF token
        log("Fetching login page...", xbmc.LOGDEBUG)
        login_page = session.get(
            'https://www.talktv.cz/prihlasit',
            headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'cs-CZ,cs;q=0.8'
            }
        )
        log(f"Login page cookies: {dict(session.cookies.items())}", xbmc.LOGDEBUG)

        soup = BeautifulSoup(login_page.text, 'html.parser')

        csrf_element = soup.find('input', {'name': 'csrf'})
        if not csrf_element:
            log("Could not find CSRF token", xbmc.LOGERROR)
            xbmcgui.Dialog().ok('Test Error', 'Could not find CSRF token')
            return

        csrf_token = csrf_element['value']
        log(f"Found CSRF token: {csrf_token}", xbmc.LOGDEBUG)

        recaptcha_div = soup.find('div', {'class': 'g-recaptcha'})
        if not recaptcha_div:
            log("Could not find reCAPTCHA div", xbmc.LOGERROR)
            xbmcgui.Dialog().ok('Test Error', 'Could not find reCAPTCHA element')
            return

        site_key = recaptcha_div['data-sitekey']
        log(f"Found reCAPTCHA site key: {site_key}", xbmc.LOGDEBUG)

        # Get reCAPTCHA token
        recaptcha_token = get_recaptcha_token(site_key)
        if not recaptcha_token:
            log("Failed to get reCAPTCHA token", xbmc.LOGERROR)
            xbmcgui.Dialog().ok('Test Error', 'Failed to get reCAPTCHA token')
            return

        log(f"Got reCAPTCHA token length: {len(recaptcha_token)}", xbmc.LOGDEBUG)
        log(f"Token preview: {recaptcha_token[:50]}...", xbmc.LOGDEBUG)

        # Set login form data in exact order
        login_data = [
            ('csrf', csrf_token),
            ('email', email),
            ('password', password),
            ('g-recaptcha-response', recaptcha_token)
        ]

        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "accept-language": "cs-CZ,cs;q=0.8",
            "cache-control": "max-age=0",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://www.talktv.cz",
            "referer": "https://www.talktv.cz/prihlasit",
            "sec-ch-ua": '"Chromium";v="131"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1"
        }

        log(f"Login request cookies: {dict(session.cookies.items())}", xbmc.LOGDEBUG)
        log("Submitting login form...", xbmc.LOGDEBUG)

        response = session.post(
            'https://www.talktv.cz/prihlasit',
            data=login_data,
            headers=headers,
            allow_redirects=True
        )

        log(f"Login response status: {response.status_code}", xbmc.LOGDEBUG)
        log(f"Login response headers: {dict(response.headers)}", xbmc.LOGDEBUG)
        log(f"Login response cookies: {dict(session.cookies.items())}", xbmc.LOGDEBUG)

        content = response.text
        content_preview = content[:500] + "..." if len(content) > 500 else content
        log(f"Login response content preview: {content_preview}", xbmc.LOGDEBUG)

        # Save full response for analysis
        try:
            import xbmcvfs
            profile_path = xbmcvfs.translatePath(_ADDON.getAddonInfo('profile'))
            response_file = os.path.join(profile_path, 'login_response.html')
            with open(response_file, 'w', encoding='utf-8') as f:
                f.write(content)
            log(f"Saved full response to: {response_file}", xbmc.LOGINFO)
        except Exception as e:
            log(f"Failed to save response content: {str(e)}", xbmc.LOGWARNING)

        # Check for error messages
        error_soup = BeautifulSoup(response.text, 'html.parser')
        error_container = error_soup.find('div', {'class': 'error-container'})
        if error_container and error_container.text.strip():
            error_text = error_container.text.strip()
            log(f"Login error message found: {error_text}", xbmc.LOGERROR)
            xbmcgui.Dialog().ok('Test Error', f'Login failed: {error_text}')
            return

        if 'popup-account__header-email' in response.text:
            # Store session cookie
            session_cookie = session.cookies.get('PHPSESSID')
            if session_cookie:
                _ADDON.setSetting('session_cookie', session_cookie)
                log("Login successful", xbmc.LOGINFO)
                xbmcgui.Dialog().ok('Test Success', 'Login successful!')
                return
            else:
                log("Login seemed successful but no session cookie found", xbmc.LOGERROR)
                xbmcgui.Dialog().ok('Test Error', 'Login seemed successful but no session cookie found')
                return

        log("Login failed - could not find account header", xbmc.LOGWARNING)
        xbmcgui.Dialog().ok('Test Error', 'Login failed - could not find account header')

    except Exception as e:
        log(f"Test failed: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok('Test Error', str(e))
    """Test login credentials with full debug output."""
    email = _ADDON.getSetting('email')
    password = _ADDON.getSetting('password')

    log(f"Testing credentials - Email length: {len(email) if email else 0}", xbmc.LOGINFO)
    log(f"Testing credentials - Password length: {len(password) if password else 0}", xbmc.LOGINFO)

    if not email or not password:
        xbmcgui.Dialog().ok('Test', 'Missing credentials in settings')
        return

    session = requests.Session()

    try:
        # Get login page and CSRF token
        log("Fetching login page...", xbmc.LOGDEBUG)
        login_page = session.get('https://www.talktv.cz/prihlasit')
        log(f"Login page status: {login_page.status_code}", xbmc.LOGDEBUG)
        log(f"Login page cookies: {dict(session.cookies.items())}", xbmc.LOGDEBUG)

        soup = BeautifulSoup(login_page.text, 'html.parser')

        csrf_element = soup.find('input', {'name': 'csrf'})
        if not csrf_element:
            log("Could not find CSRF token", xbmc.LOGERROR)
            xbmcgui.Dialog().ok('Test Error', 'Could not find CSRF token')
            return

        csrf_token = csrf_element['value']
        log(f"Found CSRF token: {csrf_token}", xbmc.LOGDEBUG)

        recaptcha_div = soup.find('div', {'class': 'g-recaptcha'})
        if not recaptcha_div:
            log("Could not find reCAPTCHA div", xbmc.LOGERROR)
            xbmcgui.Dialog().ok('Test Error', 'Could not find reCAPTCHA element')
            return

        site_key = recaptcha_div['data-sitekey']
        log(f"Found reCAPTCHA site key: {site_key}", xbmc.LOGDEBUG)

        # Get reCAPTCHA token
        recaptcha_token = get_recaptcha_token(site_key)
        if not recaptcha_token:
            log("Failed to get reCAPTCHA token", xbmc.LOGERROR)
            xbmcgui.Dialog().ok('Test Error', 'Failed to get reCAPTCHA token')
            return

        log(f"Got reCAPTCHA token: {recaptcha_token[:20]}...", xbmc.LOGDEBUG)

        # Submit login
        login_data = {
            'email': email,
            'password': password,
            'csrf': csrf_token,
            'g-recaptcha-response': recaptcha_token
        }

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'cs-CZ,cs;q=0.8',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.talktv.cz',
            'Referer': 'https://www.talktv.cz/prihlasit',
            'sec-ch-ua': '"Chromium";v="131"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        log("Submitting login form with data: " + str({k: v if k != 'password' else '*****' for k, v in login_data.items()}), xbmc.LOGDEBUG)
        log("Using headers: " + str(headers), xbmc.LOGDEBUG)

        response = session.post(
            'https://www.talktv.cz/prihlasit',
            data=login_data,
            headers=headers
        )

        log(f"Login response status: {response.status_code}", xbmc.LOGDEBUG)
        log(f"Login response headers: {dict(response.headers)}", xbmc.LOGDEBUG)
        log("Login response cookies: " + str({k: v for k, v in session.cookies.items()}), xbmc.LOGDEBUG)

        # Log the response content but mask any sensitive data
        content = response.text
        content_preview = content[:500] + "..." if len(content) > 500 else content
        log(f"Login response content preview: {content_preview}", xbmc.LOGDEBUG)

        # Save full response content to file for analysis
        try:
            import xbmcvfs
            profile_path = xbmcvfs.translatePath(_ADDON.getAddonInfo('profile'))
            response_file = os.path.join(profile_path, 'login_response.html')
            with open(response_file, 'w', encoding='utf-8') as f:
                f.write(content)
            log(f"Saved full response to: {response_file}", xbmc.LOGINFO)
        except Exception as e:
            log(f"Failed to save response content: {str(e)}", xbmc.LOGWARNING)

        # Check for specific error messages
        error_soup = BeautifulSoup(response.text, 'html.parser')

        # Look for any error messages in common error classes
        error_classes = ['alert alert-danger', 'error-message', 'form-error']
        for class_name in error_classes:
            error_msg = error_soup.find('div', {'class': class_name})
            if error_msg:
                error_text = error_msg.text.strip()
                log(f"Login error message found in class {class_name}: {error_text}", xbmc.LOGERROR)
                xbmcgui.Dialog().ok('Test Error', f'Login failed: {error_text}')
                return

        # Look for recaptcha error specifically
        if 'recaptcha' in response.text.lower():
            recaptcha_msg = "Found reCAPTCHA related content in response"
            log(recaptcha_msg, xbmc.LOGERROR)
            xbmcgui.Dialog().ok('Test Error', recaptcha_msg)
            return

        if 'popup-account__header-email' in response.text:
            # Store session cookie
            session_cookie = session.cookies.get('PHPSESSID')
            if session_cookie:
                _ADDON.setSetting('session_cookie', session_cookie)
                log("Login successful", xbmc.LOGINFO)
                xbmcgui.Dialog().ok('Test Success', 'Login successful!')
                return
            else:
                log("Login seemed successful but no session cookie found", xbmc.LOGERROR)
                xbmcgui.Dialog().ok('Test Error', 'Login seemed successful but no session cookie found')
                return

        log("Login failed - could not find account header", xbmc.LOGWARNING)
        xbmcgui.Dialog().ok('Test Error', 'Login failed - could not find account header')

    except Exception as e:
        log(f"Test failed: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok('Test Error', str(e))

def test_session():
    """
    Test if the current session cookie is valid
    """
    
    # Get the session cookie
    session_cookie = _ADDON.getSetting('session_cookie')
    log(f"Testing session cookie (length: {len(session_cookie) if session_cookie else 0})", xbmc.LOGINFO)

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
    log(f"Testing session cookie: {session_cookie[:20]}...", xbmc.LOGINFO)

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

def get_recaptcha_token(site_key):
    """
    Get reCAPTCHA token using approach that matches browser flow.

    Args:
        site_key (str): The reCAPTCHA site key to use

    Returns:
        str: The reCAPTCHA token if successful, None otherwise
    """

    try:
        session = requests.Session()

        # Step 1: Initial anchor request like browser's initial page load
        log("Starting initial anchor request...", xbmc.LOGDEBUG)
        anchor_url = (
            f"https://www.google.com/recaptcha/api2/anchor"
            f"?ar=1"
            f"&k={site_key}"
            f"&co=aHR0cHM6Ly93d3cudGFsa3R2LmN6OjQ0Mw.."
            f"&hl=cs"
            f"&v=zIriijn3uj5Vpknvt_LnfNbF"
            f"&size=invisible"
            f"&cb=" + str(int(time.time() * 1000))
        )

        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "accept-language": "cs-CZ,cs;q=0.8",
            "sec-ch-ua": '"Brave";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "iframe",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "cross-site",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1"
        }

        response = session.get(anchor_url, headers=headers)
        log(f"Initial anchor response status: {response.status_code}", xbmc.LOGDEBUG)
        log(f"Initial anchor cookies: {dict(session.cookies.items())}", xbmc.LOGDEBUG)

        soup = BeautifulSoup(response.text, 'html.parser')
        token_element = soup.find('input', {'id': 'recaptcha-token'})
        if not token_element:
            log("Could not find initial recaptcha-token", xbmc.LOGERROR)
            return None

        initial_token = token_element['value']
        log(f"Got initial token: {initial_token[:20]}...", xbmc.LOGDEBUG)

        # Step 2: First reload request (simulating grecaptcha.reset())
        log("Starting first reload request...", xbmc.LOGDEBUG)
        reload_url = f"https://www.google.com/recaptcha/api2/reload?k={site_key}"

        reload_headers = {
            "accept": "*/*",
            "accept-language": "cs-CZ,cs;q=0.8",
            "content-type": "application/x-www-form-urlencoded",
            "sec-ch-ua": '"Brave";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "origin": "https://www.google.com",
            "referer": anchor_url
        }

        reload_data = {
            'v': 'zIriijn3uj5Vpknvt_LnfNbF',
            'reason': 'q',
            'c': initial_token,
            'k': site_key,
            'co': 'aHR0cHM6Ly93d3cudGFsa3R2LmN6OjQ0Mw..',
            'hl': 'cs',
            'size': 'invisible',
            'chr': '[89,64,71]',
            'vh': '13599012192',
            'bg': 'qxNvTkF3E-kF9qRfuPPHzoNO3qGFcqQHwhfV3tXHFiXKhU9ByVvWNTrEBgQ...'
        }

        response = session.post(reload_url, headers=reload_headers, data=reload_data)
        log(f"First reload response status: {response.status_code}", xbmc.LOGDEBUG)
        log(f"First reload cookies: {dict(session.cookies.items())}", xbmc.LOGDEBUG)

        if '"rresp","' in response.text:
            token = response.text.split('"rresp","')[1].split('"')[0]
            log(f"Got final token length: {len(token)}", xbmc.LOGDEBUG)
            log(f"Token preview: {token[:50]}...", xbmc.LOGDEBUG)
            return token
        else:
            log(f"Could not find rresp in response: {response.text[:200]}", xbmc.LOGERROR)
            return None

    except Exception as e:
        log(f"Error getting reCAPTCHA token: {str(e)}", xbmc.LOGERROR)
        return None