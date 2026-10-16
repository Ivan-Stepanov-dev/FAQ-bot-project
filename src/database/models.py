"""Схема базы данных статистики и модели строк.

Четыре таблицы: users, events, daily_stats, errors. Файл ничего не знает
про подключение к БД, поэтому схему можно создать любым драйвером:

    create_tables(conn)                  # встроенный sqlite3
    await db.executescript(SCHEMA_SQL)   # aiosqlite

Все времена хранятся в UTC в формате "ГГГГ-ММ-ДД ЧЧ:ММ:СС" - именно его даёт
CURRENT_TIMESTAMP в SQLite. Такие строки правильно сравниваются и
сортируются как обычный текст.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass
from enum import Enum

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id    INTEGER NOT NULL UNIQUE,
    username       TEXT,
    first_seen_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_active_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_blocked     INTEGER NOT NULL DEFAULT 0 CHECK (is_blocked IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_users_first_seen_at  ON users (first_seen_at);
CREATE INDEX IF NOT EXISTS idx_users_last_active_at ON users (last_active_at);

CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    event_type TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_events_created_at   ON events (created_at, user_id);
CREATE INDEX IF NOT EXISTS idx_events_user_created ON events (user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_events_type_created ON events (event_type, created_at);

CREATE TABLE IF NOT EXISTS daily_stats (
    date           TEXT PRIMARY KEY CHECK (date(date) IS date),
    new_users      INTEGER NOT NULL DEFAULT 0,
    active_users   INTEGER NOT NULL DEFAULT 0,
    commands_count INTEGER NOT NULL DEFAULT 0,
    errors_count   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS errors (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    error_type  TEXT NOT NULL,
    message     TEXT NOT NULL,
    occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id     INTEGER REFERENCES users (id) ON DELETE SET NULL,
    context     TEXT
);

CREATE INDEX IF NOT EXISTS idx_errors_occurred_at ON errors (occurred_at);
"""

TABLES: tuple[str, ...] = ("users", "events", "daily_stats", "errors")


def create_tables(conn: sqlite3.Connection) -> None:
    """Создаёт таблицы и индексы. Безопасно вызывать при каждом запуске бота."""
    # Внешние ключи в SQLite выключены по умолчанию и включаются отдельно
    # для каждого соединения.
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_SQL)


class EventType(str, Enum):
    """Допустимые значения events.event_type.

    В самой таблице нет CHECK по этому списку: новый тип события можно
    добавить здесь без миграции БД.
    """

    START = "start"  # команда /start
    ADMIN = "admin"  # команда /admin
    FAQ_BUTTON = "faq_button"  # нажатие кнопки с вопросом
    MESSAGE = "message"  # любое другое сообщение


# Какие события считаются командами для daily_stats.commands_count.
COMMAND_EVENTS: tuple[EventType, ...] = (EventType.START, EventType.ADMIN)


def _parse_dt(value: str) -> dt.datetime:
    """'2026-10-16 20:14:00' (UTC) -> datetime с часовым поясом UTC."""
    return dt.datetime.fromisoformat(value).replace(tzinfo=dt.timezone.utc)


# Модели ниже собираются из строк результата. Для этого у соединения должен
# быть row_factory = sqlite3.Row (aiosqlite использует тот же класс Row).


@dataclass(frozen=True, slots=True)
class User:
    id: int
    telegram_id: int
    username: str | None
    first_seen_at: dt.datetime
    last_active_at: dt.datetime
    is_blocked: bool

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> User:
        return cls(
            id=row["id"],
            telegram_id=row["telegram_id"],
            username=row["username"],
            first_seen_at=_parse_dt(row["first_seen_at"]),
            last_active_at=_parse_dt(row["last_active_at"]),
            is_blocked=bool(row["is_blocked"]),
        )


@dataclass(frozen=True, slots=True)
class Event:
    id: int
    user_id: int
    event_type: str
    created_at: dt.datetime

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Event:
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            event_type=row["event_type"],
            created_at=_parse_dt(row["created_at"]),
        )


@dataclass(frozen=True, slots=True)
class DailyStat:
    date: dt.date
    new_users: int
    active_users: int
    commands_count: int
    errors_count: int

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> DailyStat:
        return cls(
            date=dt.date.fromisoformat(row["date"]),
            new_users=row["new_users"],
            active_users=row["active_users"],
            commands_count=row["commands_count"],
            errors_count=row["errors_count"],
        )


@dataclass(frozen=True, slots=True)
class ErrorLog:
    id: int
    error_type: str
    message: str
    occurred_at: dt.datetime
    user_id: int | None
    context: str | None  # произвольные детали, удобнее всего JSON-строкой

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> ErrorLog:
        return cls(
            id=row["id"],
            error_type=row["error_type"],
            message=row["message"],
            occurred_at=_parse_dt(row["occurred_at"]),
            user_id=row["user_id"],
            context=row["context"],
        )