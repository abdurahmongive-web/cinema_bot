import json
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
import config

logger = logging.getLogger(__name__)

MODELS_FALLBACK = [
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.7-flash"
]

class MovieInfo(BaseModel):
    title_ru: str = Field(description="Название фильма (на русском или узбекском)")
    title_orig: str = Field(description="Оригинальное название")
    year: int = Field(description="Год выхода фильма")
    kinopoisk_id: Optional[int] = Field(default=None, description="Цифровой ID фильма на Кинопоиске (например: 301, 258687, 447301)")
    rating_kp: Optional[float] = Field(default=None, description="Рейтинг Кинопоиска")
    rating_imdb: Optional[float] = Field(default=None, description="Рейтинг IMDb")
    genres: List[str] = Field(default_factory=list, description="Список основных жанров")
    director: Optional[str] = Field(default=None, description="Режиссер фильма")
    actors: List[str] = Field(default_factory=list, description="2-4 главных актера")
    duration_min: Optional[int] = Field(default=None, description="Хронометраж в минутах")
    description: str = Field(description="Увлекательное краткое описание сюжета без спойлеров")
    why_recommended: str = Field(description="Почему именно этот фильм подходит")
    alternative_titles: List[str] = Field(default_factory=list, description="2-3 альтернативных фильма")

class AIService:
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        self.client = None
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)

    def is_configured(self) -> bool:
        return bool(self.api_key and self.client)

    def _clean_json_text(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    async def find_movie(
        self,
        user_prompt: str,
        exclude_titles: Optional[List[str]] = None,
        user_lang: str = "ru",
        movie_lang: str = "ru"
    ) -> Optional[MovieInfo]:
        """Search for a movie based on user prompt, user language and preferred audio."""
        if not self.is_configured():
            logger.error("Gemini API key is not configured.")
            return None

        lang_instruction = "Ответь на РУССКОМ языке."
        if user_lang == "uz":
            lang_instruction = "Barcha tavsif (description) va izohlarni (why_recommended) O'ZBEK tilida yoz!"

        audio_instruction = ""
        if movie_lang == "uz":
            audio_instruction = "\nFoydalanuvchi filmni O'ZBEK tilida (tarjima / o'zbekcha dublyaj) ko'rmoqchi. Agar filmning o'zbekcha tarjimasi mashhur bo'lsa, hisobga ol."
        elif movie_lang == "orig":
            audio_instruction = "\nПользователь предпочитает смотреть в оригинале с субтитрами."

        prompt = f"""
Ты — персональный киноэксперт и гид по кинофильмам.
Запрос пользователя: "{user_prompt}"

Твоя задача:
1. Понять, какой фильм ищет пользователь (название, сюжет, актер или подборка под настроение).
2. Выбрать САМЫЙ лучший фильм.
3. Обязательно укажи точный цифровой Kinopoisk ID (`kinopoisk_id`), так как по нему пользователь будет смотреть фильм.
4. {lang_instruction}
{audio_instruction}

Верни СТРОГО JSON-объект:
{{
  "title_ru": "Название",
  "title_orig": "Original title",
  "year": 2010,
  "kinopoisk_id": 447301,
  "rating_kp": 8.7,
  "rating_imdb": 8.8,
  "genres": ["жанр1", "жанр2"],
  "director": "Имя режиссера",
  "actors": ["Актер 1", "Актер 2"],
  "duration_min": 140,
  "description": "Описание сюжета...",
  "why_recommended": "Почему стоит посмотреть...",
  "alternative_titles": ["Фильм 2", "Фильм 3"]
}}
"""
        if exclude_titles:
            prompt += f"\nНе рекомендуй эти фильмы (пользователь их уже видел): {', '.join(exclude_titles)}"

        for model_name in MODELS_FALLBACK:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.7,
                    ),
                )
                cleaned = self._clean_json_text(response.text)
                data = json.loads(cleaned)
                return MovieInfo(**data)
            except Exception as e:
                logger.warning("Model %s failed: %s. Trying fallback...", model_name, e)
                continue

        logger.error("All Gemini models failed for find_movie.")
        return None

    async def find_movie_by_media(
        self,
        media_bytes: bytes,
        mime_type: str,
        caption: str = "",
        user_lang: str = "ru",
        movie_lang: str = "ru"
    ) -> Optional[MovieInfo]:
        """Find a movie by photo or voice message."""
        if not self.is_configured():
            return None

        lang_instruction = "Ответь на РУССКОМ языке."
        if user_lang == "uz":
            lang_instruction = "Barcha tavsif va matnlarni O'ZBEK tilida yoz!"

        prompt = f"""
Проанализируй эти медиаданные (скриншот из фильма, постер или голос).
Определи, какой фильм ищет пользователь.
Укажи точный kinopoisk_id для плеера.
{lang_instruction}

Верни СТРОГО JSON-объект с полями:
title_ru, title_orig, year, kinopoisk_id, rating_kp, rating_imdb, genres, director, actors, duration_min, description, why_recommended, alternative_titles
"""
        if caption:
            prompt += f"\nКомментарий к медиа: {caption}"

        for model_name in MODELS_FALLBACK:
            try:
                part = types.Part.from_bytes(data=media_bytes, mime_type=mime_type)
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=[prompt, part],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.7,
                    ),
                )
                cleaned = self._clean_json_text(response.text)
                data = json.loads(cleaned)
                return MovieInfo(**data)
            except Exception as e:
                logger.warning("Model %s failed on media: %s", model_name, e)
                continue

        return None
