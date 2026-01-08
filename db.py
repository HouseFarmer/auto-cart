import sqlite3
import datetime
from pydantic import BaseModel

# Model for history response
class HistoryItem(BaseModel):
    id: int
    action: str
    timestamp: str
    success: bool
    reason: str | None

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('droidrun.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            success BOOLEAN NOT NULL,
            reason TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Database operations
def add_history(action: str, success: bool, reason: str):
    conn = sqlite3.connect('droidrun.db')
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO history (action, timestamp, success, reason) VALUES (?, ?, ?, ?)",
        (action, timestamp, success, reason)
    )
    conn.commit()
    conn.close()

def get_history():
    conn = sqlite3.connect('droidrun.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, action, timestamp, success, reason FROM history ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": row[0],
            "action": row[1],
            "timestamp": row[2],
            "success": bool(row[3]),
            "reason": row[4]
        }
        for row in rows
    ]

def delete_history(id: int):
    conn = sqlite3.connect('droidrun.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history WHERE id = ?", (id,))
    conn.commit()
    conn.close()

def delete_all_history():
    conn = sqlite3.connect('droidrun.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history")
    conn.commit()
    conn.close()
