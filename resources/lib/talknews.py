import xbmc
import xbmcgui
import xbmcplugin
from bs4 import BeautifulSoup
from .auth import require_session
from .constants import _HANDLE
from .utils import log, get_url, clean_text

def list_talknews():
    """
    Lists TALKNEWS headlines from the main TALKNEWS page

    Each headline is a separate item in the Kodi plugin
    The item contains the following information:
    - Title of the headline
    - Thumbnail image
    - Tag and meta information
    - URL to the article or info page
    """

    # Get a session for making HTTP requests
    session = require_session()
    if not session:
        xbmcplugin.endOfDirectory(_HANDLE, succeeded=False)
        return

    try:
        response = session.get('https://www.talktv.cz/talknews')
        if response.status_code != 200:
            log(f"Failed to fetch TALKNEWS page: {response.status_code}", xbmc.LOGERROR)
            return

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find both div and a tags with embed__item class
        news_items = soup.find_all(['div', 'a'], class_='embed__item')

        for item in news_items:
            # Get meta text if exists
            meta = item.find('div', class_='embed__meta')
            meta_text = meta.get_text(strip=True) if meta else ""

            # Get title element
            title_elem = item.find('h2')
            if not title_elem:
                continue

            # Get tag text if exists
            tag_elem = item.find('span', class_='embed__tag')
            tag_text = tag_elem.get_text(strip=True).upper() if tag_elem else ""

            # Add tag and meta to plot
            plot = f"[COLOR limegreen]{tag_text}[/COLOR]" if tag_text else ""
            if meta_text:
                plot = f"{plot}\n\n{meta_text}" if plot else meta_text

            title = clean_text(title_elem.text)
            title = f"[COLOR limegreen]{tag_text}[/COLOR] • {title} " if tag_text else title

            # Create a list item for the headline
            list_item = xbmcgui.ListItem(label=title)

            # Set plot and title
            info_tag = list_item.getVideoInfoTag()
            info_tag.setPlot(plot)
            info_tag.setTitle(title)
            info_tag.setMediaType('video')
            info_tag.setStudios(["TALKNEWS"])
            info_tag.setCountries(["Česká Republika"])

            # Set thumbnail image
            img_elem = item.find('img')
            if img_elem and img_elem.get('src'):
                thumbnail = img_elem['src']
                list_item.setArt({
                    'thumb': thumbnail,
                    'icon': thumbnail
                })

            # Check if item itself is a link or contains a link
            is_link = item.name == 'a'
            link = item if is_link else item.find('a', class_='embed__item')

            # Set URL and folder status
            if link and link.get('href'):
                url = get_url(action='talknews_article',
                            article_url=f"https://www.talktv.cz{link['href']}")
                is_folder = True
            else:
                url = get_url(action='talknews_info',
                            title=title,
                            meta=meta_text)
                is_folder = False

            xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)

        # Set plugin category and content type
        xbmcplugin.setPluginCategory(_HANDLE, 'TALKNEWS')
        xbmcplugin.setContent(_HANDLE, 'files')
        xbmcplugin.endOfDirectory(_HANDLE)

    except Exception as e:
        log(f"Error in list_talknews: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Chyba', 'Chyba při načítání TALKNEWS')

def show_article(article_url):
    """
    Shows a TALKNEWS article in a custom window

    Args:
        article_url (str): URL of the article to show
    """

    # Get a session for making HTTP requests
    session = require_session()
    if not session:
        xbmcplugin.endOfDirectory(_HANDLE, succeeded=False)
        return

    try:
        response = session.get(article_url)
        if response.status_code != 200:
            log(f"Failed to fetch article: {response.status_code}", xbmc.LOGERROR)
            return

        soup = BeautifulSoup(response.text, 'html.parser')

        content_div = soup.find('div', class_='post__content')
        if not content_div:
            log("Could not find article content", xbmc.LOGERROR)
            return

        # Format content with Kodi text formatting tags
        content = ""
        for element in content_div.children:
            if element.name == 'p':

                # Handle strong/bold text
                for text in element.children:
                    if text.name == 'strong':
                        content += f"[B]{text.get_text()}[/B]"
                    else:
                        content += text.get_text()

                content += "\n\n"

            elif element.name == 'h2':
                content += f"\n[COLOR limegreen][B]{element.get_text()}[/B][/COLOR]\n\n"

            elif element.name == 'ul':
                for li in element.find_all('li'):
                    content += f"[COLOR gray]•[/COLOR] {li.get_text()}\n"

                content += "\n"
            elif element.name == 'a':
                content += f"[COLOR dodgerblue]{element.get_text()}[/COLOR]"

        # Format title and date
        title = soup.find('h1', class_='post__title')
        title = title.get_text() if title else "Článek"

        # Add date to title if exists
        date = soup.find('div', class_='post__date')
        if date:
            title = f"[B]{title}[/B] • [I]{date.get_text()}[/I]"

        dialog = xbmcgui.Dialog()
        dialog.textviewer(title, content)

    except Exception as e:
        log(f"Error in show_article: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Chyba', 'Chyba při zobrazení článku')

def show_news_info(title, meta):
    """
    Shows a simple dialog with news information

    Args:
        title (str): Dialog title
        meta (str): Dialog content
    """

    content = title.replace(" • ", "\n").upper()
    if meta:
        content = f"{content}\n\n{meta}"

    dialog = xbmcgui.Dialog()
    dialog.ok('TALKNEWS', content)