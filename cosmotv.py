import sys
import re
from urllib.parse import urljoin, parse_qs
import xbmcgui
import xbmcplugin
import xbmcaddon

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    xbmcgui.Dialog().ok("Dulo Player", "Required modules missing.\nInstall: requests, beautifulsoup4")
    sys.exit(1)

# Addon settings
addon = xbmcaddon.Addon()
addon_id = addon.getAddonInfo('id')
addon_handle = int(sys.argv[1])
args = parse_qs(sys.argv[2].lstrip('?'))

# Base URL
BASE_URL = "https://dulo.tv"
SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'Mozilla/5.0'})

def log(msg, level=xbmc.LOGINFO):
    """Log messages to Kodi."""
    xbmc.log(f"[{addon_id}] {msg}", level)

def get_page(url):
    """Fetch and parse HTML."""
    try:
        resp = SESSION.get(url, timeout=10)
        resp.raise_for_status()
        return BeautifulSoup(resp.content, 'html.parser')
    except Exception as e:
        log(f"Error fetching {url}: {e}", xbmc.LOGERROR)
        return None

def scrape_movies():
    """Scrape movies from dulo.tv."""
    soup = get_page(f"{BASE_URL}/movies")
    if not soup:
        return []
    
    movies = []
    # Adjust selector based on actual site structure
    for item in soup.select('[class*="movie-item"], [class*="film-card"]')[:50]:
        try:
            title_elem = item.select_one('h2, h3, [class*="title"]')
            link_elem = item.select_one('a')
            img_elem = item.select_one('img')
            
            title = title_elem.get_text(strip=True) if title_elem else "Unknown"
            url = link_elem.get('href') if link_elem else None
            poster = img_elem.get('src') or img_elem.get('data-src') if img_elem else ""
            
            if url:
                url = urljoin(BASE_URL, url)
                movies.append({
                    'title': title,
                    'url': url,
                    'poster': urljoin(BASE_URL, poster) if poster else "",
                    'type': 'movie'
                })
        except Exception as e:
            log(f"Error parsing movie item: {e}")
            continue
    
    return movies

def scrape_tvshows():
    """Scrape TV shows from dulo.tv."""
    soup = get_page(f"{BASE_URL}/series")
    if not soup:
        return []
    
    tvshows = []
    # Adjust selector based on actual site structure
    for item in soup.select('[class*="tv-item"], [class*="serie-card"]')[:50]:
        try:
            title_elem = item.select_one('h2, h3, [class*="title"]')
            link_elem = item.select_one('a')
            img_elem = item.select_one('img')
            
            title = title_elem.get_text(strip=True) if title_elem else "Unknown"
            url = link_elem.get('href') if link_elem else None
            poster = img_elem.get('src') or img_elem.get('data-src') if img_elem else ""
            
            if url:
                url = urljoin(BASE_URL, url)
                tvshows.append({
                    'title': title,
                    'url': url,
                    'poster': urljoin(BASE_URL, poster) if poster else "",
                    'type': 'tvshow'
                })
        except Exception as e:
            log(f"Error parsing TV show item: {e}")
            continue
    
    return tvshows

def get_episodes(tvshow_url):
    """Scrape episodes for a TV show."""
    soup = get_page(tvshow_url)
    if not soup:
        return []
    
    episodes = []
    # Adjust selector based on actual site structure
    for item in soup.select('[class*="episode"], [class*="ep-item"]')[:100]:
        try:
            title_elem = item.select_one('h4, h5, [class*="ep-title"]')
            link_elem = item.select_one('a')
            
            title = title_elem.get_text(strip=True) if title_elem else "Episode"
            url = link_elem.get('href') if link_elem else None
            
            if url:
                url = urljoin(BASE_URL, url)
                episodes.append({
                    'title': title,
                    'url': url,
                    'type': 'episode'
                })
        except Exception as e:
            log(f"Error parsing episode: {e}")
            continue
    
    return episodes

def extract_stream_url(content_url):
    """Extract playable stream URL from content page."""
    soup = get_page(content_url)
    if not soup:
        return None
    
    # Look for common video player patterns
    try:
        # Try iframe src (common pattern)
        iframe = soup.select_one('iframe')
        if iframe and iframe.get('src'):
            return iframe.get('src')
        
        # Try video tag src
        video = soup.select_one('video source')
        if video and video.get('src'):
            return video.get('src')
        
        # Try embedded player URLs
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and ('m3u8' in script.string or 'mp4' in script.string):
                match = re.search(r'(https?://[^\s"\']+\.(?:m3u8|mp4))', script.string)
                if match:
                    return match.group(1)
    except Exception as e:
        log(f"Error extracting stream URL: {e}")
    
    return None

def add_directory_item(title, url, thumb="", isFolder=True, info=None):
    """Add item to Kodi directory."""
    item = xbmcgui.ListItem(label=title)
    item.setArt({'thumb': thumb, 'poster': thumb})
    
    if info:
        item.setInfo('video', info)
    
    xbmcplugin.addDirectoryItem(
        addon_handle,
        url,
        item,
        isFolder=isFolder
    )

def main_menu():
    """Display main menu."""
    items = [
        ("Movies", "movies"),
        ("TV Shows", "tvshows")
    ]
    
    for title, mode in items:
        url = f"plugin://{addon_id}/?mode={mode}"
        add_directory_item(title, url, isFolder=True)
    
    xbmcplugin.endOfDirectory(addon_handle)

def show_movies():
    """Display movies list."""
    movies = scrape_movies()
    
    if not movies:
        xbmcgui.Dialog().notification("No Movies", "Could not fetch movies")
        xbmcplugin.endOfDirectory(addon_handle)
        return
    
    for movie in movies:
        url = f"plugin://{addon_id}/?mode=play&url={movie['url']}"
        add_directory_item(
            movie['title'],
            url,
            thumb=movie['poster'],
            isFolder=False,
            info={'mediatype': 'movie', 'title': movie['title']}
        )
    
    xbmcplugin.endOfDirectory(addon_handle)

def show_tvshows():
    """Display TV shows list."""
    tvshows = scrape_tvshows()
    
    if not tvshows:
        xbmcgui.Dialog().notification("No TV Shows", "Could not fetch TV shows")
        xbmcplugin.endOfDirectory(addon_handle)
        return
    
    for tvshow in tvshows:
        url = f"plugin://{addon_id}/?mode=episodes&url={tvshow['url']}"
        add_directory_item(
            tvshow['title'],
            url,
            thumb=tvshow['poster'],
            isFolder=True,
            info={'mediatype': 'tvshow', 'title': tvshow['title']}
        )
    
    xbmcplugin.endOfDirectory(addon_handle)

def show_episodes(tvshow_url):
    """Display episodes for a TV show."""
    episodes = get_episodes(tvshow_url)
    
    if not episodes:
        xbmcgui.Dialog().notification("No Episodes", "Could not fetch episodes")
        xbmcplugin.endOfDirectory(addon_handle)
        return
    
    for episode in episodes:
        url = f"plugin://{addon_id}/?mode=play&url={episode['url']}"
        add_directory_item(
            episode['title'],
            url,
            isFolder=False,
            info={'mediatype': 'episode', 'title': episode['title']}
        )
    
    xbmcplugin.endOfDirectory(addon_handle)

def play_content(content_url):
    """Play video content."""
    stream_url = extract_stream_url(content_url)
    
    if not stream_url:
        xbmcgui.Dialog().ok("Error", "Could not extract stream URL")
        return
    
    item = xbmcgui.ListItem(path=stream_url)
    xbmcplugin.setResolvedURL(addon_handle, True, item)

# Route handling
if __name__ == '__main__':
    mode = args.get('mode', [None])[0]
    
    if mode == 'movies':
        show_movies()
    elif mode == 'tvshows':
        show_tvshows()
    elif mode == 'episodes':
        tvshow_url = args.get('url', [None])[0]
        if tvshow_url:
            show_episodes(tvshow_url)
    elif mode == 'play':
        content_url = args.get('url', [None])[0]
        if content_url:
            play_content(content_url)
    else:
        main_menu()
