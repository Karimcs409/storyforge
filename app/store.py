"""SQLite: saved stories + per-call cost/latency log."""
import json, sqlite3, threading, time
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "storyforge.db"
_lock = threading.Lock()


def _conn():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS stories (id INTEGER PRIMARY KEY, created REAL, source TEXT, voice TEXT, lang TEXT, status TEXT, data TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS calls (id INTEGER PRIMARY KEY, ts REAL, task TEXT, model TEXT, tokens_in INT, tokens_out INT, usd REAL, ms INT, retries INT, ref TEXT)")
    return c


def log_call(l: dict):
    with _lock, _conn() as c:
        c.execute("INSERT INTO calls (ts, task, model, tokens_in, tokens_out, usd, ms, retries, ref) VALUES (?,?,?,?,?,?,?,?,?)",
                  (time.time(), l["task"], l["model"], l["tokens_in"], l["tokens_out"], l["usd"], l["ms"], l["retries"], l.get("ref", "")))


def save_story(source: str, voice: str, lang: str, data: dict, status="draft", sid: int | None = None) -> int:
    with _lock, _conn() as c:
        if sid:
            c.execute("UPDATE stories SET data=?, status=? WHERE id=?", (json.dumps(data, ensure_ascii=False), status, sid))
            return sid
        cur = c.execute("INSERT INTO stories (created, source, voice, lang, status, data) VALUES (?,?,?,?,?,?)",
                        (time.time(), source, voice, lang, status, json.dumps(data, ensure_ascii=False)))
        return cur.lastrowid


def get_story(sid: int) -> dict | None:
    with _conn() as c:
        r = c.execute("SELECT id, source, voice, lang, status, data FROM stories WHERE id=?", (sid,)).fetchone()
    if not r: return None
    return {"id": r[0], "source": r[1], "voice": r[2], "lang": r[3], "status": r[4], **json.loads(r[5])}


def list_stories(limit=20):
    with _conn() as c:
        rows = c.execute("SELECT id, created, source, voice, lang, status FROM stories ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(zip(["id", "created", "source", "voice", "lang", "status"], r)) for r in rows]
