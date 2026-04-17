import sqlite3
import logging
from contextlib import closing
from datetime import datetime

DB_PATH = "user_data.db"

logger = logging.getLogger(__name__)

########################################################################################################
# ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
########################################################################################################

def init_db():
    try:
        with closing(sqlite3.connect(DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                # Журнал всех обращений пользователей
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        username TEXT,
                        full_name TEXT,
                        chat_id INTEGER NOT NULL,
                        date TEXT NOT NULL,
                        time TEXT NOT NULL
                    )
                """)

                # Лог попыток заблокированных пользователей
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS blocked_attempts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        username TEXT,
                        full_name TEXT,
                        chat_id INTEGER,
                        reason TEXT,
                        ts DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                conn.commit()

    except Exception as e:
        logger.exception("Ошибка инициализации БД: %s", e)

########################################################################################################
# УНИВЕРСАЛЬНЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С БД
########################################################################################################

def db_fetch_all(query: str, params: tuple = ()):
    try:
        with closing(sqlite3.connect(DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
    except Exception as e:
        logger.exception("Ошибка db_fetch_all: %s", e)
        return []

def db_fetch_one(query: str, params: tuple = ()):
    try:
        with closing(sqlite3.connect(DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(query, params)
                return cursor.fetchone()
    except Exception as e:
        logger.exception("Ошибка db_fetch_one: %s", e)
        return None

def db_execute(query: str, params: tuple = ()):
    try:
        with closing(sqlite3.connect(DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(query, params)
                conn.commit()
    except Exception as e:
        logger.exception("Ошибка db_execute: %s", e)

########################################################################################################
# СПЕЦИАЛЬНЫЕ ФУНКЦИИ ДЛЯ БОТА
########################################################################################################

def save_user_data(user_id: int, username: str | None, full_name: str, chat_id: int):
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")

    db_execute("""
        INSERT INTO user_data (user_id, username, full_name, chat_id, date, time)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, username, full_name, chat_id, current_date, current_time))

def save_user_attempt(user_id: int, username: str | None, full_name: str, chat_id: int, reason: str = "blacklisted"):
    db_execute("""
        INSERT INTO blocked_attempts (user_id, username, full_name, chat_id, reason)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, username, full_name, chat_id, reason))


########################################################################################################

def db_fetch_one(query: str, params: tuple = ()):
    try:
        with closing(sqlite3.connect(DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(query, params)
                return cursor.fetchone()
    except Exception as e:
        logger.exception("Ошибка db_fetch_one: %s", e)
        return (0,)


