# CinemaAI: Multimodal Conversational Discovery Engine

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![Framework](https://img.shields.io/badge/Framework-aiogram%203.x-green)](https://github.com/aiogram/aiogram)
[![LLM](https://img.shields.io/badge/Model-Gemini%202.5%20%2F%203.x%20Flash-orange?logo=google)](https://ai.google.dev/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)](LICENSE)

**CinemaAI** is an asynchronous, multimodal Telegram bot that serves as an intelligent film discovery and media recommendation agent. Built upon **aiogram 3** and the official **Google GenAI SDK** (`google-genai`), CinemaAI accepts unstructured text queries, voice audio notes, and screenshot image frames, extracting structured semantic metadata to surface curated cinematic recommendations and player embeds in real time.

---

## Architectural Overview

The application is structured around non-blocking event loops, type-safe data contracts, and resilient model failover:

```mermaid
flowchart TD
    subgraph TelegramClient["Telegram Client"]
        Text["Natural Language Query"]
        Voice["Voice Note (Audio)"]
        Image["Frame Screenshot / Meme (Visual)"]
    end

    subgraph BotCore["Asynchronous Dispatcher (aiogram 3)"]
        Router["Message & Callback Router"]
        VoiceHandler["Audio Ingestion & Pre-processing"]
        ImageHandler["Vision Frame Ingestion"]
        StateEngine["Finite State Machine & Keyboards"]
    end

    subgraph LLM["Gemini Multimodal Reasoning Engine"]
        GenAI["google.genai.Client"]
        Fallback["Model Failover Routing\n(2.5-Flash -> 3.5-Lite -> 3.6-Flash)"]
        Schema["Pydantic Structured Output\n(MovieInfo Schema Enforcement)"]
    end

    subgraph Storage["Persistence & External Services"]
        SQLite["Asynchronous SQLite Storage\n(User Preferences & History)"]
        PlayerService["Kinopoisk / Embed URL Resolver"]
    end

    Text --> Router
    Voice --> VoiceHandler --> Router
    Image --> ImageHandler --> Router

    Router --> StateEngine
    StateEngine --> GenAI
    GenAI --> Fallback
    Fallback --> Schema

    Schema --> PlayerService
    Schema --> SQLite
    PlayerService --> Router
    Router --> TelegramClient
```

---

## Key Systems Engineering Highlights

### 1. Schema-Enforced Structured LLM Output
Rather than parsing fragile unstructured markdown from language model completions, CinemaAI enforces strict schema compliance using **Pydantic**:
- Extracts normalized entities: `title_ru`, `title_orig`, `year`, `kinopoisk_id`, `rating_kp`, `rating_imdb`, `genres`, `director`, `actors`, and `why_recommended`.
- Guarantees deterministic parsing across model responses, preventing UI render crashes.

### 2. Multimodal Perception Pipeline
- **Voice Ingestion:** Streams `.ogg` / Opus voice notes from Telegram directly into Gemini's native multimodal audio ingestion pipeline without third-party speech-to-text latency.
- **Vision Recognition:** Ingests cinematic frames, stills, or movie memes, performing zero-shot visual similarity and actor identification to reconstruct movie titles from visual scenes alone.

### 3. Graceful Model Degradation & Resilience
- Implements an automated failover hierarchy (`MODELS_FALLBACK`) across Gemini model tiers to handle regional quota spikes or API rate-limiting dynamically without dropping user sessions.

### 4. Asynchronous Local State Management
- Utilizes SQLite (`database.py`) to maintain localized session states, historical recommendation tracking (preventing duplicate suggestions), and multi-lingual UI settings (Russian and Uzbek).

---

## Directory Structure

```text
cinema_bot/
├── main.py                   # Async entrypoint & aiogram router orchestration
├── ai_service.py             # Google GenAI integration & Pydantic schema validation
├── config.py                 # Typed configuration & environment loading
├── database.py               # SQLite asynchronous persistence & schema migrations
├── keyboards.py              # Inline and Reply keyboard builders
├── locales.py                # Multi-language dictionary (RU / UZ)
├── player_service.py         # Media URL routing & streaming player embeds
├── requirements.txt          # Python dependencies
├── .env.example              # Environment configuration template
└── run.bat                   # Windows batch execution script
```

---

## Getting Started

### 1. Installation
Clone the repository and set up a virtual environment:
```bash
git clone https://github.com/abdurahmongive-web/cinema_bot.git
cd cinema_bot

python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration
Copy `.env.example` to `.env` and provide your API keys:
```bash
cp .env.example .env
```

Edit `.env`:
```env
BOT_TOKEN=your_telegram_bot_token_from_botfather
GEMINI_API_KEY=your_gemini_api_key_from_google_ai_studio
GEMINI_MODEL=gemini-2.5-flash
```

### 3. Execution
```bash
python main.py
```

---

## Author

**Abdurahmon**  
High School Systems Builder & Researcher — Tashkent, Uzbekistan  
- GitHub: [@abdurahmongive-web](https://github.com/abdurahmongive-web)  
- Email: `abdurahmongive@gmail.com`
