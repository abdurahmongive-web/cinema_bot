import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_PATH = Path(__file__).resolve().parent / "cinema_bot.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Table of users and authorization status
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                language TEXT DEFAULT 'ru',
                movie_lang TEXT DEFAULT 'ru',
                is_authorized INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                auth_date TEXT
            )
        """)
        
        # Migration for existing table columns
        cursor.execute("PRAGMA table_info(users)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "language" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'ru'")
        if "movie_lang" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN movie_lang TEXT DEFAULT 'ru'")
        
        # Table of user activity (searches and movies found)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                full_name TEXT,
                username TEXT,
                query TEXT,
                movie_title TEXT,
                timestamp TEXT
            )
        """)
        conn.commit()

def is_user_authorized(user_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_authorized, is_admin FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return bool(row["is_authorized"] or row["is_admin"])
        return False

def is_user_admin(user_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return bool(row["is_admin"])
        return False

def set_user_admin(user_id: int, first_name: str = "", last_name: str = "", username: str = ""):
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO users (user_id, first_name, last_name, username, is_authorized, is_admin, auth_date)
            VALUES (?, ?, ?, ?, 1, 1, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                is_authorized = 1,
                is_admin = 1,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                username = excluded.username
        """, (user_id, first_name or "", last_name or "", username or "", now))
        conn.commit()

def authorize_user(user_id: int, first_name: str = "", last_name: str = "", username: str = "", language: str = "ru") -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO users (user_id, first_name, last_name, username, language, is_authorized, auth_date)
            VALUES (?, ?, ?, ?, ?, 1, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                is_authorized = 1,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                username = excluded.username,
                auth_date = excluded.auth_date
        """, (user_id, first_name or "", last_name or "", username or "", language, now))
        conn.commit()
        return True

def get_user_language(user_id: int) -> str:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row["language"]:
            return row["language"]
        return "ru"

def set_user_language(user_id: int, lang: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, language) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET language = excluded.language
        """, (user_id, lang))
        conn.commit()

def get_user_movie_lang(user_id: int) -> str:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT movie_lang FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row["movie_lang"]:
            return row["movie_lang"]
        return "ru"

def set_user_movie_lang(user_id: int, lang: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET movie_lang = ? WHERE user_id = ?
        """, (lang, user_id))
        conn.commit()

def log_activity(user_id: int, full_name: str, username: str, query: str, movie_title: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO activity_logs (user_id, full_name, username, query, movie_title, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, full_name or "", username or "", query or "", movie_title or "", now))
        conn.commit()

def get_authorized_users() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE is_authorized = 1 ORDER BY auth_date DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_activity_logs(limit: int = 25) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM activity_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_stats() -> Dict[str, int]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total_users FROM users WHERE is_authorized = 1")
        users_count = cursor.fetchone()["total_users"]
        
        cursor.execute("SELECT COUNT(*) as total_logs FROM activity_logs")
        logs_count = cursor.fetchone()["total_logs"]
        
        return {
            "total_users": users_count,
            "total_searches": logs_count
        }

init_db()
