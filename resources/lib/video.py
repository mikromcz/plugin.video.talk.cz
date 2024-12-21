import xbmc
import xbmcgui
import xbmcplugin
from bs4 import BeautifulSoup
from .constants import _HANDLE, _ADDON
from .utils import get_url, log
from .auth import get_session

def select_quality(video_url):
    # Handle quality selection via dialog
    qualities = ['Auto', '1080p', '720p', '480p', '360p', '240p']
    dialog = xbmcgui.Dialog()
    selected = dialog.select('Vyberte kvalitu', qualities)

    if selected >= 0:  # If user didn't cancel
        quality = qualities[selected]
        # Create a new list item and play it
        play_item = xbmcgui.ListItem(path=get_url(action='play', video_url=video_url, quality=quality))
        xbmc.Player().play(item=get_url(action='play', video_url=video_url, quality=quality), listitem=play_item)

def play_video(video_url, requested_quality=None):
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

        # Fallback to first available source if nothing else matched
        if not selected_url and sources:
            selected_url = sources[0]['src']
            log("Falling back to first available source", xbmc.LOGWARNING)

        if not selected_url:
            log("No playable source found", xbmc.LOGERROR)
            xbmcplugin.setResolvedUrl(_HANDLE, False, xbmcgui.ListItem())
            return

        # Setup playback
        play_item = xbmcgui.ListItem(path=selected_url)

        # If we came from search results, set the parent directory to include the search URL
        search_url = xbmc.getInfoLabel('Container.FolderPath')
        if 'search_url=' in search_url:
            play_item.setProperty('IsPlayable', 'true')
            play_item.setProperty('ParentFolder', search_url)

        # Configure inputstream
        if use_hls:
            play_item.setMimeType('application/x-mpegURL')
            play_item.setProperty('inputstream', 'inputstream.adaptive')
            #play_item.setProperty('inputstream.adaptive.manifest_type', 'hls') # Warning "inputstream.adaptive.manifest_type" property is deprecated and will be removed next Kodi version, the manifest type is now automatically detected.
        else:
            play_item.setMimeType('video/mp4')

        play_item.setContentLookup(False)

        # Add metadata if available
        try:
            details = soup.find('div', class_='details__info')
            if details:
                description = details.text.strip().split('                -', 1)[-1].strip()
                title = soup.find('h1', class_='details__header')
                if title:
                    title = title.text.strip()

                info_tag = play_item.getVideoInfoTag()
                info_tag.setMediaType('video')
                info_tag.setPlot(description)

                if title:
                    info_tag.setTitle(title)

        except Exception as e:
            log(f"Failed to set video metadata: {str(e)}", xbmc.LOGWARNING)

        # Start playback
        xbmcplugin.setResolvedUrl(_HANDLE, True, listitem=play_item)

    except Exception as e:
        log(f"Error during video playback setup: {str(e)}", xbmc.LOGERROR)
        xbmcplugin.setResolvedUrl(_HANDLE, False, xbmcgui.ListItem())