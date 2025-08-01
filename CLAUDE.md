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
- `resources/lib/webconfig.py` - Web server for easier PHPSESSID configuration
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

### Video Streaming
Supports both HLS (adaptive) and MP4 streams with quality selection. Features YouTube part skipping and position synchronization with the web platform.

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
1. Via web configuration interface (preferred)
2. Manual DevTools extraction

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

## Localization

Plugin is Czech-only (`lang="cs"`) as it targets Czech TALK.cz content exclusively.