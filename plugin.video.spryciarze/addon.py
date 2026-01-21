"""
Wtyczka Kodi dla Spryciarze.pl
Autor: Claude AI
Wersja: 1.0.4
"""

import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc
import re
import ssl
from urllib.parse import urlencode, parse_qsl, urljoin
try:
    from urllib.request import urlopen, Request
except ImportError:
    from urllib2 import urlopen, Request

_handle = int(sys.argv[1])
_addon = xbmcaddon.Addon()
BASE_URL = 'https://www.spryciarze.pl'

MAIN_CATEGORIES = [
    {'name': 'Komputery', 'url': 'https://komputery.spryciarze.pl/kategorie', 'type': 'category'},
    {'name': 'Kulinaria', 'url': 'https://kulinaria.spryciarze.pl/kategorie', 'type': 'category'},
    {'name': 'Kobieta', 'url': 'https://kobieta.spryciarze.pl/kategorie', 'type': 'category'},
    {'name': 'Sport', 'url': 'https://sport.spryciarze.pl/kategorie', 'type': 'category'},
    {'name': 'Dom i ogród', 'url': BASE_URL + '/kategorie/dom-i-ogrod', 'type': 'videos'},
    {'name': 'Edukacja', 'url': BASE_URL + '/kategorie/edukacja', 'type': 'videos'},
    {'name': 'Eksperymenty', 'url': BASE_URL + '/kategorie/eksperymenty', 'type': 'videos'},
    {'name': 'Gadżety', 'url': BASE_URL + '/kategorie/gadzety', 'type': 'videos'},
    {'name': 'Hobby', 'url': BASE_URL + '/kategorie/hobby', 'type': 'videos'},
    {'name': 'Magia i sztuczki', 'url': BASE_URL + '/kategorie/magia-i-sztuczki', 'type': 'videos'},
    {'name': 'Majsterkowanie', 'url': BASE_URL + '/kategorie/majsterkowanie', 'type': 'videos'},
    {'name': 'Moda męska', 'url': BASE_URL + '/kategorie/moda-meska', 'type': 'videos'},
    {'name': 'Motoryzacja', 'url': BASE_URL + '/kategorie/motoryzacja', 'type': 'videos'},
    {'name': 'Muzyka', 'url': BASE_URL + '/kategorie/muzyka', 'type': 'videos'},
    {'name': 'Zdrowie', 'url': BASE_URL + '/kategorie/zdrowie', 'type': 'videos'},
    {'name': 'Różności', 'url': BASE_URL + '/kategorie/roznosci', 'type': 'videos'},
    {'name': 'Sztuka i Rzemiosło', 'url': BASE_URL + '/kategorie/sztuka-i-rzemioslo', 'type': 'videos'},
    {'name': 'Telefony komórkowe', 'url': BASE_URL + '/kategorie/telefony-komorkowe', 'type': 'videos'},
    {'name': 'Survival', 'url': BASE_URL + '/kategorie/survival', 'type': 'videos'},
]

def get_url(**kwargs):
    return '{}?{}'.format(sys.argv[0], urlencode(kwargs))



def fetch_page(url):
    try:
        context = ssl._create_unverified_context()
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        req = Request(url, headers=headers)
        response = urlopen(req, context=context, timeout=30)
        html = response.read().decode('utf-8')
        return html
    except Exception as e:
        xbmc.log('Blad pobierania strony ' + url + ': ' + str(e), xbmc.LOGERROR)
        return None

def extract_youtube_id(url):
    patterns = [
        r'youtube\.com/watch\?v=([^&]+)',
        r'youtu\.be/([^?]+)',
        r'youtube\.com/embed/([^?]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def parse_videos(html, base_url):
    videos = []
    pattern = r'href="([^"]*?/zobacz/[^"]+)"[^>]*>.*?<img[^>]+src="([^"]+)"[^>]*alt="([^"]+)"'
    matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)

    for match in matches:
        relative_url, relative_thumbnail, title = match
        full_url = urljoin(base_url, relative_url)
        full_thumbnail = urljoin(base_url, relative_thumbnail)
        videos.append({'title': title.strip(), 'url': full_url, 'thumbnail': full_thumbnail})

    return videos

def parse_subcategories(html, base_url):
    categories = []
    pattern = r'<a\s+href="([^"]+)"[^>]*>\s*([^<\(]+?)(?:\s*\((\d+)\))?\s*</a>'
    matches = re.findall(pattern, html, re.IGNORECASE)

    seen = set()
    for match in matches:
        relative_url, name, count = match

        if '/kategorie/' in relative_url and len(name.strip()) > 0:
            full_url = urljoin(base_url, relative_url)
            title = name.strip()

            if full_url not in seen and len(title) > 1 and title not in ['Kategorie', 'Wszystkie']:
                if count:
                    title += ' (' + count + ')'
                categories.append({'name': title, 'url': full_url})
                seen.add(full_url)

    return categories

def get_video_url(page_url):
    html = fetch_page(page_url)
    if not html:
        xbmc.log('get_video_url: Nie udalo sie pobrac strony', xbmc.LOGERROR)
        return None

    xbmc.log('get_video_url: Pobrano strone', xbmc.LOGDEBUG)

    spryciarze_pattern = r'<iframe[^>]+src=["\']https?://player\.spryciarze\.pl/embed/([^"\']+)["\']'
    match = re.search(spryciarze_pattern, html, re.IGNORECASE)
    if match:
        embed_id = match.group(1)
        xbmc.log('get_video_url: Znaleziono Spryciarze player: ' + embed_id, xbmc.LOGINFO)

        embed_url = 'https://player.spryciarze.pl/embed/' + embed_id
        embed_html = fetch_page(embed_url)

        if embed_html:
            youtube_patterns = [
                r'youtube\.com/embed/([A-Za-z0-9_-]{11})',
                r'youtube\.com/watch\?v=([A-Za-z0-9_-]{11})',
                r'youtu\.be/([A-Za-z0-9_-]{11})',
            ]

            for yt_pattern in youtube_patterns:
                yt_match = re.search(yt_pattern, embed_html, re.IGNORECASE)
                if yt_match:
                    video_id = yt_match.group(1)
                    xbmc.log('get_video_url: YouTube ID w embedzie: ' + video_id, xbmc.LOGINFO)
                    return 'plugin://plugin.video.youtube/play/?video_id=' + video_id

            mp4_patterns = [
                r'["\']([^"\']+\.mp4[^"\']*)["\']',
                r'src:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
            ]

            for mp4_pattern in mp4_patterns:
                mp4_match = re.search(mp4_pattern, embed_html, re.IGNORECASE)
                if mp4_match:
                    video_url = mp4_match.group(1)
                    xbmc.log('get_video_url: Surowy MP4: ' + video_url, xbmc.LOGDEBUG)
                    
                    video_url = video_url.replace('\\', '')
                    if video_url.startswith('//'):
                        video_url = 'https:' + video_url

                    xbmc.log('get_video_url: MP4 po normalizacji: ' + video_url, xbmc.LOGINFO)
                    return video_url

    youtube_patterns = [
        r'<iframe[^>]+src=["\']([^"\']*youtube[^"\']*)["\']',
        r'["\']https?://(?:www\.)?youtube\.com/embed/([A-Za-z0-9_-]{11})["\']',
    ]

    for pattern in youtube_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        for match in matches:
            if 'youtube' in match.lower():
                video_id = extract_youtube_id(match)
                if video_id:
                    xbmc.log('get_video_url: YouTube ID: ' + video_id, xbmc.LOGINFO)
                    return 'plugin://plugin.video.youtube/play/?video_id=' + video_id
            elif len(match) == 11:
                xbmc.log('get_video_url: Direct ID: ' + match, xbmc.LOGINFO)
                return 'plugin://plugin.video.youtube/play/?video_id=' + match

    xbmc.log('get_video_url: Nie znaleziono wideo', xbmc.LOGERROR)
    return None

def list_categories():
    xbmcplugin.setPluginCategory(_handle, 'Kategorie')
    xbmcplugin.setContent(_handle, 'videos')

    for category in MAIN_CATEGORIES:
        list_item = xbmcgui.ListItem(label=category['name'])
        list_item.setArt({'thumb': '', 'icon': '', 'fanart': ''})

        info_tag = list_item.getVideoInfoTag()
        info_tag.setTitle(category['name'])
        info_tag.setMediaType('video')

        if category['type'] == 'category':
            url = get_url(action='subcategories', url=category['url'])
            is_folder = True
        else:
            url = get_url(action='videos', url=category['url'])
            is_folder = True

        xbmcplugin.addDirectoryItem(_handle, url, list_item, is_folder)

    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    xbmcplugin.endOfDirectory(_handle)

def list_subcategories(url):
    html = fetch_page(url)
    if not html:
        xbmcgui.Dialog().notification('Spryciarze.pl', 'Blad pobierania kategorii', xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(_handle, succeeded=False)
        return

    xbmcplugin.setPluginCategory(_handle, 'Podkategorie')
    xbmcplugin.setContent(_handle, 'videos')

    subcategories = parse_subcategories(html, url)

    for subcat in subcategories:
        list_item = xbmcgui.ListItem(label=subcat['name'])
        list_item.setArt({'thumb': '', 'icon': '', 'fanart': ''})

        info_tag = list_item.getVideoInfoTag()
        info_tag.setTitle(subcat['name'])
        info_tag.setMediaType('video')

        url = get_url(action='videos', url=subcat['url'])
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    xbmcplugin.endOfDirectory(_handle)

def list_videos(url, page=1):
    if page > 1:
        url = url.rstrip('/') + '/page:' + str(page)

    html = fetch_page(url)
    if not html:
        xbmcgui.Dialog().notification('Spryciarze.pl', 'Blad pobierania filmow', xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(_handle, succeeded=False)
        return

    xbmcplugin.setPluginCategory(_handle, 'Filmy')
    xbmcplugin.setContent(_handle, 'videos')

    videos = parse_videos(html, url)

    for video in videos:
        list_item = xbmcgui.ListItem(label=video['title'])
        list_item.setArt({'thumb': video['thumbnail'], 'icon': video['thumbnail'], 'fanart': video['thumbnail']})

        info_tag = list_item.getVideoInfoTag()
        info_tag.setTitle(video['title'])
        info_tag.setMediaType('video')

        list_item.setProperty('IsPlayable', 'true')

        url = get_url(action='play', url=video['url'])
        xbmcplugin.addDirectoryItem(_handle, url, list_item, False)

    if len(videos) >= 12:
        list_item = xbmcgui.ListItem(label='[Nastepna strona]')
        url_base = url.split('/page:')[0] if '/page:' in url else url
        url = get_url(action='videos', url=url_base, page=str(page + 1))
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    xbmcplugin.endOfDirectory(_handle)

def play_video(url):
    xbmc.log('play_video: Proba odtworzenia: ' + url, xbmc.LOGINFO)

    video_url = get_video_url(url)

    if video_url:
        xbmc.log('play_video: Final URL: ' + video_url, xbmc.LOGINFO)
        play_item = xbmcgui.ListItem(path=video_url)
        xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)
    else:
        xbmc.log('play_video: Nie znaleziono video URL', xbmc.LOGERROR)
        xbmcgui.Dialog().ok('Spryciarze.pl', 'Nie mozna znalezc filmu.')
        xbmcplugin.setResolvedUrl(_handle, False, listitem=xbmcgui.ListItem())

def router(paramstring):
    params = dict(parse_qsl(paramstring))

    if not params:
        list_categories()
    elif params['action'] == 'subcategories':
        list_subcategories(params['url'])
    elif params['action'] == 'videos':
        page = int(params.get('page', 1))
        list_videos(params['url'], page)
    elif params['action'] == 'play':
        play_video(params['url'])
    else:
        raise ValueError('Nieprawidlowy parametr: ' + paramstring)

if __name__ == '__main__':
    router(sys.argv[2][1:])