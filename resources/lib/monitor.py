import threading
import xbmc
import xbmcgui
from bs4 import BeautifulSoup
from .auth import get_session
from .constants import _ADDON
from .talknews import parse_talknews_item
from .utils import log

class TalkNewsMonitor:
    """
    Background monitor for TALKNEWS updates that keeps session alive
    and notifies user of new content
    """

    def __init__(self):
        self.running = False
        self.thread = None
        self.kodi_monitor = xbmc.Monitor()
        self.last_seen_title = None
        self.pending_notifications = []

    def _should_stop(self):
        """Check if the monitor should stop (Kodi exit or manual stop)"""
        return not self.running or self.kodi_monitor.abortRequested()

    def start(self):
        """Start the background monitoring"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()
        log("TALKNEWS monitor started", xbmc.LOGINFO)

    def stop(self):
        """Stop the background monitoring"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        _KODI_WINDOW.clearProperty(_MONITOR_PROP)
        log("TALKNEWS monitor stopped", xbmc.LOGINFO)

    def _monitor_loop(self):
        """Main monitoring loop"""
        # Load last seen item from settings
        self.last_seen_title = _ADDON.getSetting('last_talknews_title')

        while not self._should_stop():
            try:
                # Check if monitoring is still enabled
                if not _ADDON.getSettingBool('monitor_talknews'):
                    log("TALKNEWS monitoring disabled, stopping", xbmc.LOGINFO)
                    break

                # Get check interval in hours from enum (0=1h, 1=3h, 2=6h, 3=12h, 4=24h, 5=48h)
                interval_index = int(_ADDON.getSetting('check_interval'))
                interval_options = [1, 3, 6, 12, 24, 48]

                if interval_index < 0 or interval_index >= len(interval_options):
                    interval_hours = 6  # Fallback to default (6 hours)
                else:
                    interval_hours = interval_options[interval_index]

                log(f"Checking TALKNEWS (interval: {interval_hours}h)", xbmc.LOGDEBUG)

                # Check for new items
                self._check_talknews()

                # Check for pending notifications to show
                self._check_and_show_pending()

                # Wait for the specified interval using Kodi's waitForAbort
                # which returns True immediately when Kodi is shutting down
                interval_seconds = interval_hours * 3600
                for _ in range(interval_seconds // 300):  # 5-minute intervals
                    if self._should_stop():
                        break
                    if self.kodi_monitor.waitForAbort(300):
                        break  # Kodi is shutting down

                    # Check for pending notifications during wait periods too
                    self._check_and_show_pending()

            except Exception as e:
                log(f"Error in TALKNEWS monitor loop: {str(e)}", xbmc.LOGERROR)
                # Wait a bit before retrying, but respect Kodi shutdown
                if self.kodi_monitor.waitForAbort(60):
                    break

        self.running = False
        _KODI_WINDOW.clearProperty(_MONITOR_PROP)

    def _check_talknews(self):
        """Check TALKNEWS page for new items"""
        try:
            # Get a session (this keeps the cookie alive)
            session = get_session()
            if not session:
                log("Could not get session for TALKNEWS check", xbmc.LOGWARNING)
                return

            response = session.get('https://www.talktv.cz/talknews', timeout=10)
            if response.status_code != 200:
                log(f"Failed to fetch TALKNEWS page: {response.status_code}", xbmc.LOGWARNING)
                return

            log("Successfully fetched TALKNEWS page, session is alive", xbmc.LOGDEBUG)

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find the first news item (most recent)
            news_items = soup.find_all(['div', 'a'], class_='embed__item')
            if not news_items:
                log("No TALKNEWS items found", xbmc.LOGDEBUG)
                return

            first_item = news_items[0]

            parsed = parse_talknews_item(first_item)
            if not parsed:
                log("No title found in first TALKNEWS item", xbmc.LOGDEBUG)
                return
            tag_text, title_text, meta_text, _link = parsed

            # Build full title like in talknews.py with green color formatting
            current_title = f"[COLOR limegreen]{tag_text}[/COLOR] • {title_text}" if tag_text else title_text
            log(f"Current TALKNEWS title: {current_title[:50]}...", xbmc.LOGDEBUG)

            # Initialize last_seen_title if not set yet
            if not self.last_seen_title:
                self.last_seen_title = current_title
                _ADDON.setSetting('last_talknews_title', current_title)
                log("Initialized last seen TALKNEWS title", xbmc.LOGINFO)
                return

            # Check if this is a new item
            if current_title != self.last_seen_title:
                log(f"New TALKNEWS item detected: {current_title}", xbmc.LOGINFO)

                # Update last seen title BEFORE showing notification to prevent
                # duplicate dialogs if multiple monitor instances are running
                self.last_seen_title = current_title
                _ADDON.setSetting('last_talknews_title', current_title)

                # Show notification
                self._show_notification(tag_text, title_text, meta_text)

        except Exception as e:
            log(f"Error checking TALKNEWS: {str(e)}", xbmc.LOGERROR)

    def _show_notification(self, show_name, title_text, meta_text=""):
        """Show notification for new TALKNEWS item

        Args:
            show_name (str): Show/tag name (e.g. "livestream standashow")
            title_text (str): Article title (e.g. "Host: Petr Ludwig ...")
            meta_text (str): Additional meta info (date, etc.)
        """
        try:
            if self._should_stop():
                return

            # Toast notification uses just the show name + title; the ok() dialog
            # (shown immediately, or later from the pending queue) also gets meta_text
            toast_content = f"[COLOR limegreen]{show_name.upper()}[/COLOR]\n{title_text}" if show_name else title_text
            ok_content = f"{toast_content}\n{meta_text}" if meta_text else toast_content

            # Check if video is playing
            player = xbmc.Player()
            if player.isPlayingVideo():
                # Show non-intrusive toast notification during playback
                icon = _ADDON.getAddonInfo('icon')
                xbmcgui.Dialog().notification('TALKNEWS', toast_content, icon, time=8000)

                # Store full content for later display when playback stops
                self._store_pending_notification(ok_content)
            else:
                # Show modal dialog when not playing video
                xbmcgui.Dialog().ok('TALKNEWS', ok_content)

        except Exception as e:
            log(f"Error showing TALKNEWS notification: {str(e)}", xbmc.LOGERROR)

    def _store_pending_notification(self, content):
        """Store notification to show later when playback stops"""
        self.pending_notifications.append(content)
        log("Stored TALKNEWS notification for later display", xbmc.LOGDEBUG)

    def _check_and_show_pending(self):
        """Check if playback stopped and show any pending notifications"""
        try:
            if self._should_stop():
                return

            player = xbmc.Player()
            if not player.isPlayingVideo() and self.pending_notifications:
                # Show all pending notifications
                for content in self.pending_notifications:
                    if self._should_stop():
                        break
                    xbmcgui.Dialog().ok('TALKNEWS', content)

                # Clear pending notifications
                count = len(self.pending_notifications)
                self.pending_notifications.clear()
                log(f"Showed {count} pending TALKNEWS notifications", xbmc.LOGINFO)

        except Exception as e:
            log(f"Error showing TALKNEWS notification: {str(e)}", xbmc.LOGERROR)

# Global monitor instance
_monitor = None
_monitor_lock = threading.Lock()

# Cross-invocation singleton guard.
# xbmcgui.Window(10000) is the Kodi Home screen — its properties live in
# Kodi's own memory and survive Python context restarts (reuselanguageinvoker=false).
_KODI_WINDOW = xbmcgui.Window(10000)
_MONITOR_PROP = 'plugin.video.talk.cz.monitor_running'

def start_monitor():
    """Start the TALKNEWS monitor if enabled"""
    global _monitor

    if not _ADDON.getSettingBool('monitor_talknews'):
        return

    with _monitor_lock:
        # Primary guard: window property persists across plugin Python contexts
        if _KODI_WINDOW.getProperty(_MONITOR_PROP) == 'true':
            return
        # Secondary guard: in-process check (reuselanguageinvoker=true or same context)
        if _monitor and _monitor.running:
            return

        _KODI_WINDOW.setProperty(_MONITOR_PROP, 'true')
        _monitor = TalkNewsMonitor()
        _monitor.start()

def reset_monitor():
    """Reset the TALKNEWS monitor (clear last seen title and restart)"""
    global _monitor

    try:
        # Clear the last seen title
        _ADDON.setSetting('last_talknews_title', '')
        log("TALKNEWS monitor reset - cleared last seen title", xbmc.LOGINFO)

        # Restart monitor if it was running
        if _monitor and _monitor.running:
            _monitor.stop()
            _monitor = None
            start_monitor()
            log("TALKNEWS monitor restarted", xbmc.LOGINFO)

        xbmcgui.Dialog().notification('TALKNEWS Monitor', 'Monitor byl resetován', time=3000)

    except Exception as e:
        log(f"Error resetting TALKNEWS monitor: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Chyba', 'Chyba při resetování monitoru')