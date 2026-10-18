"""
ui_kit.py: Modern, production-grade Figma/Antigravity design system and components for AI Hub.
Provides:
  - Sticky glassmorphism horizontal nav (replacing st.tabs to fix tab-scroll & bottom dock bugs)
  - Sessions checklist & history manager in sidebar (New Chat, Rename, Delete)
  - Bottom-docked prompt input with native multi-file attachments
  - Sticky model selector toolbar with two-line metadata popover & official SVG logos
  - Keyboard shortcuts (Ctrl+K focus prompt, Ctrl+Shift+K new chat)
  - Safe media expansion via st.dialog (fixing fullscreen minimize bugs)
"""
import time
import uuid
import base64
from pathlib import Path
from typing import Callable, Iterator, Union, List, Dict, Any

import streamlit as st
import streamlit.components.v1 as components

# --------------------------------------------------------------------------- #
# 0. Navigation & Models Configuration
# --------------------------------------------------------------------------- #
NAV = [
    "⚡ Conversational Studio",
    "◈ Visual & Document Auditor",
    "✦ Free Image & Video Studio",
    "↗ Deployment & Guide",
]

MODELS: List[Dict[str, Any]] = [
    # --- Groq Cloud LPU ---
    dict(id="groq:qwen/qwen3.8-27b", provider="Groq", name="Qwen 3.8 27B",
         ctx="131K", cutoff="Mar 2026", speed="~320 tok/s"),
    dict(id="groq:openai/gpt-oss-120b", provider="Groq", name="OpenAI GPT-OSS 120B",
         ctx="131K", cutoff="Mid 2026", speed="~150 tok/s"),
    dict(id="groq:openai/gpt-oss-20b", provider="Groq", name="OpenAI GPT-OSS 20B",
         ctx="65K", cutoff="Early 2026", speed="~450 tok/s"),
    dict(id="groq:meta-llama/llama-3.3-70b-versatile", provider="Groq", name="Llama 3.3 70B Versatile",
         ctx="128K", cutoff="Dec 2025", speed="~280 tok/s"),

    # --- Google Gemini Cloud ---
    dict(id="gemini:gemini-3.5-flash", provider="Gemini", name="Google Gemini 3.5 Flash",
         ctx="1M", cutoff="Feb 2026", speed="~120 tok/s"),
    dict(id="gemini:gemini-3.5-flash-lite", provider="Gemini", name="Google Gemini 3.5 Flash Lite",
         ctx="1M", cutoff="Feb 2026", speed="~210 tok/s"),
    dict(id="gemini:gemini-3.8-flash", provider="Gemini", name="Google Gemini 3.8 Flash (Preview)",
         ctx="1M", cutoff="Apr 2026", speed="~110 tok/s"),

    # --- OpenRouter Free Cluster ---
    dict(id="openrouter:google/gemma-4-31b-it:free", provider="OpenRouter", name="Gemma 4 31B IT (Free)",
         ctx="32K", cutoff="Early 2026", speed="~80 tok/s"),
    dict(id="openrouter:nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free", provider="OpenRouter", name="Nemotron 3 Nano Omni 30B (Free)",
         ctx="65K", cutoff="Mid 2026", speed="~65 tok/s"),
    dict(id="openrouter:nvidia/nemotron-3.5-lightning:free", provider="OpenRouter", name="Nemotron 3.5 Lightning (Free)",
         ctx="32K", cutoff="Mid 2026", speed="~140 tok/s"),
    dict(id="openrouter:openrouter/free", provider="OpenRouter", name="OpenRouter Smart Auto-Free Router",
         ctx="Dynamic", cutoff="Active 2026", speed="~180 tok/s"),

    # --- Adaption Labs LoRA Mesh ---
    dict(id="adaption:adaption/base-router", provider="Adaption", name="Adaption Labs Base Router",
         ctx="32K", cutoff="Continuous", speed="~180 tok/s"),

    # --- Google Colab Dedicated GPU ---
    dict(id="colab:qwen/qwen-2.5-7b-local", provider="Colab GPU", name="Qwen 2.5 7B (Colab 16GB Dedicated GPU)",
         ctx="32K", cutoff="Local T4 Session", speed="~75 tok/s"),
]

PROVIDER_EMOJI = {
    "Groq": "⚡",
    "Gemini": "✨",
    "OpenRouter": "🧠",
    "Colab GPU": "🚀",
    "Adaption": "🧩"
}

LOGO_DIR = Path("assets/logos")

STARTERS = {
    "✦ Pitch": "Write a 60-second hackathon pitch for this project.",
    "⬡ Arch Flow": "Draw the architecture flow for this project as a clean Mermaid flowchart TD with quoted labels.",
    "◈ Code Review": "Review the attached code for bugs, security issues, performance bottlenecks, and quick wins.",
    "⚡ Fast MVP": "Give me the fastest 24-hour MVP build plan with an actionable task split for 3 engineers.",
}

# --------------------------------------------------------------------------- #
# 1. CSS Design Tokens & Styling
# --------------------------------------------------------------------------- #
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root{
  --bg:#0c0e14; --panel:#141721; --panel-2:#161922; --line:#232838;
  --line-soft:rgba(255,255,255,.08); --accent:#6366f1;
  --accent-soft:rgba(99,102,241,.14); --text:#e6e8ef; --muted:#8b91a5;
  --ease:150ms ease;
  --dock-h:5.5rem;
}

/* RULE: Never put backdrop-filter/transform/filter on root wrappers (.stApp, stMain, .block-container).
   Only style leaf elements to preserve fixed overlay and dialog behaviors. */
.stApp{background:var(--bg);color:var(--text)}
.stApp, .stApp p, .stApp label, .stApp li, .stApp input, .stApp textarea,
.stApp button, .stApp h1, .stApp h2, .stApp h3{
  font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif}
[data-testid="stHeader"]{background:transparent}
[data-testid="stSidebar"]{background:var(--panel);border-right:1px solid var(--line)}
.block-container{max-width:980px;padding-top:1rem;padding-bottom:7rem}

/* ---- Sticky Glass Navigation (st.radio key="nav") ---- */
.st-key-nav{position:sticky;top:3.75rem;z-index:100;padding:.45rem 0;
  background:rgba(12,14,20,.85);-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);
  border-bottom:1px solid var(--line)}
.st-key-nav [role="radiogroup"]{display:flex;flex-wrap:nowrap;gap:.35rem;overflow-x:auto}
.st-key-nav label{margin:0;padding:.5rem .95rem;border-radius:10px;cursor:pointer;
  color:var(--muted);white-space:nowrap;transition:background var(--ease),color var(--ease);font-size:0.92rem;font-weight:500}
.st-key-nav label>div:first-child{display:none} /* hide radio dot */
.st-key-nav label:hover{background:var(--accent-soft);color:var(--text)}
.st-key-nav label:has(input:checked){background:var(--accent-soft);color:#fff;
  box-shadow:inset 0 -2px 0 var(--accent)}

/* ---- Chat Messages ---- */
[data-testid="stChatMessage"]{background:var(--panel);border:1px solid var(--line-soft);
  border-radius:14px;padding:1rem 1.15rem;margin-bottom:.75rem;box-shadow:0 4px 12px rgba(0,0,0,0.25)}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]){
  background:rgba(99,102,241,.08);border-color:rgba(99,102,241,.25)}
[data-testid="stCode"] pre, pre{background:#0f1117 !important;border:1px solid var(--line);
  border-radius:10px}

/* ---- Bottom Prompt Dock ---- */
[data-testid="stBottom"]>div{background:linear-gradient(to top,var(--bg) 75%,transparent)}
[data-testid="stChatInput"]{background:var(--panel);border:1px solid var(--line);
  border-radius:16px;transition:border-color var(--ease),box-shadow var(--ease)}
[data-testid="stChatInput"]:focus-within{border-color:var(--accent);
  box-shadow:0 0 0 3px var(--accent-soft)}
.st-key-dock_toolbar{position:sticky;bottom:var(--dock-h);z-index:50;padding:.25rem 0}

/* ---- Buttons ---- */
button[data-testid^="stBaseButton"]{background:var(--panel);border:1px solid var(--line);
  border-radius:10px;color:var(--text);
  transition:border-color var(--ease),transform var(--ease),box-shadow var(--ease)}
button[data-testid^="stBaseButton"]:hover{border-color:var(--accent);transform:translateY(-1px);
  box-shadow:0 4px 14px rgba(99,102,241,.18)}
button[data-testid="stBaseButton-primary"]{background:var(--accent);border-color:var(--accent);color:#fff}

/* ---- Popovers & Selectbox Listbox (Readable & Un-Clipped) ---- */
[data-testid="stPopoverBody"]{background:var(--panel-2);border:1px solid var(--line);
  border-radius:14px;min-width:min(460px,94vw);max-height:70vh;overflow:auto;box-shadow:0 12px 36px rgba(0,0,0,0.6)}
[data-baseweb="popover"] > div{background:var(--panel-2)}
[data-baseweb="popover"] ul[role="listbox"]{min-width:440px}
[data-baseweb="popover"] ul[role="listbox"] li{height:auto;min-height:2.4rem;
  white-space:normal;line-height:1.35;padding-top:.4rem;padding-bottom:.4rem}
[data-testid="stPopoverBody"] [role="radiogroup"] label{padding:.55rem .75rem;border-radius:10px;
  border:1px solid transparent;transition:background var(--ease)}
[data-testid="stPopoverBody"] [role="radiogroup"] label:hover{background:var(--accent-soft)}
[data-testid="stPopoverBody"] [role="radiogroup"] label:has(input:checked){
  background:var(--accent-soft);border-color:rgba(99,102,241,.4)}

/* ---- Dialog (Native Close & Esc) & Fullscreen Frame ---- */
div[role="dialog"]{background:var(--panel);border:1px solid var(--line);border-radius:16px}
div[role="dialog"] button[aria-label="Close"]{
  background:rgba(239,68,68,.2) !important;border:1px solid rgba(239,68,68,.5) !important;
  color:#fca5a5 !important;border-radius:8px !important;padding:4px 8px !important;
  font-weight:700 !important;transition:all var(--ease) !important}
div[role="dialog"] button[aria-label="Close"]:hover{
  background:#ef4444 !important;color:#fff !important;box-shadow:0 0 15px rgba(239,68,68,.6) !important}
[data-testid="stFullScreenFrame"]{z-index:2147483640 !important;background:rgba(7,8,13,.98) !important}
[data-testid="stFullScreenFrame"] button{
  position:fixed !important;top:1.25rem !important;right:1.5rem !important;z-index:2147483647 !important;
  background:#ef4444 !important;color:#fff !important;border:2px solid #fff !important;border-radius:9999px !important;
  padding:.55rem 1.35rem !important;font-weight:700 !important;font-size:.95rem !important;
  box-shadow:0 4px 25px rgba(239,68,68,.85) !important;cursor:pointer !important}

/* ---- Badges & Cards ---- */
.badge{display:inline-block;margin:.35rem .35rem 0 0;padding:.12rem .55rem;border-radius:999px;
  font-size:.75rem;color:var(--muted);background:rgba(255,255,255,.04);
  border:1px solid var(--line-soft)}
.model-card{display:flex;align-items:center;gap:.75rem;padding:.65rem .9rem;margin:.2rem 0 .6rem;
  background:var(--panel);border:1px solid var(--line);border-radius:12px}
.model-card img{width:22px;height:22px;flex-shrink:0}
.model-card .t{font-weight:600;font-size:0.95rem;color:#ffffff}
.model-card .m{color:var(--muted);font-size:.8rem}
.empty{text-align:center;padding:2.5rem 1rem;color:var(--muted);background:var(--panel);
  border:1px solid var(--line);border-radius:16px;margin:1rem 0}
.empty b{display:block;color:var(--text);font-size:1.05rem;margin-bottom:.3rem}

/* Hidden JS iframe zero gap */
[data-testid="stElementContainer"]:has(> iframe[height="0"]){height:0;margin:0;overflow:hidden}

@media (prefers-reduced-motion: reduce){*{transition:none !important}}
</style>
"""

def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
# 2. JS: Shortcuts & Auto-Scroll
# --------------------------------------------------------------------------- #
_KEYS_JS = """
<script>
const w = window.parent, d = w.document;
if (!w.__hubKeys) {
  w.__hubKeys = true;
  d.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      if (e.shiftKey) { // Ctrl+Shift+K -> New Chat
        const b = [...d.querySelectorAll('button')].find(x => x.innerText.includes('New chat'));
        if (b) b.click();
      } else { // Ctrl+K -> Focus prompt textarea
        const t = d.querySelector('[data-testid="stChatInputTextArea"]');
        if (t) t.focus();
      }
    }
  });
}
</script>
"""

def inject_js():
    components.html(_KEYS_JS, height=0)

def scroll_bottom():
    components.html(f"""<script>/*{time.time()}*/
      const m = window.parent.document.querySelector('[data-testid="stMain"]');
      if (m) m.scrollTo({{top: m.scrollHeight, behavior: 'smooth'}});
    </script>""", height=0)

# --------------------------------------------------------------------------- #
# 3. Sticky Navigation
# --------------------------------------------------------------------------- #
def nav() -> str:
    return st.radio("nav", NAV, horizontal=True, key="nav", label_visibility="collapsed")

# --------------------------------------------------------------------------- #
# 4. Model Selector with Official Logos & 2-Line Metadata Popover
# --------------------------------------------------------------------------- #
def logo_uri(provider: str) -> Union[str, None]:
    key = provider.lower().replace(" gpu", "").replace(" ", "")
    p = LOGO_DIR / f"{key}.svg"
    if p.exists():
        return "data:image/svg+xml;base64," + base64.b64encode(p.read_bytes()).decode()
    return None

def _model(models: List[Dict[str, Any]], mid: str) -> Dict[str, Any]:
    return next((m for m in models if m["id"] == mid), models[0])

def _pick(key: str):
    st.session_state[key] = st.session_state[f"{key}_radio"]

def model_card(m: Dict[str, Any]):
    uri = logo_uri(m["provider"])
    icon = f'<img src="{uri}">' if uri else f'<span>{PROVIDER_EMOJI.get(m["provider"], "●")}</span>'
    st.markdown(
        f'<div class="model-card">{icon}<div><div class="t">{m["name"]}</div>'
        f'<div class="m">{m["provider"]} · {m["ctx"]} context · cutoff {m["cutoff"]} · {m["speed"]}</div>'
        f'</div></div>', unsafe_allow_html=True)

def model_selector(models=MODELS, key="model") -> Dict[str, Any]:
    ss = st.session_state
    ss.setdefault(key, models[0]["id"])
    cur = _model(models, ss[key])

    uri = logo_uri(cur["provider"])
    label_prefix = f'{PROVIDER_EMOJI.get(cur["provider"], "●")}'
    with st.popover(f'{label_prefix} {cur["name"]}'):
        providers = ["All"] + sorted({m["provider"] for m in models})
        prov = st.pills("Provider Filter", providers, default="All", key=f"{key}_prov") or "All"
        pool = [m for m in models if prov == "All" or m["provider"] == prov]
        ids = [m["id"] for m in pool]
        by_id = {m["id"]: m for m in pool}
        st.radio(
            "Model Selection", ids,
            index=ids.index(cur["id"]) if cur["id"] in ids else 0,
            key=f"{key}_radio", on_change=_pick, args=(key,),
            format_func=lambda i: f'{by_id[i]["name"]} ({by_id[i]["provider"]})',
            captions=[f'{m["ctx"]} context · cutoff {m["cutoff"]} · {m["speed"]}'
                      for m in pool],
        )
    return _model(models, ss[key])

# --------------------------------------------------------------------------- #
# 5. Chat Sessions Checklist & History
# --------------------------------------------------------------------------- #
def _new_session():
    sid = uuid.uuid4().hex[:8]
    st.session_state.sessions[sid] = {"title": "New chat", "messages": [], "ts": time.time()}
    st.session_state.active = sid
    try:
        from session_manager import save_session
        save_session(sid, "New chat", [])
    except Exception:
        pass

def _init():
    ss = st.session_state
    if "sessions" not in ss:
        ss.sessions = {}
        try:
            from session_manager import get_all_sessions, load_session
            for s in get_all_sessions():
                loaded = load_session(s["id"])
                if loaded:
                    ss.sessions[s["id"]] = {
                        "title": loaded.get("title", s.get("title", "Chat")),
                        "messages": loaded.get("messages", []),
                        "ts": loaded.get("updated_at", s.get("updated_at", time.time()))
                    }
        except Exception:
            pass
    if "active" not in ss or ss.active not in ss.sessions:
        if ss.sessions:
            ss.active = max(ss.sessions, key=lambda k: ss.sessions[k]["ts"])
        else:
            _new_session()

def _switch(sid: str):
    st.session_state.active = sid

def _delete(sid: str):
    ss = st.session_state
    ss.sessions.pop(sid, None)
    try:
        from session_manager import delete_session
        delete_session(sid)
    except Exception:
        pass
    if ss.get("active") == sid:
        if ss.sessions:
            ss.active = max(ss.sessions, key=lambda k: ss.sessions[k]["ts"])
        else:
            _new_session()

def _rename(sid: str):
    v = st.session_state.get(f"rn_{sid}", "").strip()
    if v:
        st.session_state.sessions[sid]["title"] = v
        try:
            from session_manager import save_session
            save_session(sid, v, st.session_state.sessions[sid]["messages"])
        except Exception:
            pass

def render_sidebar_sessions():
    _init()
    ss = st.session_state
    st.button("➕ New chat", key="new_chat", type="primary", use_container_width=True,
              on_click=_new_session)
    st.caption("Chat History (Persisted Checklist)")
    for sid, s in sorted(ss.sessions.items(), key=lambda kv: -kv[1]["ts"]):
        c1, c2 = st.columns([5, 1], vertical_alignment="center")
        is_active = (sid == ss.active)
        prefix = "● " if is_active else ""
        c1.button(prefix + s["title"][:24],
                  key=f"open_{sid}", use_container_width=True, on_click=_switch, args=(sid,))
        with c2.popover("⋮"):
            st.text_input("Rename", s["title"], key=f"rn_{sid}",
                          on_change=_rename, args=(sid,))
            st.button("🗑 Delete chat", key=f"del_{sid}", on_click=_delete, args=(sid,))

def render_sidebar():
    with st.sidebar:
        render_sidebar_sessions()

# --------------------------------------------------------------------------- #
# 6. Chat Rendering with Streaming, Files & Dock
# --------------------------------------------------------------------------- #
_TEXT_EXT = (".py", ".js", ".ts", ".tsx", ".json", ".md", ".txt", ".csv", ".html", ".css",
             ".yml", ".yaml", ".ipynb", ".java", ".c", ".cpp", ".v", ".sv", ".sh", ".sql")

def _badges(meta: Dict[str, Any]):
    parts = [f'⏱ {meta["secs"]:.1f}s', f'≈ {meta["tokens"]} tok', f'{meta["provider"]} · {meta["model"]}']
    st.markdown("".join(f'<span class="badge">{p}</span>' for p in parts), unsafe_allow_html=True)

def _read_input(raw):
    if raw is None:
        return None, []
    if isinstance(raw, str):
        return raw, []
    text = getattr(raw, "text", None) or (raw.get("text") if hasattr(raw, "get") else "") or ""
    files = getattr(raw, "files", None) or (raw.get("files") if hasattr(raw, "get") else []) or []
    return text, list(files)

def _chat_input():
    try:
        return st.chat_input("Ask anything (ideas, architecture, code, business model)...",
                             accept_file="multiple")
    except TypeError:
        return st.chat_input("Ask anything (ideas, architecture, code, business model)...")

def render_chat(generate: Callable):
    """
    generate(model: dict, messages: list[dict], attachments: list[dict]) -> str | Iterator[str]
    attachments items: {"name": str, "mime": str, "data": bytes}
    """
    _init()
    ss = st.session_state
    sess = ss.sessions[ss.active]

    for m in sess["messages"]:
        with st.chat_message(m["role"]):
            if m.get("files"):
                st.caption("📎 " + ", ".join(m["files"]))
            st.markdown(m["content"])
            if m["role"] == "assistant" and m.get("meta"):
                _badges(m["meta"])

    queued = None
    if not sess["messages"]:
        st.markdown('<div class="empty"><b>AI Studio Ready</b>Ask anything, attach code or '
                    'files in the box below, or pick a starter prompt.</div>', unsafe_allow_html=True)
        cols = st.columns(len(STARTERS))
        for col, (label, text) in zip(cols, STARTERS.items()):
            if col.button(label, key=f"st_{label}", use_container_width=True):
                queued = text

    # Sticky toolbar directly above prompt dock
    with st.container(key="dock_toolbar"):
        c1, c2 = st.columns([3.5, 6.5], vertical_alignment="center")
        with c1:
            model = model_selector()
        c2.caption("⌨️ `Ctrl+K` focus prompt · `Ctrl+Shift+K` new chat")

    text, files = _read_input(_chat_input())
    text = queued or text
    if not text:
        if ss.pop("_scroll", False):
            scroll_bottom()
        return

    attachments, inline = [], []
    for f in files:
        data = f.getvalue()
        if f.name.lower().endswith(_TEXT_EXT):
            inline.append(f"\n\n```{f.name}\n{data.decode('utf-8', 'ignore')}\n```")
        else:
            attachments.append({"name": f.name, "mime": f.type, "data": data})
    full = text + "".join(inline)

    sess["messages"].append({"role": "user", "content": full, "files": [f.name for f in files]})
    if sess["title"] == "New chat":
        sess["title"] = text[:36]
    sess["ts"] = time.time()
    with st.chat_message("user"):
        if files:
            st.caption("📎 " + ", ".join(f.name for f in files))
        st.markdown(full)

    msgs = [{"role": m["role"], "content": m["content"]} for m in sess["messages"]]
    with st.chat_message("assistant"):
        t0 = time.perf_counter()
        try:
            out = generate(model, msgs, attachments)
            if isinstance(out, str):
                st.markdown(out)
                reply = out
            else:
                reply = st.write_stream(out)
        except Exception as e:
            reply = f"⚠️ {model['provider']} failed: `{e}`"
            st.error(reply)
        meta = {"secs": time.perf_counter() - t0, "tokens": max(1, len(reply) // 4),
                "provider": model["provider"], "model": model["name"]}
        _badges(meta)

    sess["messages"].append({"role": "assistant", "content": reply, "meta": meta})
    try:
        from session_manager import save_session
        save_session(ss.active, sess["title"], sess["messages"])
    except Exception:
        pass
    ss["_scroll"] = True
    st.rerun()

# --------------------------------------------------------------------------- #
# 7. Media Preview with Native st.dialog (Working Close, Esc & Minimize)
# --------------------------------------------------------------------------- #
@st.dialog("Media Preview & Fullscreen", width="large")
def _preview(kind: str, src):
    top_c1, top_c2 = st.columns([3.5, 1.5])
    with top_c1:
        st.markdown(f"#### ⛶ Fullscreen {kind.capitalize()} Viewer")
    with top_c2:
        if st.button("✕ Close (Esc)", key=f"preview_close_top_{kind}", type="primary", use_container_width=True):
            st.rerun()

    if kind == "image":
        st.image(src, use_container_width=True)
    elif kind == "video":
        st.video(src)
    elif kind == "audio":
        st.audio(src)

    bot_c1, bot_c2 = st.columns([1, 1])
    with bot_c1:
        if st.button("✕ Exit Fullscreen", key=f"preview_close_bot_{kind}", use_container_width=True):
            st.rerun()
    with bot_c2:
        if isinstance(src, bytes):
            ext = "png" if kind == "image" else ("mp4" if kind == "video" else "wav")
            mime = f"image/{ext}" if kind == "image" else (f"video/{ext}" if kind == "video" else f"audio/{ext}")
            st.download_button(f"⬇️ Download {kind.capitalize()}", data=src, file_name=f"media_export.{ext}", mime=mime, key=f"dl_dlg_{kind}", use_container_width=True)

def media_card(kind: str, src, key: str):
    """kind = 'image' | 'video' | 'audio'; src = url, path or bytes."""
    if kind == "image":
        st.image(src, use_container_width=True)
    elif kind == "video":
        st.video(src)
    elif kind == "audio":
        st.audio(src)
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("⛶ Expand Fullscreen", key=f"exp_{key}", use_container_width=True):
            _preview(kind, src)
    with c2:
        if isinstance(src, bytes):
            ext = "png" if kind == "image" else ("mp4" if kind == "video" else "wav")
            mime = f"image/{ext}" if kind == "image" else (f"video/{ext}" if kind == "video" else f"audio/{ext}")
            st.download_button("⬇️ Download", data=src, file_name=f"{key}.{ext}", mime=mime, key=f"dl_card_{key}", use_container_width=True)

