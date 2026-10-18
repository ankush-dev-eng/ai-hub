"""
chat_hub.py - Unified Multi-Provider AI Studio with Local ChromaDB RAG,
Model Arena Side-by-Side Compare Mode, and Instant Cloudflare Colab Endpoints.

Supported Protocol: Universal OpenAI-compatible API
Default Providers: Groq LPU, Google Gemini Flash, OpenRouter, Google Colab T4 Ollama
RAG Engine: Local ChromaDB + ONNX all-MiniLM-L6-v2 (Zero GPU, 100% Free & Offline)
"""

import base64
import io
import json
import os
import pathlib
import time
from types import SimpleNamespace
from typing import Dict, List, Tuple, Generator, Any

from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from openai import OpenAI

import voice_hub
import history_ui as hui
import history_db as hdb

ENDPOINTS_FILE = pathlib.Path("endpoints.json")

# Verified Production 2026 Model IDs
BUILTIN = {
    "Groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
        "models": ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"],
    },
    "Gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "key_env": "GEMINI_API_KEY",
        "models": ["gemini-3.8-flash", "gemini-3.5-flash-lite"],
    },
    "OpenRouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "key_env": "OPENROUTER_API_KEY",
        "models": ["nvidia/nemotron-3.5-lightning:free", "nvidia/nemotron-3.5-super-vl:free"],
    },
}

PERSONAS = {
    "Default Assistant": "You are a sharp, highly capable AI assistant. Answer directly, show clean code with explanations, and state any uncertainties honestly.",
    "Senior Code Reviewer": "You review code like a Principal Engineer: bugs and edge cases first, then algorithmic complexity & performance, then styling. Always provide drop-in code fixes.",
    "Hackathon Mentor": "You are a battle-tested hackathon mentor. Prioritize features that ship in hours, cut unnecessary scope ruthlessly, and optimize for live demo impact.",
    "Intuitive Teacher": "Explain step by step using relatable analogies and concise real-world examples. Assume the reader is smart but new to the topic.",
}

TEXT_EXT = {".py", ".js", ".ts", ".md", ".json", ".csv", ".txt", ".html", ".css", ".c", ".cpp", ".rs", ".go", ".sql", ".sh"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}


# --------------------------------------------------------------------------- #
# Configuration & Provider Registry
# --------------------------------------------------------------------------- #
def secret(name: str) -> str:
    v = os.getenv(name)
    if v:
        return v
    try:
        if hasattr(st, "secrets") and name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return ""


def load_custom() -> Dict[str, Any]:
    try:
        if ENDPOINTS_FILE.exists():
            return json.loads(ENDPOINTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def save_custom(data: Dict[str, Any]):
    ENDPOINTS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def registry() -> Dict[str, Dict[str, Any]]:
    reg = {}
    for name, p in BUILTIN.items():
        key = secret(p["key_env"])
        if key:
            reg[name] = {"base_url": p["base_url"], "key": key, "models": list(p["models"])}
    for name, p in load_custom().items():
        reg[name] = {
            "base_url": p["base_url"],
            "key": p.get("key") or "none",
            "models": p.get("models", ["default"]),
        }
    return reg


# --------------------------------------------------------------------------- #
# Local ChromaDB Vector RAG Engine (100% Free, Offline, CPU-accelerated)
# --------------------------------------------------------------------------- #
@st.cache_resource
def get_chroma_client():
    try:
        import chromadb
        return chromadb.Client()
    except Exception as e:
        return None


def get_session_collection(session_id: str):
    client = get_chroma_client()
    if client is None:
        return None
    coll_name = f"rag_{session_id.replace('-', '_')[:40]}"
    try:
        return client.get_or_create_collection(coll_name)
    except Exception:
        return None


def chunk_document_text(text: str, chunk_size: int = 600, overlap: int = 100) -> List[str]:
    chunks = []
    start = 0
    clean_text = text.strip()
    while start < len(clean_text):
        end = min(start + chunk_size, len(clean_text))
        chunk = clean_text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(clean_text):
            break
        start += chunk_size - overlap
    return chunks


def index_attachments_in_rag(collection, files, session_id: str):
    if collection is None or not files:
        return 0

    indexed_count = 0
    for f in files:
        fname = f.name
        ext = pathlib.Path(fname).suffix.lower()
        data = f.getvalue()
        text_content = ""

        if ext == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(data))
                text_content = "\n".join((p.extract_text() or "") for p in reader.pages)
            except Exception:
                try:
                    import pdfplumber
                    with pdfplumber.open(io.BytesIO(data)) as pdf:
                        text_content = "\n".join((p.extract_text() or "") for p in pdf.pages)
                except Exception:
                    pass
        elif ext in TEXT_EXT:
            try:
                text_content = data.decode("utf-8", errors="replace")
            except Exception:
                text_content = str(data)

        if text_content and len(text_content.strip()) > 30:
            chunks = chunk_document_text(text_content, chunk_size=600, overlap=100)
            for i, chunk in enumerate(chunks):
                doc_id = f"{session_id}_{fname}_{i}"
                try:
                    collection.add(
                        documents=[chunk],
                        metadatas=[{"source": fname, "chunk_idx": i, "total_chunks": len(chunks)}],
                        ids=[doc_id]
                    )
                    indexed_count += 1
                except Exception:
                    pass
    return indexed_count


def query_rag_context(collection, query: str, top_k: int = 3) -> Tuple[str, List[Dict[str, Any]]]:
    if collection is None or not query:
        return "", []

    try:
        count = collection.count()
        if count == 0:
            return "", []

        k = min(top_k, count)
        results = collection.query(query_texts=[query], n_results=k)

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        context_lines = []
        citations = []
        for d, m in zip(docs, metas):
            source = m.get("source", "document")
            c_idx = m.get("chunk_idx", 0)
            context_lines.append(f"--- [Document: {source} (Chunk {c_idx+1})] ---\n{d}\n")
            citations.append({"source": source, "chunk": c_idx + 1, "text": d[:160] + "..."})

        rag_prompt = "\n".join(context_lines)
        return rag_prompt, citations
    except Exception:
        return "", []


# --------------------------------------------------------------------------- #
# Inference & Streaming
# --------------------------------------------------------------------------- #
def stream_one(p: Dict[str, Any], model: str, messages: List[Dict[str, Any]], temp: float) -> Generator[str, None, None]:
    c = OpenAI(base_url=p["base_url"], api_key=p["key"], timeout=90.0)
    resp = c.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temp,
        stream=True
    )
    for ch in resp:
        if ch.choices and ch.choices[0].delta and ch.choices[0].delta.content:
            yield ch.choices[0].delta.content


def run_chain(reg: Dict[str, Any], chain: List[Tuple[str, str]], messages: List[Dict[str, Any]], temp: float, slot, speaker=None) -> Tuple[str, str]:
    """Tries each (provider, model) in chain until one completes successfully."""
    for pname, model in chain:
        text = ""
        try:
            for delta in stream_one(reg[pname], model, messages, temp):
                text += delta
                slot.markdown(text + " ▌")
                if speaker:
                    speaker.feed(delta)
            slot.markdown(text)
            if speaker:
                speaker.flush()
            return text, f"{pname} · {model}"
        except Exception as e:
            if speaker:
                speaker.restart()
            err_msg = str(e)[:90]
            st.toast(f"⚠️ {pname} failed ({err_msg}) — Routing to next fallback...", icon="⚡")
    if speaker:
        speaker.close()
    fallback_msg = "⚠️ All providers in failover chain failed. Please verify API keys, active models, or Colab tunnel status."
    slot.markdown(fallback_msg)
    return fallback_msg, "none"


def web_context(q: str) -> str:
    try:
        from duckduckgo_search import DDGS
        rows = DDGS().text(q, max_results=4)
        if rows:
            return "\n".join(f"- **{r.get('title', '')}**: {r.get('body', '')} ([Link]({r.get('href', '')}))" for r in rows)
    except Exception:
        pass
    return ""


def parse_files(files) -> Tuple[str, List[str]]:
    text, imgs = "", []
    for f in files or []:
        ext = pathlib.Path(f.name).suffix.lower()
        data = f.getvalue()
        if ext in IMG_EXT:
            mime = "image/jpeg" if ext in (".jpg", ".jpeg") else f"image/{ext[1:]}"
            imgs.append(f"data:{mime};base64,{base64.b64encode(data).decode('utf-8')}")
        elif ext == ".pdf":
            try:
                import pypdf
                body = "\n".join((pg.extract_text() or "") for pg in pypdf.PdfReader(io.BytesIO(data)).pages)
                text += f"\n\n--- 📑 ATTACHED PDF: {f.name} ---\n{body[:40000]}\n--- END OF FILE {f.name} ---\n"
            except Exception as e:
                text += f"\n\n[Attached PDF: {f.name} ({len(data)} bytes, unreadable text)]"
        elif ext in TEXT_EXT:
            try:
                decoded = data.decode("utf-8", "ignore")
                text += f"\n\n--- 📄 ATTACHED FILE: {f.name} ---\n```{ext[1:]}\n{decoded[:40000]}\n```\n--- END OF FILE {f.name} ---\n"
            except Exception:
                pass
    return text, imgs


def to_api(system: str, hist: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    msgs = [{"role": "system", "content": system}]
    for m in hist:
        if m.get("images"):
            parts = [{"type": "text", "text": m["content"]}]
            for u in m["images"]:
                parts.append({"type": "image_url", "image_url": {"url": u}})
            msgs.append({"role": m["role"], "content": parts})
        else:
            msgs.append({"role": m["role"], "content": m["content"]})
    return msgs


# --------------------------------------------------------------------------- #
# Sidebar & Controls
# --------------------------------------------------------------------------- #
def sidebar(reg: Dict[str, Any]):
    sb = st.sidebar
    sb.markdown("### 🧠 Studio Settings")

    col_p, col_m = sb.columns(2)
    prov = col_p.selectbox("Provider", list(reg.keys()), key="ch_prov")
    models = reg[prov]["models"]
    model = col_m.selectbox("Model", models, key="ch_model")

    c1, c2 = sb.columns(2)
    failover = c1.toggle("Auto-Failover", True, help="Automatically switches to next available provider if current hits quota/timeout.")
    search = c2.toggle("Web Search", False, help="Injects real-time DuckDuckGo search citations into prompt context.")

    c3, c4 = sb.columns(2)
    use_rag = c3.toggle("Document RAG", True, help="Uses local ChromaDB vector database to retrieve semantically relevant chunks from uploaded files.")
    compare_mode = c4.toggle("Compare Arena", False, help="Runs side-by-side comparison of 2 models on the same prompt.")

    model_b = None
    prov_b = None
    if compare_mode:
        sb.markdown("#### ⚔️ Opponent Model (Arena)")
        col_pb, col_mb = sb.columns(2)
        other_provs = list(reg.keys())
        prov_b = col_pb.selectbox("Opponent Provider", other_provs, index=1 if len(other_provs) > 1 else 0, key="ch_prov_b")
        models_b = reg[prov_b]["models"]
        model_b = col_mb.selectbox("Opponent Model", models_b, key="ch_model_b")

    persona = sb.selectbox("Persona", list(PERSONAS.keys()))
    custom_sys = sb.text_area("Custom System Instruction", "", height=70, placeholder="e.g. Always format responses with bullet points...")
    temp = sb.slider("Temperature", 0.0, 1.2, 0.6, 0.05)

    with sb.expander("➕ Connect Endpoint (Colab T4 / Ollama / vLLM)"):
        st.caption("Paste any Cloudflare tunnel or local OpenAI-compatible endpoint:")
        n = st.text_input("Endpoint Name", placeholder="colab-qwen", key="ep_name")
        u = st.text_input("Base URL", placeholder="https://xxxx.trycloudflare.com/v1", key="ep_url")
        m = st.text_input("Model Name(s)", placeholder="qwen2.5:7b, llama3.1:8b", key="ep_model")
        k = st.text_input("API Key (leave blank for local/colab)", type="password", key="ep_key")
        if st.button("Save Endpoint", use_container_width=True) and n and u and m:
            d = load_custom()
            d[n] = {
                "base_url": u.rstrip("/"),
                "key": k or "none",
                "models": [x.strip() for x in m.split(",") if x.strip()]
            }
            save_custom(d)
            st.success(f"Endpoint '{n}' connected successfully!")
            st.rerun()

        custom = load_custom()
        if custom:
            st.markdown("---")
            rm = st.selectbox("Remove custom endpoint", [""] + list(custom.keys()))
            if rm and st.button(f"Delete {rm}", use_container_width=True):
                custom.pop(rm)
                save_custom(custom)
                st.rerun()

    sb.markdown("---")
    cb1, cb2 = sb.columns(2)
    if cb1.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.ch_hist = []
        st.rerun()

    chat_export = json.dumps([{k: v for k, v in m.items() if k != "images"} for m in st.session_state.get("ch_hist", [])], indent=2)
    cb2.download_button("💾 Export JSON", chat_export, "chat_history.json", mime="application/json", use_container_width=True)

    system = PERSONAS[persona] + ("\n" + custom_sys if custom_sys else "")
    return prov, model, failover, search, use_rag, compare_mode, prov_b, model_b, system, temp


# --------------------------------------------------------------------------- #
# Main Render Entrypoint
# --------------------------------------------------------------------------- #
def render_chat():
    ss = st.session_state
    hui.ensure_session()
    ss.setdefault("ch_hist", [])
    ss.setdefault("session_id", ss.get("sid") or f"session_{int(time.time())}")

    reg = registry()
    if not reg:
        st.warning("⚠️ No AI provider connected. Please configure GROQ_API_KEY or GEMINI_API_KEY in `.env`, or connect a Colab endpoint in the sidebar.")
        return

    hui.sidebar()
    prov, model, failover, search, use_rag, compare_mode, prov_b, model_b, system, temp = sidebar(reg)
    vcfg = voice_hub.sidebar()

    # Render Chat History
    for m in ss.ch_hist:
        with st.chat_message(m["role"]):
            if m.get("is_compare"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**⚡ {m.get('meta_a', 'Model A')}**")
                    st.markdown(m.get("content_a", ""))
                with c2:
                    st.markdown(f"**✨ {m.get('meta_b', 'Model B')}**")
                    st.markdown(m.get("content_b", ""))
            else:
                st.markdown(m["content"])
                if m.get("used"):
                    st.caption(f"⚡ *Served by {m['used']}*")
                if m.get("citations"):
                    with st.expander("📚 RAG Document Citations", expanded=False):
                        for cit in m["citations"]:
                            st.markdown(f"- **{cit['source']}** (Chunk {cit['chunk']}): `{cit['text']}`")

    # Dock toolbar directly above chat input
    with st.container(key="ch_dock_toolbar"):
        col_mic, _ = st.columns([2.2, 7.8])
        with col_mic:
            spoken = voice_hub.mic_input(vcfg)

    # Bottom Sticky Input Dock with Multi-file attachment
    prompt = st.chat_input(
        "Ask anything or attach code, PDF & images...",
        accept_file="multiple",
        file_type=["png", "jpg", "jpeg", "webp", "pdf", "py", "js", "ts", "md", "json", "csv", "txt", "sql", "sh"],
    )

    via_voice = False
    if not prompt and spoken:
        prompt = SimpleNamespace(text=spoken, files=[])
        via_voice = True

    if not prompt:
        return

    user_text = prompt.text or ""
    file_text, imgs = parse_files(prompt.files)

    # Local ChromaDB Vector RAG Indexing
    rag_context = ""
    citations = []
    if use_rag and prompt.files:
        coll = get_session_collection(ss.session_id)
        if coll:
            count = index_attachments_in_rag(coll, prompt.files, ss.session_id)
            if count > 0:
                st.toast(f"📚 Indexed {count} document chunks into local ChromaDB vector store!", icon="🧠")

    if use_rag and user_text:
        coll = get_session_collection(ss.session_id)
        if coll and coll.count() > 0:
            rag_context, citations = query_rag_context(coll, user_text, top_k=3)

    # Append user message
    display_content = user_text or ("*(Attached files)*" if prompt.files else "")
    full_content = user_text + file_text
    hui.save_user(display_content, full_content, imgs)
    ss.ch_hist.append({"role": "user", "content": full_content, "images": imgs})

    with st.chat_message("user"):
        st.markdown(user_text or "*(File attachments)*")
        for u in imgs:
            st.image(u, width=280)
        if prompt.files:
            st.caption("📎 " + ", ".join(f.name for f in prompt.files))

    # Construct Augmented System Prompt
    sys_prompt = system
    if rag_context:
        sys_prompt += f"\n\n[Retrieved Context from Uploaded Documents (Local ChromaDB Semantic Search)]:\n{rag_context}\n[End of Context — Answer using these document facts when relevant]"

    if search and user_text:
        web_res = web_context(user_text)
        if web_res:
            sys_prompt += f"\n\n[Web Search Results via DuckDuckGo]:\n{web_res}\n[End of Web Results — Cite links when appropriate]"

    # Model Arena / Side-by-Side Compare Mode Execution
    if compare_mode and prov_b and model_b:
        with st.chat_message("assistant"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"#### ⚡ {prov} · {model}")
                slot_a = st.empty()
            with c2:
                st.markdown(f"#### ✨ {prov_b} · {model_b}")
                slot_b = st.empty()

            api_msgs = to_api(sys_prompt, ss.ch_hist)
            t0 = time.perf_counter()
            text_a, used_a = run_chain(reg, [(prov, model)], api_msgs, temp, slot_a)
            t_a = time.perf_counter() - t0

            t0 = time.perf_counter()
            text_b, used_b = run_chain(reg, [(prov_b, model_b)], api_msgs, temp, slot_b)
            t_b = time.perf_counter() - t0

            meta_a = f"{used_a} ({t_a:.2f}s)"
            meta_b = f"{used_b} ({t_b:.2f}s)"

        meta_cmp = {"is_compare": True, "meta_a": meta_a, "meta_b": meta_b}
        hui.save_assistant(f"**{meta_a}**:\n{text_a}\n\n**{meta_b}**:\n{text_b}", f"{prov} vs {prov_b}", meta_cmp)
        ss.ch_hist.append({
            "role": "assistant",
            "is_compare": True,
            "content_a": text_a,
            "content_b": text_b,
            "meta_a": meta_a,
            "meta_b": meta_b,
        })
        if len(ss.ch_hist) <= 2:
            hui.start_title(reg, [(prov, model)], user_text)
        st.rerun()

    # Normal Single Streaming Inference with Failover
    chain = [(prov, model)]
    if imgs and "Gemini" in reg and prov != "Gemini":
        chain = [("Gemini", reg["Gemini"]["models"][0])]  # route visual to Gemini Flash
    if failover:
        chain += [(p, reg[p]["models"][0]) for p in reg if p != chain[0][0]]

    with st.chat_message("assistant"):
        slot = st.empty()
        speaker = voice_hub.make_speaker(vcfg, via_voice)
        api_msgs = to_api(sys_prompt, ss.ch_hist)
        t0 = time.perf_counter()
        text, used = run_chain(reg, chain, api_msgs, temp, slot, speaker=speaker)
        elapsed = time.perf_counter() - t0

        st.caption(f"⚡ {used} · {elapsed:.2f}s")
        if citations:
            with st.expander("📚 Retrieved Document Chunks (ChromaDB)", expanded=False):
                for cit in citations:
                    st.markdown(f"- **{cit['source']}** (Chunk {cit['chunk']}): `{cit['text']}`")

    meta = {"citations": citations} if citations else {}
    hui.save_assistant(text, used, meta)
    ss.ch_hist.append({"role": "assistant", "content": text, "used": used, "citations": citations})
    if len(ss.ch_hist) <= 2:
        hui.start_title(reg, chain, user_text)
    st.rerun()


if __name__ == "__main__":
    st.set_page_config(page_title="AI Hub - Conversational Studio", layout="wide", page_icon="⚡")
    render_chat()
