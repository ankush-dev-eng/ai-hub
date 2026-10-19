"""
history_ui.py - Streamlit glue for history_db.

    hui.ensure_session()      # top of render_chat (replaces ss.setdefault("hist", []))
    hui.sidebar()             # chat list / search / manage - call BEFORE the settings sidebar
    mid = hui.save_user(display_text, full_content, image_data_uris)
    th  = hui.start_title(reg, chain, user_text)        # first message only; runs in a thread
    aid = hui.save_assistant(text, used)
"""
import re
import threading

import streamlit as st

import history_db as hdb


# ---------- session state ----------
def _load(sid):
    out = []
    for m in hdb.get_messages(sid):
        meta = m["meta"]
        imgs = [u for u in (hdb.load_image(n) for n in meta.get("images", [])) if u]
        out.append({"id": m["id"], "role": m["role"], "content": m["content"], "images": imgs,
                    "used": meta.get("used"), "display": meta.get("display"), "citations": meta.get("citations"),
                    "trace": meta.get("trace"), "telemetry": meta.get("telemetry")})
    return out


def _switch(sid):
    ss = st.session_state
    ss.sid = sid
    ss.ch_hist = _load(sid) if sid else []
    ss.hist = ss.ch_hist
    st.query_params["s"] = sid or "new"          # survives browser refresh


def ensure_session():
    ss = st.session_state
    if "sid" in ss and ss.sid is not None:
        return
    hdb.init()
    try:
        from voice_hub import prune_tts_cache
        prune_tts_cache()
    except Exception:
        pass
    want = st.query_params.get("s")
    if want == "new":
        sid = None
    elif want and hdb.session_exists(want):
        sid = want
    else:
        sid = hdb.latest_session()               # fresh start: reopen the last chat
    _switch(sid)


# ---------- sidebar ----------
def sidebar():
    ss, sb = st.session_state, st.sidebar
    sb.markdown("### 💬 Chats")
    if sb.button("➕ New chat", use_container_width=True):
        _switch(None)
        st.rerun()
    q = sb.text_input("Search chats", placeholder="Search titles and messages...", label_visibility="collapsed")
    rows = hdb.list_sessions(q)
    if not rows:
        sb.caption("No matches." if q else "No saved chats yet.")
    for r in rows:
        cur = r["id"] == ss.sid
        if sb.button(("● " if cur else "") + r["title"], key=f"s_{r['id']}", use_container_width=True,
                     type="primary" if cur else "secondary") and not cur:
            _switch(r["id"])
            st.rerun()

    if ss.sid:
        with sb.expander("⚙️ Manage this chat"):
            title = hdb.get_title(ss.sid)
            new = st.text_input("Title", value=title, key=f"rn_{ss.sid}")
            if st.button("Rename", key=f"rnb_{ss.sid}", use_container_width=True) and new.strip():
                hdb.rename(ss.sid, new)
                st.rerun()
            st.download_button("⬇ Transcript (.md)", hdb.export_markdown(ss.sid),
                                f"{re.sub(r'[^A-Za-z0-9_-]+', '_', title)[:40] or 'chat'}.md",
                                use_container_width=True)
            st.download_button("⬇ JSON", hdb.export_json(ss.sid), "chat.json", use_container_width=True)
            ok = st.checkbox("Confirm delete", key=f"dc_{ss.sid}")
            if st.button("🗑 Delete chat", key=f"db_{ss.sid}", disabled=not ok, use_container_width=True):
                hdb.delete_session(ss.sid)
                _switch(None)
                st.rerun()


# ---------- persistence ----------
def save_user(display: str, content: str, images: list) -> int:
    ss = st.session_state
    if ss.sid is None:                            # chats are created lazily: no empty sessions
        ss.sid = hdb.new_session(hdb.heuristic_title(display))
        st.query_params["s"] = ss.sid
    refs = [r for r in (hdb.save_image(u) for u in images) if r]
    return hdb.add_message(ss.sid, "user", content, {"images": refs, "display": display})


def save_assistant(text: str, used: str, meta: dict | None = None) -> int:
    m = {"used": used}
    if meta:
        m.update(meta)
    return hdb.add_message(st.session_state.sid, "assistant", text, m)


def drop_message(mid: int):
    hdb.delete_message(mid)


# ---------- auto-title ----------
def _clean_title(t: str) -> str:
    t = re.sub(r"<think>.*?</think>", "", t or "", flags=re.S).strip()
    t = t.splitlines()[0] if t else ""
    t = re.sub(r"[\"“”'`*#.!?:]+", "", t).strip()
    return " ".join(t.split()[:6])[:48]


def _llm_title(reg, chain, text):
    from openai import OpenAI
    prompt = [
        {"role": "system", "content": "Write a 4-5 word title for this chat. Reply with the title only: "
                                      "no quotes, no punctuation, no preamble."},
        {"role": "user", "content": text[:600]},
    ]
    for pname, model in chain[:3]:
        try:
            p = reg[pname]
            r = OpenAI(base_url=p["base_url"], api_key=p["key"], timeout=12).chat.completions.create(
                model=model, messages=prompt, max_tokens=24, temperature=0.3)
            t = _clean_title(r.choices[0].message.content)
            if t:
                return t
        except Exception:
            continue
    return ""


def start_title(reg, chain, user_text: str):
    """Runs while the main reply streams. Thread touches only SQLite, never st.*"""
    sid = st.session_state.sid

    def work():
        t = _llm_title(reg, chain, user_text)
        if t:
            hdb.auto_title(sid, t)

    th = threading.Thread(target=work, daemon=True)
    th.start()
    return th
