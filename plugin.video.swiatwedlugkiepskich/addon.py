import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import requests
from urllib.parse import urlencode, parse_qsl
import json
import resolveurl

# Addon info
_addon = xbmcaddon.Addon()
_handle = int(sys.argv[1])
_url = sys.argv[0]

# URLs
DATABASE_URL = 'https://kiepski-player.web.app/database.json'
RATINGS_URL = 'https://kiepski-player.web.app/oceny.json'

def get_url(**kwargs):
    return '{}?{}'.format(_url, urlencode(kwargs))

def load_episodes_data():
    """Pobiera bazę odcinków z serwera"""
    try:
        response = requests.get(DATABASE_URL, timeout=10)
        response.raise_for_status()
        videos = response.json()

        # Próba pobrania ocen
        try:
            ratings_response = requests.get(RATINGS_URL, timeout=5)
            ratings = ratings_response.json() if ratings_response.status_code == 200 else []
        except:
            ratings = []

        return videos, ratings
    except Exception as e:
        xbmcgui.Dialog().notification('Błąd', 'Nie można pobrać bazy odcinków: {}'.format(str(e)), xbmcgui.NOTIFICATION_ERROR)
        return [], []

def build_seasons_structure(videos):
    """Grupuje odcinki w sezony"""
    seasons = {}

    for video in videos:
        # Próba wydobycia numeru sezonu z daty premiery lub innej metadanych
        # Ponieważ nie ma jawnej informacji o sezonie, grupujemy po latach
        release_date = video.get('release_date', '')

        # Pobierz rok z daty (format: DD.MM.YYYY)
        if release_date and '.' in release_date:
            parts = release_date.split('.')
            if len(parts) >= 3:
                year = parts[2]
                season_key = 'Sezon {} ({})'.format(len([s for s in seasons if year in s]) + 1, year)
            else:
                season_key = 'Pozostałe'
        else:
            season_key = 'Pozostałe'

        # Prostsze grupowanie - po 26 odcinków na sezon (typowo dla polskich seriali)
        episode_num = video.get('n', 0)
        season_num = ((episode_num - 1) // 26) + 1
        season_key = 'Sezon {}'.format(season_num)

        if season_key not in seasons:
            seasons[season_key] = []

        seasons[season_key].append(video)

    return seasons

def list_categories():
    xbmcplugin.setPluginCategory(_handle, 'Świat Według Kiepskich')
    xbmcplugin.setContent(_handle, 'videos')

    videos, ratings = load_episodes_data()

    if not videos:
        xbmcplugin.endOfDirectory(_handle)
        return

    # Opcja: Wszystkie odcinki
    list_item = xbmcgui.ListItem(label='Wszystkie odcinki (1-{})'.format(len(videos)))
    list_item.setInfo('video', {'title': 'Wszystkie odcinki', 'mediatype': 'video'})
    url = get_url(action='all_episodes')
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    # Sezony
    seasons = build_seasons_structure(videos)
    for season_name in sorted(seasons.keys(), key=lambda x: int(x.split()[1]) if x.split()[1].isdigit() else 999):
        # Dodaj zero wiodące do nazwy sezonu (Sezon 01, Sezon 02, etc.)
        season_parts = season_name.split()
        if len(season_parts) >= 2 and season_parts[1].isdigit():
            season_num = int(season_parts[1])
            display_name = 'Sezon {:02d}'.format(season_num)
        else:
            display_name = season_name

        list_item = xbmcgui.ListItem(label=display_name)
        list_item.setInfo('video', {
            'title': display_name,
            'mediatype': 'season'
        })
        url = get_url(action='season', season=season_name)
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    xbmcplugin.endOfDirectory(_handle)

def list_all_episodes():
    xbmcplugin.setPluginCategory(_handle, 'Wszystkie odcinki')
    xbmcplugin.setContent(_handle, 'episodes')

    videos, ratings = load_episodes_data()

    if not videos:
        xbmcplugin.endOfDirectory(_handle)
        return

    # Sortowanie po numerze odcinka
    videos_sorted = sorted(videos, key=lambda v: v.get('n', 0))

    for video in videos_sorted:
        add_episode_item(video, ratings)

    xbmcplugin.endOfDirectory(_handle)

def list_season_episodes(season_name):
    xbmcplugin.setPluginCategory(_handle, season_name)
    xbmcplugin.setContent(_handle, 'episodes')

    videos, ratings = load_episodes_data()

    if not videos:
        xbmcplugin.endOfDirectory(_handle)
        return

    seasons = build_seasons_structure(videos)
    season_videos = seasons.get(season_name, [])

    # Sortowanie po numerze odcinka
    season_videos_sorted = sorted(season_videos, key=lambda v: v.get('n', 0))

    for video in season_videos_sorted:
        add_episode_item(video, ratings)

    xbmcplugin.endOfDirectory(_handle)

def add_episode_item(video, ratings):
    """Dodaje pojedynczy odcinek do listy"""
    ep_num = video.get('n', 0)
    title = video.get('title', 'Odcinek {}'.format(ep_num))

    # Znajdź ocenę
    rating_obj = next((r for r in ratings if r.get('n') == ep_num), None)
    rating_text = rating_obj.get('o', '') if rating_obj else ''

    # Tytuł z oceną
    display_title = 'Odc. {} - {}'.format(ep_num, title)
    if rating_text:
        display_title += ' [COLOR yellow]({})[/COLOR]'.format(rating_text)

    list_item = xbmcgui.ListItem(label=display_title)

    # Metadata
    info_labels = {
        'title': title,
        'episode': ep_num,
        'mediatype': 'episode',
        'plot': video.get('description', ''),
        'duration': parse_duration(video.get('duration', '')),
        'director': video.get('director', ''),
        'premiered': format_date(video.get('release_date', ''))
    }

    if rating_text:
        try:
            # Konwersja polskiego formatu (4,5) na float
            rating_float = float(rating_text.replace(',', '.'))
            info_labels['rating'] = rating_float
        except:
            pass

    list_item.setInfo('video', info_labels)
    list_item.setProperty('IsPlayable', 'true')

    url = get_url(action='play', episode=ep_num)
    xbmcplugin.addDirectoryItem(_handle, url, list_item, False)

def parse_duration(duration_str):
    """Konwertuje czas trwania na sekundy (np. '25 min' -> 1500)"""
    if not duration_str:
        return 0

    try:
        # Zakładając format "XX min"
        duration_str = duration_str.replace('min', '').strip()
        minutes = int(duration_str)
        return minutes * 60
    except:
        return 0

def format_date(date_str):
    """Konwertuje datę z DD.MM.YYYY na YYYY-MM-DD"""
    if not date_str or '.' not in date_str:
        return ''

    try:
        parts = date_str.split('.')
        if len(parts) == 3:
            return '{}-{}-{}'.format(parts[2], parts[1].zfill(2), parts[0].zfill(2))
    except:
        pass

    return ''

def get_video_url(episode_num):
    """Pobiera URL do video z bazy danych"""
    try:
        videos, _ = load_episodes_data()

        # Znajdź odcinek
        video = next((v for v in videos if v.get('n') == episode_num), None)

        if not video:
            xbmcgui.Dialog().notification('Błąd', 'Nie znaleziono odcinka #{}'.format(episode_num), xbmcgui.NOTIFICATION_ERROR)
            return None

        # Pobierz link do video
        video_link = video.get('link', '')

        if not video_link:
            xbmcgui.Dialog().notification('Błąd', 'Brak linku do odcinka', xbmcgui.NOTIFICATION_ERROR)
            return None

        # Konwertuj link na embed (jak robi to strona)
        embed_link = video_link.replace('/video/', '/videoembed/')

        return embed_link

    except Exception as e:
        xbmcgui.Dialog().notification('Błąd', 'Błąd: {}'.format(str(e)), xbmcgui.NOTIFICATION_ERROR)
        return None

def play_video(episode_num):
    video_url = get_video_url(episode_num)

    if video_url:
        # Użyj ResolveURL do rozwiązania linku VK
        try:
            resolved = resolveurl.resolve(video_url)
            if resolved:
                video_url = resolved
        except Exception as e:
            # Jeśli ResolveURL nie zadziałał, użyj oryginalnego linku
            pass

        play_item = xbmcgui.ListItem(path=video_url)
        play_item.setProperty('IsPlayable', 'true')
        xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)
    else:
        xbmcplugin.setResolvedUrl(_handle, False, listitem=xbmcgui.ListItem())

def router(paramstring):
    params = dict(parse_qsl(paramstring))

    if not params:
        list_categories()
    elif params['action'] == 'all_episodes':
        list_all_episodes()
    elif params['action'] == 'season':
        list_season_episodes(params['season'])
    elif params['action'] == 'play':
        play_video(int(params['episode']))
    else:
        raise ValueError('Invalid paramstring: {}!'.format(paramstring))

if __name__ == '__main__':
    router(sys.argv[2][1:])