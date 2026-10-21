import asyncio
import io
import logging
import sys
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatAction
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    BufferedInputFile
)

# Fix Windows console UTF-8 encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import config
import database
from locales import t, TEXTS
from ai_service import AIService, MovieInfo
from keyboards import (
    get_main_reply_keyboard,
    get_movie_keyboard,
    get_language_inline_keyboard,
    get_movie_lang_inline_keyboard,
    get_quality_choice_keyboard,
    get_download_choice_keyboard,
    get_admin_keyboard
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("CinemaBot")

ai_service = AIService()

USER_ACCESS_CODE = "3461"
DEV_PASSWORDS = ["0102abdu2010", "0102фивг2010"]

chat_history: dict[int, list[str]] = {}

def get_user_display_name(user) -> str:
    parts = []
    if user.first_name:
        parts.append(user.first_name)
    if user.last_name:
        parts.append(user.last_name)
    return " ".join(parts).strip() or "Без имени"

def format_movie_card(movie: MovieInfo, lang: str = "ru") -> str:
    lines = []
    lines.append(f"🎬 <b>{movie.title_ru}</b> ({movie.year})")
    if movie.title_orig and movie.title_orig.lower() != movie.title_ru.lower():
        lines.append(f"<i>{movie.title_orig}</i>")
    lines.append("")

    ratings = []
    if movie.rating_kp:
        ratings.append(f"{t('kp_label', lang)}: <b>{movie.rating_kp}</b>")
    if movie.rating_imdb:
        ratings.append(f"{t('imdb_label', lang)}: <b>{movie.rating_imdb}</b>")
    if ratings:
        lines.append(f"⭐ Рейтинг: {' | '.join(ratings)}")

    if movie.genres:
        lines.append(f"{t('genres_label', lang)}: {', '.join(movie.genres)}")

    if movie.director:
        lines.append(f"{t('director_label', lang)}: {movie.director}")

    if movie.actors:
        lines.append(f"{t('actors_label', lang)}: {', '.join(movie.actors)}")

    if movie.duration_min:
        lines.append(f"{t('duration_label', lang)}: {movie.duration_min} {t('min_label', lang)}")

    lines.append("")
    lines.append(f"<b>{t('plot_label', lang)}:</b>\n{movie.description}")
    lines.append("")
    lines.append(f"<b>{t('why_label', lang)}:</b>\n{movie.why_recommended}")

    return "\n".join(lines)

async def check_access(message: Message) -> bool:
    user = message.from_user
    if not user:
        return False

    lang = database.get_user_language(user.id)
    text = (message.text or "").strip()

    # Developer password
    if text in DEV_PASSWORDS:
        database.set_user_admin(
            user_id=user.id,
            first_name=user.first_name or "",
            last_name=user.last_name or "",
            username=user.username or ""
        )
        await message.answer(
            t("admin_activated", lang),
            reply_markup=get_main_reply_keyboard(lang=lang, is_admin=True)
        )
        await show_admin_panel(message)
        return False

    # Access code 3461
    if text == USER_ACCESS_CODE:
        database.authorize_user(
            user_id=user.id,
            first_name=user.first_name or "",
            last_name=user.last_name or "",
            username=user.username or "",
            language=lang
        )
        is_admin = database.is_user_admin(user.id)
        await message.answer(
            t("code_success", lang),
            reply_markup=get_main_reply_keyboard(lang=lang, is_admin=is_admin)
        )
        # Suggest language selection if not yet set
        await message.answer(
            "🌐 <b>Тилни танланг / Выберите язык:</b>",
            reply_markup=get_language_inline_keyboard()
        )
        return False

    # Already authorized
    if database.is_user_authorized(user.id):
        return True

    # Blocked
    await message.answer(t("access_blocked", lang))
    return False

async def show_admin_panel(message: Message):
    stats = database.get_stats()
    text = (
        "🛠 <b>Меню разработчика / Dasturchi paneli</b>\n\n"
        f"👥 Авторизовано пользователей: <b>{stats['total_users']}</b>\n"
        f"📊 Всего запросов к кино: <b>{stats['total_searches']}</b>\n\n"
        "Выберите раздел для просмотра:"
    )
    await message.answer(text, reply_markup=get_admin_keyboard())

async def process_movie_search(message: Message, query: str, exclude_list: list[str] = None):
    chat_id = message.chat.id
    user = message.from_user
    lang = database.get_user_language(user.id if user else 0)
    movie_lang = database.get_user_movie_lang(user.id if user else 0)

    await message.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    wait_msg = await message.answer(t("searching", lang))

    movie = await ai_service.find_movie(
        user_prompt=query,
        exclude_titles=exclude_list,
        user_lang=lang,
        movie_lang=movie_lang
    )
    if not movie:
        await wait_msg.edit_text(t("not_found", lang))
        return

    if chat_id not in chat_history:
        chat_history[chat_id] = []
    chat_history[chat_id].append(movie.title_ru)

    database.log_activity(
        user_id=user.id if user else 0,
        full_name=get_user_display_name(user) if user else "Аноним",
        username=user.username or "" if user else "",
        query=query,
        movie_title=f"{movie.title_ru} ({movie.year})"
    )

    text = format_movie_card(movie, lang=lang)
    keyboard = get_movie_keyboard(movie, user_lang=lang, movie_lang=movie_lang)

    await wait_msg.delete()
    await message.answer(text, reply_markup=keyboard)

dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    lang = database.get_user_language(user.id if user else 0)

    if not await check_access(message):
        return

    is_admin = database.is_user_admin(user.id) if user else False
    await message.answer(
        t("welcome", lang),
        reply_markup=get_main_reply_keyboard(lang=lang, is_admin=is_admin)
    )

@dp.message(Command("help"))
@dp.message(F.text.in_({"ℹ️ Помощь", "ℹ️ Yordam"}))
async def cmd_help(message: Message):
    if not await check_access(message):
        return

    user = message.from_user
    lang = database.get_user_language(user.id if user else 0)
    is_admin = database.is_user_admin(user.id) if user else False
    await message.answer(t("help", lang), reply_markup=get_main_reply_keyboard(lang=lang, is_admin=is_admin))

@dp.message(F.text.in_({"👤 Об авторе", "👤 Muallif haqida"}))
async def cmd_about(message: Message):
    if not await check_access(message):
        return

    user = message.from_user
    lang = database.get_user_language(user.id if user else 0)
    is_admin = database.is_user_admin(user.id) if user else False
    await message.answer(t("about_author", lang), reply_markup=get_main_reply_keyboard(lang=lang, is_admin=is_admin))

@dp.message(F.text.in_({"🌐 Тил / Язык", "🌐 Til / Язык", "/lang"}))
async def cmd_language(message: Message):
    if not await check_access(message):
        return
    await message.answer(
        "🌐 <b>Тилни танланг / Выберите язык интерфейса:</b>",
        reply_markup=get_language_inline_keyboard()
    )

@dp.message(F.text.in_({"🔊 Озвучка кино", "🔊 Film tili"}))
async def cmd_movie_language(message: Message):
    if not await check_access(message):
        return
    user = message.from_user
    lang = database.get_user_language(user.id if user else 0)
    await message.answer(
        t("choose_movie_lang", lang),
        reply_markup=get_movie_lang_inline_keyboard(lang=lang)
    )

@dp.message(F.text == "🛠 Режим разработчика")
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    user = message.from_user
    if user and database.is_user_admin(user.id):
        await show_admin_panel(message)
    else:
        await message.answer("🔒 Введите пароль разработчика:")

@dp.message(F.photo)
async def handle_photo(message: Message):
    if not await check_access(message):
        return

    chat_id = message.chat.id
    user = message.from_user
    lang = database.get_user_language(user.id if user else 0)
    movie_lang = database.get_user_movie_lang(user.id if user else 0)

    await message.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    status_msg = await message.answer(t("analyzing_photo", lang))

    try:
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        file_io = io.BytesIO()
        await message.bot.download_file(file.file_path, destination=file_io)
        image_bytes = file_io.getvalue()

        movie = await ai_service.find_movie_by_media(
            media_bytes=image_bytes,
            mime_type="image/jpeg",
            caption=message.caption or "",
            user_lang=lang,
            movie_lang=movie_lang
        )
        if not movie:
            await status_msg.edit_text(t("not_found", lang))
            return

        database.log_activity(
            user_id=user.id if user else 0,
            full_name=get_user_display_name(user) if user else "Аноним",
            username=user.username or "" if user else "",
            query="[Поиск по фото / Rasm bo'yicha]",
            movie_title=f"{movie.title_ru} ({movie.year})"
        )

        text = format_movie_card(movie, lang=lang)
        keyboard = get_movie_keyboard(movie, user_lang=lang, movie_lang=movie_lang)

        await status_msg.delete()
        await message.answer(text, reply_markup=keyboard)
    except Exception as e:
        logger.exception("Error processing photo: %s", e)
        await status_msg.edit_text("Ошибка при обработке фото.")

@dp.message(F.voice)
async def handle_voice(message: Message):
    if not await check_access(message):
        return

    chat_id = message.chat.id
    user = message.from_user
    lang = database.get_user_language(user.id if user else 0)
    movie_lang = database.get_user_movie_lang(user.id if user else 0)

    await message.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    status_msg = await message.answer(t("listening_voice", lang))

    try:
        voice = message.voice
        file = await message.bot.get_file(voice.file_id)
        file_io = io.BytesIO()
        await message.bot.download_file(file.file_path, destination=file_io)
        audio_bytes = file_io.getvalue()

        movie = await ai_service.find_movie_by_media(
            media_bytes=audio_bytes,
            mime_type="audio/ogg",
            caption="",
            user_lang=lang,
            movie_lang=movie_lang
        )
        if not movie:
            await status_msg.edit_text(t("not_found", lang))
            return

        database.log_activity(
            user_id=user.id if user else 0,
            full_name=get_user_display_name(user) if user else "Аноним",
            username=user.username or "" if user else "",
            query="[Голосовой запрос / Ovozli xabar]",
            movie_title=f"{movie.title_ru} ({movie.year})"
        )

        text = format_movie_card(movie, lang=lang)
        keyboard = get_movie_keyboard(movie, user_lang=lang, movie_lang=movie_lang)

        await status_msg.delete()
        await message.answer(text, reply_markup=keyboard)
    except Exception as e:
        logger.exception("Error processing voice: %s", e)
        await status_msg.edit_text("Ошибка при обработке голосового сообщения.")

# Callbacks: Language settings
@dp.callback_query(F.data.startswith("setlang:"))
async def callback_set_lang(callback: CallbackQuery):
    lang = callback.data.split(":", 1)[1]
    user = callback.from_user
    database.set_user_language(user.id, lang)
    is_admin = database.is_user_admin(user.id)
    await callback.message.delete()
    await callback.message.answer(
        t("lang_changed", lang),
        reply_markup=get_main_reply_keyboard(lang=lang, is_admin=is_admin)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("setmovielang:"))
async def callback_set_movie_lang(callback: CallbackQuery):
    mlang = callback.data.split(":", 1)[1]
    user = callback.from_user
    database.set_user_movie_lang(user.id, mlang)
    lang = database.get_user_language(user.id)

    name_map = {"ru": "Русская озвучка 🇷🇺", "uz": "O'zbekcha tarjima 🇺🇿", "orig": "Original + Subs 🇬🇧"}
    await callback.message.edit_text(
        f"{t('movie_lang_changed', lang)} <b>{name_map.get(mlang, mlang)}</b>"
    )
    await callback.answer()

# Callbacks: Quality choice
@dp.callback_query(F.data.startswith("qual:"))
async def callback_quality(callback: CallbackQuery):
    parts = callback.data.split(":")
    kp_id = int(parts[1]) if parts[1].isdigit() else 0
    year = int(parts[2]) if parts[2].isdigit() else 0
    title = parts[3] if len(parts) > 3 else ""

    user = callback.from_user
    lang = database.get_user_language(user.id)
    movie_lang = database.get_user_movie_lang(user.id)

    await callback.message.answer(
        f"{t('choose_quality', lang)}\n🎬 <b>{title}</b>",
        reply_markup=get_quality_choice_keyboard(title, year, kp_id, movie_lang=movie_lang, user_lang=lang)
    )
    await callback.answer()

# Callbacks: Download / Video choice
@dp.callback_query(F.data.startswith("down:"))
async def callback_download(callback: CallbackQuery):
    parts = callback.data.split(":")
    year = int(parts[2]) if parts[2].isdigit() else 0
    title = parts[3] if len(parts) > 3 else ""

    user = callback.from_user
    lang = database.get_user_language(user.id)
    movie_lang = database.get_user_movie_lang(user.id)

    await callback.message.answer(
        f"📥 <b>{'Скачивание и файлы видео' if lang == 'ru' else 'Video faylini yuklab olish'}:</b>\n🎬 <b>{title}</b>",
        reply_markup=get_download_choice_keyboard(title, year, movie_lang=movie_lang, user_lang=lang)
    )
    await callback.answer()

# Admin Callbacks
@dp.callback_query(F.data == "admin:users")
async def callback_admin_users(callback: CallbackQuery):
    if not database.is_user_admin(callback.from_user.id):
        await callback.answer("Нет прав доступа", show_alert=True)
        return

    users = database.get_authorized_users()
    if not users:
        await callback.message.edit_text("👥 Авторизованных пользователей пока нет.", reply_markup=get_admin_keyboard())
        return

    lines = ["👥 <b>Кто авторизовался (код 3461):</b>\n"]
    for i, u in enumerate(users, 1):
        name = f"{u['first_name']} {u['last_name']}".strip() or "Без имени"
        uname = f"@{u['username']}" if u['username'] else "нет username"
        lang_flag = "🇺🇿" if u['language'] == 'uz' else "🇷🇺"
        admin_badge = " [👑 Автор]" if u['is_admin'] else ""
        lines.append(f"<b>{i}. {name}</b> ({uname}) {lang_flag}{admin_badge}\n   ID: <code>{u['user_id']}</code> | 📅 {u['auth_date']}")

    await callback.message.edit_text("\n".join(lines), reply_markup=get_admin_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "admin:logs")
async def callback_admin_logs(callback: CallbackQuery):
    if not database.is_user_admin(callback.from_user.id):
        await callback.answer("Нет прав доступа", show_alert=True)
        return

    logs = database.get_activity_logs(limit=15)
    if not logs:
        await callback.message.edit_text("📜 История просмотров пуста.", reply_markup=get_admin_keyboard())
        return

    lines = ["📜 <b>Последние запросы и просмотры пользователей:</b>\n"]
    for log in logs:
        user_info = log['full_name']
        if log['username']:
            user_info += f" (@{log['username']})"
        lines.append(
            f"🕒 <b>{log['timestamp']}</b>\n"
            f"👤 <b>{user_info}</b> (ID: <code>{log['user_id']}</code>)\n"
            f"🔍 Запрос: <i>{log['query']}</i>\n"
            f"🎬 Фильм: <b>{log['movie_title']}</b>\n"
            f"────────────────"
        )

    await callback.message.edit_text("\n".join(lines), reply_markup=get_admin_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "admin:stats")
async def callback_admin_stats(callback: CallbackQuery):
    if not database.is_user_admin(callback.from_user.id):
        await callback.answer("Нет прав доступа", show_alert=True)
        return

    stats = database.get_stats()
    text = (
        "📊 <b>Статистика AI Кино-Бота:</b>\n\n"
        f"👥 Всего авторизовано пользователей: <b>{stats['total_users']}</b>\n"
        f"🔍 Всего запросов к фильмам: <b>{stats['total_searches']}</b>\n"
        f"🤖 Активная модель Gemini: <b>gemini-3.5-flash-lite / 3.6 / 3.7</b>\n"
        f"🔒 Статус доступа: <b>Закрытый для семьи (код 3461)</b>"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "admin:refresh")
async def callback_admin_refresh(callback: CallbackQuery):
    if not database.is_user_admin(callback.from_user.id):
        await callback.answer("Нет прав доступа", show_alert=True)
        return
    await show_admin_panel(callback.message)
    await callback.answer("Обновлено!")

@dp.callback_query(F.data == "admin:close")
async def callback_admin_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()

# Movie Callbacks
@dp.callback_query(F.data.startswith("next:"))
async def callback_next(callback: CallbackQuery):
    await callback.answer("...")
    title = callback.data.split(":", 1)[1]
    chat_id = callback.message.chat.id
    history = chat_history.get(chat_id, [])
    if title not in history:
        history.append(title)

    user = callback.from_user
    lang = database.get_user_language(user.id)
    query_text = (
        f"Посоветуй другой отличный фильм, похожий по качеству, но не {title}"
        if lang == "ru"
        else f"{title} filmiga o'xshash, lekin boshqa zo'r film taklif qil"
    )
    await process_movie_search(callback.message, query=query_text, exclude_list=history)

@dp.callback_query(F.data.startswith("pick:"))
async def callback_pick(callback: CallbackQuery):
    await callback.answer("...")
    title = callback.data.split(":", 1)[1]
    await process_movie_search(callback.message, query=title)

@dp.message(F.text)
async def handle_text(message: Message):
    if not await check_access(message):
        return

    raw = message.text.strip()
    query = raw

    # Preset mappings for RU and UZ buttons
    if raw in {"🍿 Фильм на вечер", "🍿 Kechki kino"}:
        query = "Посоветуй захватывающий фильм на вечер с высоким рейтингом"
    elif raw in {"🔥 Топовый триллер", "🔥 Zo'r triller"}:
        query = "Посоветуй напряженный психологический триллер с неожиданным финалом"
    elif raw in {"😂 Легкая комедия", "😂 Yengil komediya"}:
        query = "Посоветуй смешную и добрую комедию для отличного настроения"
    elif raw in {"🚀 Фантастика", "🚀 Qiziqarli fantastika"}:
        query = "Посоветуй глубокую фантастику про космос, время или будущее"
    elif raw in {"🎲 Случайный шедевр", "🎲 Sara film"}:
        query = "Посоветуй культовый признанный шедевр мирового кино"

    await process_movie_search(message, query)

async def main():
    if not config.BOT_TOKEN or not config.GEMINI_API_KEY:
        print("Ошибка: Проверьте BOT_TOKEN и GEMINI_API_KEY в файле .env!")
        return

    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    print("AI Cinema Bot (AbMovie) успешно запущен со всеми функциями (RU/UZ, плеер, видео, качество)!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
