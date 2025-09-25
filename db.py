CREATE_VIEWED_LINKS = '''
CREATE TABLE IF NOT EXISTS viewed_links (
    user_id INTEGER,
    link_id TEXT,
    PRIMARY KEY (user_id, link_id)
);
'''
import sqlite3
from contextlib import closing
from typing import Optional

DB_PATH = 'botdata.sqlite3'

CREATE_USERS = '''
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    points REAL DEFAULT 0,
    is_admin INTEGER DEFAULT 0
);
'''

CREATE_LINKS = '''
CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT,
    user_id INTEGER,
    timestamp TEXT,
    is_admin INTEGER
);
'''

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(CREATE_USERS)
    c.execute(CREATE_LINKS)
    c.execute(CREATE_VIEWED_LINKS)
    conn.commit()
    conn.close()
# Record that a user has viewed a link
def add_viewed_link(user_id, link_id):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        c = conn.cursor()
        c.execute('''INSERT OR IGNORE INTO viewed_links (user_id, link_id) VALUES (?, ?)''', (user_id, link_id))
        conn.commit()

# Get all link_ids viewed by a user
def get_viewed_links(user_id):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        c = conn.cursor()
        c.execute('''SELECT link_id FROM viewed_links WHERE user_id = ?''', (user_id,))
        return set(row[0] for row in c.fetchall())
        conn.commit()

def add_user(telegram_id, username, is_admin=0):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        c = conn.cursor()
        c.execute('''INSERT OR IGNORE INTO users (telegram_id, username, is_admin) VALUES (?, ?, ?)''',
                  (telegram_id, username, is_admin))
        conn.commit()

def update_points(telegram_id, delta):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        c = conn.cursor()
        c.execute('''UPDATE users SET points = points + ? WHERE telegram_id = ?''', (delta, telegram_id))
        conn.commit()

def get_points(telegram_id) -> Optional[float]:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        c = conn.cursor()
        c.execute('''SELECT points FROM users WHERE telegram_id = ?''', (telegram_id,))
        row = c.fetchone()
        return row[0] if row else None

def is_admin(telegram_id) -> bool:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        c = conn.cursor()
        c.execute('''SELECT is_admin FROM users WHERE telegram_id = ?''', (telegram_id,))
        row = c.fetchone()
        return bool(row[0]) if row else False
