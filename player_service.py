import urllib.parse

def get_webapp_player_url(kinopoisk_id: int | str | None) -> str:
    """URL for embedded Telegram WebApp player."""
    if kinopoisk_id:
        return f"https://kinodivbox.github.io/?id={kinopoisk_id}"
    return "https://kinodivbox.github.io/"

def get_yandex_video_url(title: str, year: int | None = None, quality: str = "", movie_lang: str = "ru") -> str:
    lang_tag = "на русском"
    if movie_lang == "uz":
        lang_tag = "o'zbek tilida tarjima"
    elif movie_lang == "orig":
        lang_tag = "на английском с субтитрами"

    query = f"смотреть онлайн {title}"
    if year:
        query += f" {year}"
    if quality:
        query += f" {quality}"
    query += f" {lang_tag}"
    return f"https://yandex.ru/video/search?text={urllib.parse.quote(query)}"

def get_google_watch_url(title: str, year: int | None = None, movie_lang: str = "ru", quality: str = "1080p") -> str:
    if movie_lang == "uz":
        query = f"{title} {year or ''} ozbek tilida skachat kino {quality}".strip()
    else:
        query = f"смотреть фильм {title} {year or ''} {quality} онлайн бесплатно".strip()
    return f"https://www.google.com/search?q={urllib.parse.quote(query)}"

def get_telegram_channel_search(title: str, movie_lang: str = "ru") -> str:
    if movie_lang == "uz":
        query = f"{title} ozbek tilida kino"
    else:
        query = f"{title} фильм"
    return f"https://t.me/s?q={urllib.parse.quote(query)}"

def get_torrent_rutor_url(title: str, year: int | None = None, quality: str = "") -> str:
    query = title
    if year:
        query += f" {year}"
    if quality:
        query += f" {quality}"
    return f"https://rutor.info/search/0/0/0/0/{urllib.parse.quote(query)}"

def get_rutracker_url(title: str, year: int | None = None, quality: str = "") -> str:
    query = title
    if year:
        query += f" {year}"
    if quality:
        query += f" {quality}"
    return f"https://rutracker.org/forum/tracker.php?nm={urllib.parse.quote(query)}"

def get_kinopoisk_url(kinopoisk_id: int | str | None) -> str | None:
    if kinopoisk_id:
        return f"https://www.kinopoisk.ru/film/{kinopoisk_id}/"
    return None
