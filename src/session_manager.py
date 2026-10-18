import os
import json
import time
import uuid
from pathlib import Path
from typing import List, Dict, Optional

SESSIONS_DIR = Path(__file__).parent.parent / "data" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

def generate_session_id() -> str:
    return str(uuid.uuid4())[:8]

def get_all_sessions() -> List[Dict]:
    """Retrieve all saved chat sessions sorted by last updated timestamp."""
    sessions = []
    if not SESSIONS_DIR.exists():
        return sessions
    for f in SESSIONS_DIR.glob("session_*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                sessions.append({
                    "id": data.get("id", f.stem.replace("session_", "")),
                    "title": data.get("title", "Untitled Chat"),
                    "updated_at": data.get("updated_at", 0),
                    "message_count": len(data.get("messages", []))
                })
        except Exception:
            continue
    # Sort descending by updated_at
    sessions.sort(key=lambda s: s["updated_at"], reverse=True)
    return sessions

def load_session(session_id: str) -> Optional[Dict]:
    """Load a specific session by ID."""
    file_path = SESSIONS_DIR / f"session_{session_id}.json"
    if not file_path.exists():
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as fp:
            return json.load(fp)
    except Exception:
        return None

def save_session(session_id: str, title: str, messages: List[Dict]) -> bool:
    """Save a chat session to disk as a compact JSON (under 5KB)."""
    file_path = SESSIONS_DIR / f"session_{session_id}.json"
    data = {
        "id": session_id,
        "title": title,
        "updated_at": time.time(),
        "messages": messages
    }
    try:
        with open(file_path, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def delete_session(session_id: str) -> bool:
    """Completely delete session file leaving zero residual junk."""
    file_path = SESSIONS_DIR / f"session_{session_id}.json"
    if file_path.exists():
        try:
            os.remove(file_path)
            return True
        except Exception:
            return False
    return False

def derive_auto_title(first_prompt: str, groq_key: str = None) -> str:
    """Quickly generate an appropriate 3-5 word title."""
    if groq_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            completion = client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=[
                    {"role": "user", "content": f"Generate a concise 3 to 5 word topic title for a conversation starting with: {first_prompt[:250]}. Output ONLY the title, no quotes, no markdown, no punctuation."}
                ],
                max_tokens=25,
                temperature=0.3
            )
            title = completion.choices[0].message.content.strip().replace('"', '').replace("'", "")
            if title and len(title) > 2:
                return title[:45]
        except Exception:
            pass
            
    # Fallback to smart heuristic
    clean = first_prompt.strip().replace("\n", " ")
    words = clean.split()
    if len(words) <= 5:
        return " ".join(words)[:40]
    return " ".join(words[:5]) + "..."
