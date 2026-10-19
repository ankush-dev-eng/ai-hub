"""
history_db.py - SQLite persistence for the AI Hub chat. Pure storage, no Streamlit import.

Layout (override root with CHAT_DATA env):
    chat_data/history.db      sessions + messages
    chat_data/img/<sha>.ext   attached images (kept OUT of the DB so it stays small)
    chat_data/tts/<sha>.mp3   TTS cache (written by voice_hub)

messages.meta JSON keys used by the app: images (file refs), display (text shown in the bubble), used (provider/model).
"""
import base64
import hashlib
import json
import os
import pathlib
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager

DATA = pathlib.Path(os.getenv("CHAT_DATA", "chat_data"))
DB = DATA / "history.db"
IMG = DATA / "img"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions(
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    title_auto  INTEGER NOT NULL DEFAULT 1,
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS messages(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    meta        TEXT NOT NULL DEFAULT '{}',
    ts          REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at DESC);
"""

_ready = False


@contextmanager
def _db():
    """New connection per call: Streamlit runs scripts on different threads."""
    DATA.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init():
    global _ready
    if _ready:
        return
    with _db() as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.executescript(SCHEMA)
    _ready = True


def new_session(title: str = "New chat", sid: str | None = None) -> str:
    init()
    sid = sid or uuid.uuid4().hex[:12]
    now = time.time()
    with _db() as c:
        c.execute("INSERT OR REPLACE INTO sessions(id,title,created_at,updated_at) VALUES(?,?,?,?)", (sid, title[:80], now, now))
    return sid


def session_exists(sid: str) -> bool:
    init()
    with _db() as c:
        return c.execute("SELECT 1 FROM sessions WHERE id=?", (sid,)).fetchone() is not None


def latest_session():
    init()
    with _db() as c:
        r = c.execute("SELECT id FROM sessions ORDER BY updated_at DESC LIMIT 1").fetchone()
    return r["id"] if r else None


def get_title(sid: str) -> str:
    with _db() as c:
        r = c.execute("SELECT title FROM sessions WHERE id=?", (sid,)).fetchone()
    return r["title"] if r else ""


def list_sessions(query: str = "", limit: int = 40):
    """Newest first. `query` matches titles AND message text (LIKE, case-insensitive for ASCII)."""
    init()
    sql = "SELECT s.id, s.title, s.updated_at FROM sessions s"
    args = []
    q = query.strip()
    if q:
        like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        sql += (" WHERE s.title LIKE ? ESCAPE '\\' OR EXISTS("
                "SELECT 1 FROM messages m WHERE m.session_id=s.id AND m.content LIKE ? ESCAPE '\\')")
        args += [like, like]
    sql += " ORDER BY s.updated_at DESC LIMIT ?"
    args.append(limit)
    with _db() as c:
        return [dict(r) for r in c.execute(sql, args)]


def rename(sid: str, title: str):
    title = re.sub(r"\s+", " ", title).strip()[:80] or "Untitled"
    with _db() as c:
        c.execute("UPDATE sessions SET title=?, title_auto=0 WHERE id=?", (title, sid))


def auto_title(sid: str, title: str):
    """Set a generated title unless the user has renamed the chat."""
    with _db() as c:
        c.execute("UPDATE sessions SET title=? WHERE id=? AND title_auto=1", (title[:80], sid))


def delete_session(sid: str):
    with _db() as c:
        c.execute("DELETE FROM sessions WHERE id=?", (sid,))  # messages cascade
    gc_images()


# ---------- messages ----------
def add_message(sid: str, role: str, content: str, meta: dict | None = None) -> int:
    now = time.time()
    with _db() as c:
        cur = c.execute(
            "INSERT INTO messages(session_id,role,content,meta,ts) VALUES(?,?,?,?,?)",
            (sid, role, content, json.dumps(meta or {}), now),
        )
        c.execute("UPDATE sessions SET updated_at=? WHERE id=?", (now, sid))
        return cur.lastrowid


def delete_message(mid: int):
    with _db() as c:
        c.execute("DELETE FROM messages WHERE id=?", (mid,))


def get_messages(sid: str) -> list[dict]:
    with _db() as c:
        rows = c.execute("SELECT id,role,content,meta,ts FROM messages WHERE session_id=? ORDER BY id", (sid,)).fetchall()
    out = []
    for r in rows:
        try:
            meta = json.loads(r["meta"])
        except Exception:
            meta = {}
        out.append({"id": r["id"], "role": r["role"], "content": r["content"], "meta": meta, "ts": r["ts"]})
    return out


# ---------- images (files, not blobs) ----------
_EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


def save_image(data_uri: str) -> str:
    m = re.match(r"data:(image/[a-z+]+);base64,(.*)", data_uri, re.S)
    if not m:
        return ""
    raw = base64.b64decode(m.group(2))
    name = hashlib.sha1(raw).hexdigest()[:20] + _EXT.get(m.group(1), ".png")
    IMG.mkdir(parents=True, exist_ok=True)
    f = IMG / name
    if not f.exists():
        f.write_bytes(raw)
    return name


def load_image(name: str):
    f = IMG / pathlib.Path(name).name  # basename only: no path traversal
    if not f.is_file():
        return None
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp"}.get(f.suffix, "image/png")
    return f"data:{mime};base64,{base64.b64encode(f.read_bytes()).decode()}"


def gc_images():
    """Remove image files no message references any more."""
    if not IMG.exists():
        return
    used = set()
    with _db() as c:
        for r in c.execute("SELECT meta FROM messages WHERE meta LIKE '%images%'"):
            try:
                used.update(json.loads(r["meta"]).get("images", []))
            except Exception:
                pass
    for f in IMG.iterdir():
        if f.name not in used:
            f.unlink(missing_ok=True)


# ---------- helpers / export ----------
def heuristic_title(text: str) -> str:
    words = re.sub(r"\s+", " ", text or "").strip().split()[:5]
    return (" ".join(words)[:48]) or "New chat"


def export_markdown(sid: str) -> str:
    lines = [f"# {get_title(sid)}", ""]
    for m in get_messages(sid):
        who = "**You**" if m["role"] == "user" else "**Assistant**"
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(m["ts"]))
        body = m["meta"].get("display") or m["content"]
        lines += [f"{who} · {when}", "", body, ""]
        if m["role"] == "assistant" and m["meta"].get("used"):
            lines += [f"_{m['meta']['used']}_", ""]
    return "\n".join(lines)


def export_json(sid: str) -> str:
    msgs = [{"role": m["role"], "content": m["content"], "ts": m["ts"], "used": m["meta"].get("used")}
            for m in get_messages(sid)]
    return json.dumps({"id": sid, "title": get_title(sid), "messages": msgs}, indent=2, ensure_ascii=False)
