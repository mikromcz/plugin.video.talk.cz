import threading
import time
import re
import xbmc
import xbmcgui
import xbmcplugin
from bs4 import BeautifulSoup
from .auth import get_session
from .constants import _HANDLE, _ADDON
from .utils import get_url, log

# Global progress monitor instance
_progress_monitor = None
_monitor_lock = threading.Lock()

def play_video(video_url, requested_quality=None, start_time=None):
    """
    Play a video from the provided URL with optional quality and start time

    Args:
        video_url (str): URL of the video to play
        requested_quality (str): Optional quality preference (Auto, 1080p, 720p, 480p, 360p, 240p)
        start_time (int): Optional start time in seconds for video playback

    Example:
        play_video('https://www.talktv.cz/video/1726/marcel-kolaja-regulace-ai-cookie-listy-tiktok-a-bezpecnost-monopoly-na-trhu-a-ochrana-spotrebitele-papirova-brcka', '720p', 300)
    """

    # Get a session for making HTTP requests
    session = get_session()
    if not session:
        log("Failed to get valid session for video playback", xbmc.LOGERROR)
        return

    try:
        log(f"Attempting to play video: {video_url}", xbmc.LOGINFO)
        response = session.get(video_url)
        if response.status_code != 200:
            log(f"Failed to fetch video page: {response.status_code}", xbmc.LOGERROR)
            return

        # Parse the HTML response
        soup = BeautifulSoup(response.text, 'html.parser')
        video_element = soup.find('video-js')
        if not video_element:
            log("Video player element not found in page", xbmc.LOGERROR)
            return

        # Get quality preference if not specified
        if not requested_quality:
            quality_index = int(_ADDON.getSetting('video_quality'))
            qualities = ['Auto', '1080p', '720p', '480p', '360p', '240p']
            requested_quality = qualities[quality_index]

        # Find the best available source
        sources = video_element.find_all('source')
        selected_url = None
        use_hls = False

        # First try HLS for Auto quality
        if requested_quality.lower() == 'auto':
            for source in sources:
                if source.get('type') == 'application/x-mpegURL':
                    selected_url = source['src']
                    use_hls = True
                    log("Selected HLS stream for auto quality", xbmc.LOGINFO)
                    break

        # If no HLS or specific quality requested, try MP4
        if not selected_url:
            qualities = ['1080p', '720p', '480p', '360p', '240p']
            if requested_quality != 'Auto':
                # Start from requested quality
                start_idx = qualities.index(requested_quality)
                qualities = qualities[start_idx:]

            for quality in qualities:
                for source in sources:
                    if (source.get('type') == 'video/mp4' and
                        quality in source.get('src', '')):
                        selected_url = source['src']
                        log(f"Selected {quality} MP4 stream", xbmc.LOGINFO)
                        break
                if selected_url:
                    break

        # Fallback to first available source
        if not selected_url and sources:
            selected_url = sources[0]['src']
            log("Falling back to first available source", xbmc.LOGWARNING)

        if not selected_url:
            log("No playable source found", xbmc.LOGERROR)
            xbmcplugin.setResolvedUrl(_HANDLE, False, xbmcgui.ListItem())
            return

        # Setup playback
        play_item = xbmcgui.ListItem(path=selected_url)

        # Configure inputstream
        if use_hls:
            play_item.setMimeType('application/x-mpegURL')
            play_item.setProperty('inputstream', 'inputstream.adaptive')
        else:
            play_item.setMimeType('video/mp4')

        play_item.setContentLookup(False)

        try:
            # Get main details info
            details = soup.find('div', class_='details__info')
            description = ''

            if details:
                main_content = details.text.strip()
                parts = main_content.split('                -', 1)
                if len(parts) == 2:
                    description = parts[1].strip()
                else:
                    description = main_content

            # Get additional description if available
            description_element = soup.find('div', class_='details__description-text')
            if description_element:
                additional_description = description_element.text.strip()
                if additional_description:
                    # Only add newline if we have both descriptions
                    if description:
                        description += '\n\n' + additional_description
                    else:
                        description = additional_description

            # Get title if available
            title = soup.find('h1', class_='details__header')
            if title:
                title = title.text.strip()

            # Set video metadata
            info_tag = play_item.getVideoInfoTag()
            info_tag.setMediaType('video')
            if description:
                info_tag.setPlot(description)
            if title:
                info_tag.setTitle(title)

        except Exception as e:
            log(f"Failed to set video metadata: {str(e)}", xbmc.LOGWARNING)

        # Handle start time if specified
        if start_time:
            monitor = get_progress_monitor()
            monitor.initial_position = start_time
            log(f"Setting initial position to {start_time}s", xbmc.LOGINFO)

        # Extract and store video ID
        #
        # Original JS code on the video page footer:
        # initPlayerComponent({
        #     "videoTitle":"Marcel Kolaja: regulace AI, cookie lišty, TikTok a bezpečnost, monopoly na trhu a ochrana spotřebitele, papírová brčka...",
        #     "posterUrl":"https://static.talktv.cz/upload/videos/gl4vZ6yK-poster-sGox3q.jpg",
        #->   "videoId":1726,
        #     "debugMode":false,
        #     "overrideNative":true,
        #     "overrideChromecastSource":false,
        #     "overrideChromecastSourceOriginal":false,
        #     "canShowChromecastWarning":true,
        #     "canShowChromecastRevert":false,
        #     "videoFallbackUrl":"https://vz-b80bf3f2-495.b-cdn.net/bcdn_token=isq0PSmvxnfa054B4A9CTah_xT-L3gfS9OfvqCMp4do&expires=1735482522&token_path=%2Ffbed3ada-c002-475d-9545-d5e679746370/fbed3ada-c002-475d-9545-d5e679746370/play_720p.mp4",
        #     "ssVideoPos":5899,
        #     "ssVideoTime":1735309692
        # });
        try:
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'initPlayerComponent' in script.string:
                    match = re.search(r'"videoId":(\d+)', script.string)
                    if match:
                        monitor = get_progress_monitor()
                        monitor.video_id = match.group(1)
                        break
        except Exception as e:
            log(f"Error extracting video ID: {str(e)}", xbmc.LOGERROR)

        # Start playback
        xbmcplugin.setResolvedUrl(_HANDLE, True, listitem=play_item)

    except Exception as e:
        log(f"Error during video playback setup: {str(e)}", xbmc.LOGERROR)
        xbmcplugin.setResolvedUrl(_HANDLE, False, xbmcgui.ListItem())

def select_quality(video_url):
    """
    Allows the user to select the quality of the video to play from the given URL

    Args:
        video_url (str): URL of the video to play
    """

    # Handle quality selection via dialog
    qualities = ['Auto', '1080p', '720p', '480p', '360p', '240p']
    dialog = xbmcgui.Dialog()
    selected = dialog.select('Vyberte kvalitu', qualities)

    if selected >= 0:  # If user didn't cancel
        quality = qualities[selected]
        # Create a new list item and play it
        play_item = xbmcgui.ListItem(path=get_url(action='play', video_url=video_url, quality=quality))
        xbmc.Player().play(item=get_url(action='play', video_url=video_url, quality=quality), listitem=play_item)

def skip_yt_part(video_url):
    """
    Skips a specific part of a YouTube video based on the provided URL

    Args:
        video_url (str): URL of the YouTube video to play
    """

    try:
        # Get the skip time from settings (in minutes)
        skip_time = int(_ADDON.getSetting('skip_yt_time'))

        # Convert minutes to seconds for the seek parameter
        seek_time = skip_time * 60

        # Create a new list item and play it with the seek time
        play_item = xbmcgui.ListItem(path=get_url(action='play', video_url=video_url))
        play_item.setProperty('StartOffset', str(seek_time))

        # Start playback from the specified time
        xbmc.Player().play(item=get_url(action='play', video_url=video_url), listitem=play_item)

        return True
    except Exception as e:
        log(f'Error in skip_yt_part: {str(e)}', xbmc.LOGERROR)
        return False

def yt_live():
    """
    Create directory item for YouTube live streams

    Note: This function requires the YouTube addon to be installed
    """

    try:
        # Check if YouTube addon is installed
        import xbmcaddon
        try:
            youtube_addon = xbmcaddon.Addon('plugin.video.youtube')
        except:
            log("YouTube addon not installed", xbmc.LOGERROR)
            xbmcgui.Dialog().ok('Chyba', 'Doplněk YouTube není nainstalován, nainstalujte jej pro zobrazení živých streamů.')
            return False

        # STANDASHOW YouTube channel ID
        # https://www.youtube.com/@StandaShow
        # https://www.youtube.com/channel/UCeDNCzyWtX6Y1ThbVuxbrtw
        channel_id = 'UCeDNCzyWtX6Y1ThbVuxbrtw'

        # Construct the URL for the live streams page
        youtube_url = f'plugin://plugin.video.youtube/channel/{channel_id}/live/'

        log(f"Creating directory item for YouTube URL: {youtube_url}", xbmc.LOGINFO)

        # Create a list item for the live streams
        list_item = xbmcgui.ListItem(label='Živé vysílání')
        list_item.setInfo('video', {'Title': 'Živé vysílání',
                                    'Plot': 'Živé streamy na YouTube kanálu [COLOR limegreen]STANDASHOW[/COLOR].\n\n[COLOR slategrey]Poznámka: Otevře doplněk YouTube v sekci živých přenosů na kanálu @StandaShow.[/COLOR]'})

        # Add the directory item
        xbmcplugin.addDirectoryItem(_HANDLE, youtube_url, list_item, isFolder=True)

        # you're creating a direct link to the YouTube plugin (plugin://plugin.video.youtube/...).
        # When you do this, you're essentially jumping to a different plugin, which breaks the natural directory hierarchy tracking.
        ADDON_NAME = _ADDON.getAddonInfo('name')
        plugin_category = f'{ADDON_NAME} / Živě'

        # Set the plugin category and content type
        xbmcplugin.setPluginCategory(_HANDLE, plugin_category)
        xbmcplugin.endOfDirectory(_HANDLE)

        return True

    except Exception as e:
        log(f'Error in yt_live: {str(e)}', xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Chyba', str(e))
        return False

def resume_from_web(video_url):
    """
    Resume playback from the web position.

    Args:
        video_url (str): URL of the video to resume
    """

    try:
        web_position = check_web_resume(video_url)
        if web_position:
            # Convert seconds to readable time format
            hours = web_position // 3600
            minutes = (web_position % 3600) // 60
            seconds = web_position % 60

            if hours > 0:
                time_str = f'{hours}:{minutes:02d}:{seconds:02d}'
            else:
                time_str = f'{minutes}:{seconds:02d}'

            # Ask user if they want to resume from this position
            dialog = xbmcgui.Dialog()
            resume = dialog.yesno('Pokračovat v přehrávání', f'Chcete pokračovat v přehrávání od času {time_str}?')

            if resume:
                # Create a new list item with the start position
                play_item = xbmcgui.ListItem(path=get_url(action='play', video_url=video_url))
                play_item.setProperty('StartOffset', str(web_position))

                # Start playback from the specified time
                xbmc.Player().play(item=get_url(action='play', video_url=video_url), listitem=play_item)
                return True
            else:
                return False

        # No web position or user declined to resume
        dialog = xbmcgui.Dialog()
        start = dialog.yesno('Přehrát od začátku', 'Žádná uložená pozice sledování na webu.\nChcete spustit přehrávání od začátku?')

        if start:
            # Create a new list item without start position
            play_item = xbmcgui.ListItem(path=get_url(action='play', video_url=video_url))
            xbmc.Player().play(item=get_url(action='play', video_url=video_url), listitem=play_item)
            return True

        return False

    except Exception as e:
        log(f'Error in resume_from_web: {str(e)}', xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Chyba', str(e))
        return False

def check_web_resume(video_url):
    """
    Check if there's a resume point on the web.

    Args:
        video_url (str): URL of the video to check

    Returns:
        int: Web resume position in seconds

    Original JS code on the video page footer:
    initPlayerComponent({
        "videoTitle":"Marcel Kolaja: regulace AI, cookie lišty, TikTok a bezpečnost, monopoly na trhu a ochrana spotřebitele, papírová brčka...",
        "posterUrl":"https://static.talktv.cz/upload/videos/gl4vZ6yK-poster-sGox3q.jpg",
        "videoId":1726,
        "debugMode":false,
        "overrideNative":true,
        "overrideChromecastSource":false,
        "overrideChromecastSourceOriginal":false,
        "canShowChromecastWarning":true,
        "canShowChromecastRevert":false,
        "videoFallbackUrl":"https://vz-b80bf3f2-495.b-cdn.net/bcdn_token=isq0PSmvxnfa054B4A9CTah_xT-L3gfS9OfvqCMp4do&expires=1735482522&token_path=%2Ffbed3ada-c002-475d-9545-d5e679746370/fbed3ada-c002-475d-9545-d5e679746370/play_720p.mp4",
    ->  "ssVideoPos":5899,
        "ssVideoTime":1735309692
    });
    """

    try:
        session = get_session()
        if not session:
            return None

        response = session.get(video_url)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'initPlayerComponent' in script.string:
                pos_match = re.search(r'"ssVideoPos":(\d+)', script.string)
                if pos_match:
                    return int(pos_match.group(1))
    except Exception as e:
        log(f"Error checking web resume point: {str(e)}", xbmc.LOGERROR)
    return None

def get_progress_monitor():
    """
    Get or create the progress monitor singleton instance.
    """

    global _progress_monitor
    with _monitor_lock:
        if _progress_monitor is None:
            _progress_monitor = ProgressMonitor()
            log("Created new ProgressMonitor instance", xbmc.LOGINFO)
        return _progress_monitor

class ProgressMonitor(xbmc.Player):
    """
    Progress monitor class to track video playback progress and send updates to the server.

    Note: This class extends the xbmc.Player class to inherit playback methods.
    """

    def __init__(self):
        super().__init__()
        self._video_id = None
        self.monitor = xbmc.Monitor()
        self.session = None
        self.stop_thread = False
        self.progress_thread = None
        self.initial_position = 0  # Add this new property
        log("ProgressMonitor initialized", xbmc.LOGINFO)

    @property
    def video_id(self):
        return self._video_id

    @video_id.setter
    def video_id(self, value):
        self._video_id = value
        if value:
            log(f"Video ID set to: {value}", xbmc.LOGINFO)
            self._start_monitoring()

    def _start_monitoring(self):
        # Start the monitoring thread.

        try:
            # Get a new session
            self.session = get_session()
            if not self.session:
                log("Failed to get session for monitoring", xbmc.LOGERROR)
                return

            # Stop existing thread if running
            if self.progress_thread and self.progress_thread.is_alive():
                log("Stopping existing progress thread", xbmc.LOGINFO)
                self.stop_thread = True
                self.progress_thread.join()

            # Start new monitoring thread
            self.stop_thread = False
            self.progress_thread = threading.Thread(target=self.monitor_progress)
            self.progress_thread.daemon = True
            self.progress_thread.start()
            log(f"Started progress monitoring thread for video {self.video_id}", xbmc.LOGINFO)
        except Exception as e:
            log(f"Error starting monitoring: {str(e)}", xbmc.LOGERROR)

    def cleanup(self):
        # Clean up resources and stop monitoring.

        log("Cleanup called", xbmc.LOGINFO)
        if self.progress_thread and self.progress_thread.is_alive():
            self.stop_thread = True
            self.progress_thread.join()
            log("Stopped progress monitoring thread", xbmc.LOGINFO)
        self.video_id = None
        self.session = None

    def monitor_progress(self):
        log("Starting progress monitoring loop", xbmc.LOGINFO)

        # Wait for playback to start
        attempt = 0
        while attempt < 10 and (not self.isPlaying() or not self.isPlayingVideo()):
            xbmc.sleep(1000)
            attempt += 1
            log(f"Waiting for playback to start (attempt {attempt})", xbmc.LOGINFO)

        # If we have an initial position and playback has started, seek to it
        if self.initial_position > 0 and self.isPlaying() and self.isPlayingVideo():
            log(f"Seeking to initial position: {self.initial_position}", xbmc.LOGINFO)
            self.seekTime(self.initial_position)
            xbmc.sleep(1000)  # Give time for seek to complete

        while not self.monitor.abortRequested() and not self.stop_thread:
            try:
                if self.video_id and self.session and self.isPlaying() and self.isPlayingVideo():
                    current_time = self.getTime()

                    # Only send updates if we have a valid time
                    if current_time > 0:
                        # Send progress update to server
                        log(f"Sending progress update for video {self.video_id} at position {int(current_time)}", xbmc.LOGINFO)
                        response = self.session.get(
                            'https://www.talktv.cz/srv/log-time',
                            params={
                                'vid': self.video_id,
                                'p': int(current_time),
                                't': int(time.time()),
                                's': 30
                            },
                            timeout=10
                        )

                        if response.status_code == 200:
                            log(f"Progress updated for video {self.video_id} at position {int(current_time)}", xbmc.LOGINFO)
                        else:
                            log(f"Failed to update progress: {response.status_code}", xbmc.LOGWARNING)
                else:
                    if not self.isPlaying() or not self.isPlayingVideo():
                        xbmc.sleep(1000)  # Wait a bit before checking again
                        continue
            except Exception as e:
                log(f"Error in progress monitoring: {str(e)}", xbmc.LOGWARNING)

            # Wait for 30 seconds before next update
            for _ in range(30):
                if self.monitor.waitForAbort(1) or self.stop_thread or not self.isPlaying():
                    return

        log("Progress monitoring loop ended", xbmc.LOGINFO)
        self.initial_position = 0
