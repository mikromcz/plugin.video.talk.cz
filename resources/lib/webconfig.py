import os
import http.server
import socket
import socketserver
import json
import requests
import threading
import time
import xbmc
from urllib.parse import urlparse
from .constants import _ADDON
from .utils import log


class ConfigHandler(http.server.SimpleHTTPRequestHandler):
    """
    Custom handler for the config server

    GET /talk - Serve the HTML template
    POST /talk/save - Save the session cookie
    POST /talk/test - Test the session cookie
    """

    # Handle GET requests
    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/talk':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()

            # Get current session cookie
            current_cookie = _ADDON.getSetting('session_cookie')

            # Get the path to webconfig.html
            current_dir = os.path.dirname(__file__)
            parent_dir = os.path.dirname(current_dir)
            html_path = os.path.join(parent_dir, 'webconfig.html')

            # Read the HTML template
            try:
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                # Replace placeholder with current cookie
                html_content = html_content.replace('{{CURRENT_COOKIE}}', current_cookie)

                self.wfile.write(html_content.encode('utf-8'))
            except Exception as e:
                log(f'Error reading HTML template: {str(e)}', xbmc.LOGERROR)
                self.send_error(500, f"Error reading template: {str(e)}")
            return

        self.send_error(404)

    # Handle POST requests
    def do_POST(self):
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/talk/save':
            log('Path matched /talk/save, processing request', xbmc.LOGINFO)

            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)

            if 'cookie' in data:
                _ADDON.setSetting('session_cookie', data['cookie'])

                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'success'}).encode('utf-8'))
                return

        elif parsed_path.path == '/talk/test':
            log('Path matched /talk/test, processing request', xbmc.LOGINFO)

            session = requests.Session()
            success = False
            message = 'Cookie není platné nebo je expirované'

            try:
                session_cookie = _ADDON.getSetting('session_cookie')
                session.cookies.set('PHPSESSID', session_cookie, domain='www.talktv.cz')
                response = session.get('https://www.talktv.cz/videa')

                if 'popup-account__header-email' in response.text:
                    success = True
                    message = 'Cookie je platné!'

                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': success,
                    'message': message
                }).encode('utf-8'))
                return

            except Exception as e:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': f'Chyba při testování: {str(e)}'
                }).encode('utf-8'))
                return
        else:
            log(f'No matching handler for path: {parsed_path}', xbmc.LOGINFO)
            self.send_error(404)

# Global server control
_server_shutdown_event = threading.Event()
_server_instance = None

def start_server():
    """
    Start the config server with auto-shutdown after 10 minutes

    If the config page is enabled, start the server at the specified port
    and automatically shut it down after 10 minutes while disabling the setting
    """
    global _server_instance

    if not _ADDON.getSetting('enable_config_page') == 'true':
        return

    port = int(_ADDON.getSetting('config_port'))

    try:
        # Create custom TCPServer class with better socket options
        class ReuseAddrTCPServer(socketserver.TCPServer):
            allow_reuse_address = True

            def server_bind(self):
                # Set SO_REUSEADDR before binding
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # On Linux, also set SO_REUSEPORT if available
                try:
                    self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except (OSError, AttributeError):
                    pass  # SO_REUSEPORT not available on all systems
                super().server_bind()

            def service_actions(self):
                # Check if shutdown was requested
                if _server_shutdown_event.is_set():
                    self.shutdown()

        _server_instance = ReuseAddrTCPServer(("", port), ConfigHandler)

        # Start auto-shutdown timer (10 minutes)
        shutdown_timer = threading.Timer(600.0, _auto_shutdown_server)
        shutdown_timer.daemon = True
        shutdown_timer.start()

        log(f'Config server started at port {port} (auto-shutdown in 10 minutes)', xbmc.LOGINFO)

        # Serve until shutdown is requested
        while not _server_shutdown_event.is_set():
            _server_instance.handle_request()

    except Exception as e:
        log(f'Config server error: {str(e)}', xbmc.LOGERROR)
    finally:
        _cleanup_server()

def _auto_shutdown_server():
    """Auto-shutdown the server after timeout and disable the setting"""
    global _server_instance

    try:
        log('Config server auto-shutdown triggered (10 minutes timeout)', xbmc.LOGINFO)

        # Signal server to shutdown
        _server_shutdown_event.set()

        # Disable the config page setting
        _ADDON.setSettingBool('enable_config_page', False)

        # Show notification to user
        import xbmcgui
        xbmcgui.Dialog().notification(
            'Konfigurační server',
            'Server byl automaticky vypnut po 10 minutách',
            _ADDON.getAddonInfo('icon'),
            time=5000
        )

    except Exception as e:
        log(f'Error during auto-shutdown: {str(e)}', xbmc.LOGERROR)

def _cleanup_server():
    """Clean up server resources"""
    global _server_instance

    try:
        if _server_instance:
            _server_instance.server_close()
            _server_instance = None
        _server_shutdown_event.clear()
        log('Config server cleaned up', xbmc.LOGDEBUG)
    except Exception as e:
        log(f'Error cleaning up server: {str(e)}', xbmc.LOGERROR)
