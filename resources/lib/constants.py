import sys
import xbmcaddon

_URL = sys.argv[0]  # Base URL of the addon
_HANDLE = int(sys.argv[1])  # Handle for the Kodi plugin instance
_ADDON = xbmcaddon.Addon()  # Instance of the addon
ADDON_ID = xbmcaddon.Addon().getAddonInfo('id')  # ID of the addon