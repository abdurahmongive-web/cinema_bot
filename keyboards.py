from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo
)
from locales import t
from player_service import (
    get_webapp_player_url,
    get_yandex_video_url,
    get_google_watch_url,
    get_telegram_channel_search,
    get_torrent_rutor_url,
    get_rutracker_url,
    get_kinopoisk_url
)
from ai_service import MovieInfo

def get_main_reply_keyboard(lang: str = "ru", is_admin: bool = False) -> ReplyKeyboardMarkup:
    kb = [
        [
            KeyboardButton(text=t("btn_evening", lang)),
            KeyboardButton(text=t("btn_thriller", lang))
        ],
        [
            KeyboardButton(text=t("btn_comedy", lang)),
            KeyboardButton(text=t("btn_scifi", lang))
        ],
        [
            KeyboardButton(text=t("btn_random", lang)),
            KeyboardButton(text=t("btn_help", lang))
        ],
        [
            KeyboardButton(text=t("btn_author", lang)),
            KeyboardButton(text=t("btn_lang", lang))
        ],
        [
            KeyboardButton(text=t("btn_movie_lang", lang))
        ]
    ]
    if is_admin:
        kb.append([KeyboardButton(text="🛠 Режим разработчика")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_language_inline_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="setlang:ru"),
            InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="setlang:uz")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_movie_lang_inline_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="🇷🇺 Русский перевод", callback_data="setmovielang:ru"),
            InlineKeyboardButton(text="🇺🇿 O'zbek tilida", callback_data="setmovielang:uz")
        ],
        [
            InlineKeyboardButton(text="🇬🇧 Original + Subs", callback_data="setmovielang:orig")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_movie_keyboard(movie: MovieInfo, user_lang: str = "ru", movie_lang: str = "ru") -> InlineKeyboardMarkup:
    buttons = []

    # 1. Main Watch Button (Telegram WebApp Player)
    if movie.kinopoisk_id:
        player_url = get_webapp_player_url(movie.kinopoisk_id)
        buttons.append([
            InlineKeyboardButton(
                text=t("btn_watch_player", user_lang),
                web_app=WebAppInfo(url=player_url)
            )
        ])
    else:
        buttons.append([
            InlineKeyboardButton(
                text=t("btn_watch_browser", user_lang),
                url=get_yandex_video_url(movie.title_ru, movie.year, movie_lang=movie_lang)
            )
        ])

    # 2. Watch Option: Choose Quality (480p / 720p / 1080p)
    buttons.append([
        InlineKeyboardButton(
            text="⚙️ " + ("Выбрать качество (480p/720p/1080p)" if user_lang == "ru" else "Sifatni tanlash (480p/720p/1080p)"),
            callback_data=f"qual:{movie.kinopoisk_id or 0}:{movie.year or 0}:{movie.title_ru[:20]}"
        )
    ])

    # 3. Watch Option: Download / Send Video
    buttons.append([
        InlineKeyboardButton(
            text=t("btn_download_video", user_lang),
            callback_data=f"down:{movie.kinopoisk_id or 0}:{movie.year or 0}:{movie.title_ru[:20]}"
        )
    ])

    # 4. Next/Alternative button
    buttons.append([
        InlineKeyboardButton(
            text=t("btn_next", user_lang),
            callback_data=f"next:{movie.title_ru[:25]}"
        )
    ])

    # 5. Alternative movies quick buttons
    if movie.alternative_titles:
        alt_row = []
        for alt in movie.alternative_titles[:2]:
            alt_row.append(
                InlineKeyboardButton(
                    text=f"👉 {alt[:18]}",
                    callback_data=f"pick:{alt[:25]}"
                )
            )
        if alt_row:
            buttons.append(alt_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_quality_choice_keyboard(title: str, year: int, kp_id: int, movie_lang: str = "ru", user_lang: str = "ru") -> InlineKeyboardMarkup:
    buttons = []
    
    # In online player:
    if kp_id:
        player_url = get_webapp_player_url(kp_id)
        buttons.append([
            InlineKeyboardButton(
                text="▶️ 1080p Full HD (" + ("Плеер в Telegram" if user_lang == "ru" else "Telegram pleyerda") + ")",
                web_app=WebAppInfo(url=player_url)
            )
        ])

    # Quality direct links
    buttons.append([
        InlineKeyboardButton(
            text="📱 480p (" + ("Эконом / Трафик кам" if user_lang == "ru" else "Kam trafik") + ")",
            url=get_yandex_video_url(title, year, quality="480p", movie_lang=movie_lang)
        )
    ])
    buttons.append([
        InlineKeyboardButton(
            text="💻 720p (" + ("HD качество / O'rtacha" if user_lang == "ru" else "HD sifat") + ")",
            url=get_yandex_video_url(title, year, quality="720p", movie_lang=movie_lang)
        )
    ])
    buttons.append([
        InlineKeyboardButton(
            text="🎬 1080p (" + ("Full HD качество" if user_lang == "ru" else "Eng yuqori sifat") + ")",
            url=get_google_watch_url(title, year, movie_lang=movie_lang, quality="1080p")
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_download_choice_keyboard(title: str, year: int, movie_lang: str = "ru", user_lang: str = "ru") -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="📥 Rutor (1080p / 720p)",
                url=get_torrent_rutor_url(title, year, quality="1080p")
            ),
            InlineKeyboardButton(
                text="🧲 RuTracker",
                url=get_rutracker_url(title, year, quality="1080p")
            )
        ],
        [
            InlineKeyboardButton(
                text="🔎 " + ("Найти видеофайл в Telegram" if user_lang == "ru" else "Telegramdan faylni topish"),
                url=get_telegram_channel_search(title, movie_lang=movie_lang)
            )
        ],
        [
            InlineKeyboardButton(
                text="🌐 " + ("Скачать с сайта (прямой поиск)" if user_lang == "ru" else "Saytdan yuklash"),
                url=get_google_watch_url(title, year, movie_lang=movie_lang, quality="skachat")
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="👥 Кто авторизовался", callback_data="admin:users"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")
        ],
        [
            InlineKeyboardButton(text="📜 Кто и что смотрел (Логи)", callback_data="admin:logs")
        ],
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="admin:refresh"),
            InlineKeyboardButton(text="❌ Закрыть панель", callback_data="admin:close")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
