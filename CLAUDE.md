# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an unofficial Kodi video plugin for TALK.cz (formerly TALKTV.cz), a Czech podcast platform. The plugin provides access to premium content for authenticated users. The project was developed primarily using Claude.AI and serves subscribers of the TALK.cz platform.

## Architecture

### Entry Point & Routing
- `addon.py` - Main entry point containing the router that handles all actions and URL parameters
- `resources/lib/constants.py` - Contains addon globals, menu structures, and category definitions

### Core Modules
- `resources/lib/auth.py` - Authentication handling (PHPSESSID cookie-based)
- `resources/lib/menu.py` - Menu generation and video listing logic
- `resources/lib/video.py` - Video playback, quality selection, and streaming
- `resources/lib/search.py` - Search functionality across TALK.cz content
- `resources/lib/talknews.py` - TALKNEWS section (news articles and updates)
- `resources/lib/cache.py` - Caching system for video metadata and performance
- `resources/lib/webconfig.py` - Web server for easier PHPSESSID configuration (auto-shutdown after 10 minutes)
- `resources/lib/utils.py` - Utility functions for data processing and formatting

### Authentication System
The plugin uses PHPSESSID cookie authentication due to reCAPTCHA protection on the login page. Two methods available:
1. Manual cookie extraction from browser DevTools
2. Web configuration interface (`webconfig.py`) that runs a local server for easier setup

### Menu Structure
Main categories defined in `constants.py`:
- TALKNEWS - News and updates
- Latest Videos, Popular Videos, Top Videos
- Continue Watching (cross-platform position sync)
- Creators (STANDASHOW, TECH GUYS, JADRNÁ VĚDA, etc.)
- Archive & Video Lists
- Search functionality
- Live streams (via YouTube plugin)

### Video Streaming & Progress Monitoring
- Supports both HLS (adaptive) and MP4 streams with quality selection
- Features YouTube part skipping and position synchronization with the web platform
- `video.py` contains `ProgressMonitor` class that extends `xbmc.Player` with threaded progress tracking
- Progress monitoring uses singleton pattern with proper resource cleanup and thread management
- Implements context manager pattern (`__enter__`/`__exit__`) for safe resource handling
- Auto-cleanup with destructor methods and timeout protection for thread joins

### Background Monitoring System
- `monitor.py` contains `TalkNewsMonitor` class for background TALKNEWS monitoring
- Runs in daemon thread with configurable intervals (1-48 hours)
- Maintains session keep-alive functionality
- Smart notification system that avoids interrupting video playback
- Implements pending notification queue for post-playback display

## Development Commands

This is a Kodi plugin with no build system. Development workflow:

### Testing & Debugging
```bash
# Enable debug logging in plugin settings, then check Kodi logs
# Location varies by platform:
# Windows: %APPDATA%\Kodi\kodi.log
# Linux: ~/.kodi/temp/kodi.log
```

### Installation & Deployment
```bash
# Install as ZIP through Kodi interface or:
# Copy entire directory to Kodi addons folder:
# Windows: %APPDATA%\Kodi\addons\plugin.video.talk.cz\
# Linux: ~/.kodi/addons/plugin.video.talk.cz/
```

### Development Setup
- Kodi addon development requires Kodi installation for testing
- Use `dev/KodiPortable.exe` shortcut for development environment
- Plugin settings available at `resources/settings.xml`
- Debug logging can be enabled in plugin settings

## Key Configuration

### Required Dependencies (addon.xml)
- `xbmc.python` version 3.0.0+
- `script.module.requests` version 2.22.0+
- `script.module.beautifulsoup4` version 4.6.2+

### Authentication Setup
Users must provide PHPSESSID cookie from authenticated TALK.cz session:
1. Via web configuration interface (preferred) - `webconfig.py` runs local HTTP server with auto-shutdown after 10 minutes
2. Manual DevTools extraction

### Session Management
- `auth.py` implements session caching with 1-hour TTL to reduce validation requests
- Automatic session refresh during background monitoring
- Thread-safe session management with proper cleanup

### Important Settings
- `preferred_stream` - HLS (Adaptive) vs MP4
- `video_quality` - Auto, 1080p, 720p, 480p, 360p, 240p
- `skip_yt_time` - Minutes to skip YouTube portion (default: 22)
- `use_cache` - Enable metadata caching for performance

## API Integration

The plugin scrapes TALK.cz website and uses internal JSON APIs:
- Main video listings: `/srv/videos/home`
- Search: Various search endpoints
- Position tracking: `/srv/log-time` for watch progress sync
- Pagination: Different patterns for different content types

## File Structure Notes

- `resources/media/` - Custom icons and images for shows/categories
- `resources/screenshot-*.jpg` - Plugin screenshots for Kodi addon browser
- `dev/` - Development tools, notes, and shortcuts
- `dev/NOTES.md` - Detailed development notes and API documentation

## Error Handling & Logging

### Unified Error Handling Pattern
- Consistent pattern across all modules: `log()` + `xbmcgui.Dialog().notification()`
- Czech user notifications, English developer logs
- `utils.log()` provides automatic function name detection and traceback support
- Error notifications avoid interrupting video playback

### ListItem Enhancement
Recent improvements to Kodi integration include:
- Enhanced art properties (fanart, poster) for better visual presentation
- Rich metadata (genres, studios, countries, year extraction)
- Custom properties for advanced Kodi skins
- Unique IDs for external tool integration
- Cast member integration with profile images

## Resource Management

### Thread Safety
- Proper cleanup patterns implemented for all background threads
- Context manager support for `ProgressMonitor` class
- Global singleton management with thread-safe locks
- Timeout protection for thread joins to prevent blocking

### Memory Management
- Session cleanup with proper `session.close()` calls
- Destructor methods (`__del__`) for automatic resource cleanup
- Cache size management and TTL-based invalidation

### Web Configuration Server
- `webconfig.py` provides HTTP server on configurable port (default: 47447) for PHPSESSID setup
- Server includes auto-shutdown after 10 minutes to prevent resource waste
- Automatic setting disable when timeout occurs with user notification
- Serves HTML form at `/talk` endpoint with test and save functionality
- Enhanced socket configuration with `SO_REUSEADDR` and `SO_REUSEPORT` for port binding reliability

## Cast & Creator System

### Cast Member Integration
- `constants.py` defines cast members in dictionary format with optional profile images
- `utils.get_creator_cast()` supports both legacy string format and new dictionary format for backward compatibility
- Cast members appear in video information with profile pictures located in `resources/media/creator-*.jpg`

### Image Naming Convention
Creator profile images follow the pattern: `creator-[name-with-hyphens].jpg`
- Examples: `creator-standa-hruska.jpg`, `creator-kicom.jpg`, `creator-leos-kysa.jpg`
- Images are automatically converted to full Kodi paths via `utils.get_image_path()`
- Missing images gracefully fall back to empty string without breaking functionality

## Localization

Plugin is Czech-only (`lang="cs"`) as it targets Czech TALK.cz content exclusively.