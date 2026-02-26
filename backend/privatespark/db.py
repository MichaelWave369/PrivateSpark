import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from .config import DB_PATH, ensure_dirs


def utcnow() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def get_conn() -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_cursor():
    conn = get_conn()
    try:
        cur = conn.cursor()
        yield conn, cur
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with db_cursor() as (_, cur):
        cur.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(chat_id) REFERENCES chats(id)
            );
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                mime TEXT,
                size INTEGER,
                sha256 TEXT,
                stored_path TEXT NOT NULL,
                extracted_text TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );
            CREATE TABLE IF NOT EXISTS capsules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                file_id INTEGER,
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(file_id) REFERENCES files(id)
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(
                title,
                text,
                content='capsules',
                content_rowid='id'
            );
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                capsule_id INTEGER NOT NULL,
                model TEXT NOT NULL,
                vector_json TEXT NOT NULL,
                dim INTEGER NOT NULL,
                FOREIGN KEY(capsule_id) REFERENCES capsules(id)
            );
            """
        )

        project_count = cur.execute("SELECT COUNT(*) AS c FROM projects").fetchone()["c"]
        if project_count == 0:
            cur.execute(
                "INSERT INTO projects(name, created_at) VALUES (?, ?)",
                ("Default Project", utcnow()),
            )


def upsert_fts(capsule_id: int, title: str, text: str) -> None:
    with db_cursor() as (_, cur):
        cur.execute("DELETE FROM fts WHERE rowid = ?", (capsule_id,))
        cur.execute("INSERT INTO fts(rowid, title, text) VALUES (?, ?, ?)", (capsule_id, title, text))


def store_embedding(capsule_id: int, model: str, vector: list[float]) -> None:
    with db_cursor() as (_, cur):
        cur.execute(
            "INSERT INTO embeddings(capsule_id, model, vector_json, dim) VALUES (?, ?, ?, ?)",
            (capsule_id, model, json.dumps(vector), len(vector)),
        )
