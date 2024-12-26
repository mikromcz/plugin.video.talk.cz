import os
import http.server
import socketserver
import json
import requests
import xbmc
from urllib.parse import urlparse
from .constants import _ADDON
from .utils import log

class ConfigHandler(http.server.SimpleHTTPRequestHandler):
    # Custom handler for the config server

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

def start_server():
    # Start the config server
    if not _ADDON.getSettingBool('enable_config_page'):
        return

    port = _ADDON.getSettingInt('config_port')

    try:
        # Allow socket reuse
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", port), ConfigHandler) as httpd:
            log(f'Config server started at port {port}', xbmc.LOGINFO)
            httpd.serve_forever()
    except Exception as e:
        log(f'Config server error: {str(e)}', xbmc.LOGERROR)
