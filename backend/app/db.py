"""SQLite storage. One file DB, per-user rows keyed by uid (anonymous id from the browser)."""
import json
import os
import sqlite3
import threading
from contextlib import contextmanager

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "..", "data", "coach.db"))
_lock = threading.RLock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions(
  id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT NOT NULL, date TEXT NOT NULL,
  description TEXT NOT NULL, amount REAL NOT NULL, merchant TEXT NOT NULL,
  category TEXT NOT NULL, cat_source TEXT NOT NULL, source TEXT NOT NULL, hash TEXT NOT NULL,
  UNIQUE(uid, hash));
CREATE INDEX IF NOT EXISTS ix_tx_uid_date ON transactions(uid, date);
CREATE TABLE IF NOT EXISTS rules(
  id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT NOT NULL, pattern TEXT NOT NULL,
  category TEXT NOT NULL, hits INTEGER DEFAULT 0, UNIQUE(uid, pattern));
CREATE TABLE IF NOT EXISTS kv(uid TEXT NOT NULL, k TEXT NOT NULL, v TEXT NOT NULL, PRIMARY KEY(uid,k));
CREATE TABLE IF NOT EXISTS goals(
  id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT NOT NULL, name TEXT NOT NULL,
  target_amount REAL NOT NULL, saved REAL NOT NULL DEFAULT 0, target_date TEXT NOT NULL,
  monthly_contrib REAL NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS sub_meta(uid TEXT NOT NULL, merchant TEXT NOT NULL, last_used TEXT,
  PRIMARY KEY(uid, merchant));
CREATE TABLE IF NOT EXISTS proposals(
  id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
  reason TEXT, status TEXT NOT NULL DEFAULT 'pending', created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS chat(
  id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT NOT NULL, role TEXT NOT NULL, text TEXT NOT NULL,
  created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS cache(h TEXT PRIMARY KEY, v TEXT NOT NULL);
"""


def _connect():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    c = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    c.row_factory = sqlite3.Row
    return c


def init():
    with conn() as c:
        c.executescript(SCHEMA)


@contextmanager
def conn():
    with _lock:
        c = _connect()
        try:
            yield c
            c.commit()
        finally:
            c.close()


def rows(sql, args=()):
    with conn() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]


def one(sql, args=()):
    r = rows(sql, args)
    return r[0] if r else None


def run(sql, args=()):
    with conn() as c:
        cur = c.execute(sql, args)
        return cur.lastrowid


def kv_get(uid, k, default=None):
    r = one("SELECT v FROM kv WHERE uid=? AND k=?", (uid, k))
    return json.loads(r["v"]) if r else default


def kv_set(uid, k, v):
    run("INSERT INTO kv(uid,k,v) VALUES(?,?,?) ON CONFLICT(uid,k) DO UPDATE SET v=excluded.v",
        (uid, k, json.dumps(v)))


def wipe_user(uid):
    with conn() as c:
        for t in ("transactions", "rules", "kv", "goals", "sub_meta", "proposals", "chat"):
            c.execute(f"DELETE FROM {t} WHERE uid=?", (uid,))
