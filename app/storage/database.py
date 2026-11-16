import sqlite3
from datetime import datetime, timezone
from app.core.config import DB_PATH

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def initialize_database():
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id)
        )""")

def create_conversation(title: str):
    with connect() as db:
        cur = db.execute("INSERT INTO conversations(title, created_at) VALUES (?, ?)",
            (title[:100], datetime.now(timezone.utc).isoformat()))
        return cur.lastrowid

def save_message(conversation_id: int, role: str, content: str):
    with connect() as db:
        db.execute("INSERT INTO messages(conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, datetime.now(timezone.utc).isoformat()))

def list_conversations():
    with connect() as db:
        rows = db.execute("SELECT * FROM conversations ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]

def get_messages(conversation_id: int):
    with connect() as db:
        rows = db.execute("SELECT * FROM messages WHERE conversation_id=? ORDER BY id", (conversation_id,)).fetchall()
        return [dict(row) for row in rows]
