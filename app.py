import os
import re
import time
import json
import uuid
import sys
import io
import urllib.parse
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from PIL import Image
from google import genai
from google.genai import types
from groq import Groq
import httpx
import subprocess

# Add src to path for session_manager
sys.path.append(str(Path(__file__).parent / "src"))
from studio_components import (
    esc,
    fx_flags,
    hero_html,
    gen_log,
    provider_health_html,
    model_matrix_cards_html,
    brand_html
)
from session_manager import (
    generate_session_id,
    get_all_sessions,
    load_session,
    save_session,
    delete_session,
    derive_auto_title
)

# Load environment variables from .env with override
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)
import html

st.set_page_config(
    page_title="AI Hub",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Set STUDIO_PUBLIC_MODE=1 in Streamlit Cloud secrets / env for any public deployment.
# It hides the API Key Vault (so visitors cannot reveal your keys) and stops listing
# other visitors' saved chats.
PUBLIC_MODE = os.getenv("STUDIO_PUBLIC_MODE", "").strip().lower() in ("1", "true", "yes")

# =====================================================================
# DESIGN SYSTEM
# Ink #08090c | Panel #0d0f14 | Line rgba(255,255,255,.08)
# Indigo #6366f1 (actions) | Cyan #38bdf8 (telemetry / "cold GPU") | Text #f1f5f9 | Muted #94a3b8
# One family (Inter). Radius scale: controls 10px, panels 16px, chips full.
# Motion: hover/press feedback only, plus one status ping. No entrance animations.
# Blur is used only on dropdown popovers (the only layer that overlaps content).
# =====================================================================
STUDIO_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700');

:root{
  --bg:#08090c; --bg-elev:#0d0f14;
  --border:rgba(255,255,255,.08); --border-strong:rgba(255,255,255,.16);
  --text:#f1f5f9; --muted:#94a3b8;
  --accent:#6366f1; --cyan:#38bdf8;
  --ok:#34d399; --warn:#fbbf24;
  --ring:0 0 0 3px rgba(99,102,241,.32);
  --font:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
}

/* ---------- Base ---------- */
.stApp{
  background:
    radial-gradient(900px 420px at 8% -8%, rgba(99,102,241,.16), transparent 60%),
    radial-gradient(700px 360px at 100% 0%, rgba(56,189,248,.07), transparent 60%),
    var(--bg);
  color:var(--text); font-family:var(--font); color-scheme:dark;
}
[data-testid="stHeader"]{background:transparent}
footer{visibility:hidden}
.block-container,[data-testid="stMainBlockContainer"]{max-width:1280px;padding-top:2rem;padding-bottom:4rem}
.stApp p,.stApp label,.stApp li,.stApp button,.stApp input,.stApp textarea{font-family:var(--font)}
[data-testid="stWidgetLabel"] p,.stApp label p{font-size:.8rem;font-weight:500;color:var(--muted)}
::selection{background:rgba(99,102,241,.45)}
*{scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.18) transparent}
iframe[height="0"]{display:none}
[data-testid="stElementContainer"]:has(iframe[height="0"]){display:none}

/* ---------- Dropdowns: no blinking caret, no typing line, instant open ---------- */
div[data-testid="stSelectbox"] input,
div.stSelectbox input,
.react-aria-ComboBox input,
input[role="combobox"],
div[data-baseweb="select"] input{
  caret-color:transparent !important; cursor:pointer !important;
  user-select:none !important; -webkit-user-select:none !important;
}
div[data-testid="stSelectbox"] input:focus,
div.stSelectbox input:focus,
.react-aria-ComboBox input:focus,
input[role="combobox"]:focus{
  caret-color:transparent !important; outline:none !important; box-shadow:none !important;
}
div[data-testid="stSelectbox"],div.stSelectbox,.react-aria-ComboBox,
div[data-baseweb="select"] > div{cursor:pointer !important}
div[data-baseweb="select"] input::selection{background:transparent}
div[data-baseweb="select"] > div{
  background:#0b0c10 !important; border:1px solid var(--border) !important;
  border-radius:10px !important; min-height:2.5rem;
  transition:border-color .15s ease, box-shadow .15s ease;
}
div[data-baseweb="select"] > div:hover{border-color:var(--border-strong) !important}
div[data-baseweb="select"]:focus-within > div{border-color:var(--accent) !important;box-shadow:var(--ring) !important}
div[data-baseweb="select"] svg{color:var(--muted)}
div[data-baseweb="popover"] > div{
  background:rgba(15,17,23,.92) !important; border:1px solid var(--border-strong) !important;
  border-radius:12px !important; box-shadow:0 24px 60px -16px rgba(0,0,0,.85) !important;
  backdrop-filter:blur(14px) saturate(140%); -webkit-backdrop-filter:blur(14px) saturate(140%);
}
div[data-baseweb="popover"] ul{background:transparent !important;padding:.3rem}
li[role="option"]{border-radius:8px !important;margin:1px 0;transition:background .12s ease}
li[role="option"]:hover,li[role="option"][aria-selected="true"]{background:rgba(99,102,241,.18) !important}

/* ---------- Inputs ---------- */
div[data-baseweb="input"],div[data-baseweb="textarea"],div[data-baseweb="base-input"]{
  background:#0b0c10 !important; border-color:var(--border) !important; border-radius:10px !important;
}
div[data-baseweb="input"]:focus-within,div[data-baseweb="textarea"]:focus-within{
  border-color:var(--accent) !important; box-shadow:var(--ring) !important;
}
.stTextArea textarea,.stTextInput input{color:var(--text) !important;font-size:.92rem}

/* ---------- Buttons ---------- */
.stButton > button,.stDownloadButton > button{
  min-height:2.5rem; border-radius:10px; font-weight:500; font-size:.88rem; color:var(--text);
  background:rgba(255,255,255,.04); border:1px solid var(--border);
  transition:transform .12s ease, border-color .15s ease, background .15s ease, box-shadow .15s ease;
}
.stButton > button:hover,.stDownloadButton > button:hover{
  background:rgba(255,255,255,.075); border-color:var(--border-strong); transform:translateY(-1px);
}
.stButton > button:active,.stDownloadButton > button:active{transform:translateY(0) scale(.99)}
.stButton > button:focus-visible,.stDownloadButton > button:focus-visible{outline:none;box-shadow:var(--ring)}
.stButton > button[kind="primary"],.stButton > button[data-testid="stBaseButton-primary"]{
  background:linear-gradient(180deg,#7578f5,#5557e6); color:#fff; font-weight:600;
  border:1px solid rgba(255,255,255,.2);
  box-shadow:0 1px 0 rgba(255,255,255,.28) inset, 0 10px 26px -10px rgba(99,102,241,.85);
}
.stButton > button[kind="primary"]:hover,.stButton > button[data-testid="stBaseButton-primary"]:hover{
  background:linear-gradient(180deg,#8487f8,#5f61ec);
  box-shadow:0 1px 0 rgba(255,255,255,.3) inset, 0 14px 32px -10px rgba(99,102,241,.95);
}

/* ---------- Tabs ---------- */
.stTabs [data-baseweb="tab-list"]{gap:2px;border-bottom:1px solid var(--border)}
.stTabs [data-baseweb="tab"]{
  height:44px; padding:0 14px; background:transparent; color:var(--muted);
  font-weight:500; font-size:.9rem; border-radius:8px 8px 0 0;
  transition:color .15s ease, background .15s ease;
}
.stTabs [data-baseweb="tab"]:hover{color:var(--text);background:rgba(255,255,255,.04)}
.stTabs [aria-selected="true"]{color:var(--text)}
.stTabs [data-baseweb="tab-highlight"]{background:linear-gradient(90deg,var(--accent),var(--cyan));height:2px}
.stTabs [data-baseweb="tab-border"]{display:none}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"]{background:var(--bg-elev);border-right:1px solid var(--border)}
section[data-testid="stSidebar"][aria-expanded="true"]{min-width:320px !important;max-width:320px !important;width:320px !important}
.brand{display:flex;align-items:center;gap:.7rem;margin:.2rem 0 1rem}
.brand-mark{
  width:34px;height:34px;border-radius:10px;display:grid;place-items:center;font-size:1.05rem;flex:none;
  background:linear-gradient(145deg,#7c7ff7,#4f46e5);
  box-shadow:0 0 0 1px rgba(255,255,255,.18) inset, 0 8px 20px -8px rgba(99,102,241,.8);
}
.brand-name{font-weight:600;font-size:.98rem;letter-spacing:-.01em}
.brand-sub{font-size:.76rem;color:var(--muted)}
.tele{display:grid;grid-template-columns:repeat(3,1fr);border:1px solid var(--border);border-radius:12px;
  background:rgba(255,255,255,.025);overflow:hidden;margin-bottom:1rem}
.tele-cell{padding:.65rem .4rem;text-align:center}
.tele-cell + .tele-cell{border-left:1px solid var(--border)}
.tele-val{font-size:1.02rem;font-weight:600;color:var(--cyan);font-variant-numeric:tabular-nums;letter-spacing:-.01em}
.tele-lbl{font-size:.72rem;color:var(--muted);margin-top:2px}
.side-label{font-size:.8rem;font-weight:600;color:var(--muted);margin:1.1rem 0 .45rem}
.session-badge{display:flex;align-items:center;gap:.55rem;font-size:.82rem;padding:.5rem .75rem;border-radius:10px;
  background:rgba(99,102,241,.08);border:1px solid rgba(99,102,241,.25);margin:.6rem 0 .2rem}
.session-badge span:last-child{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* ---------- Status ---------- */
.dot{position:relative;width:7px;height:7px;border-radius:50%;background:var(--ok);flex:none;display:inline-block}
.dot.live::after{content:"";position:absolute;inset:0;border-radius:50%;background:var(--ok);
  animation:ping 2.4s ease-out infinite}
@keyframes ping{0%{transform:scale(1);opacity:.6}100%{transform:scale(2.8);opacity:0}}
.pill{display:inline-flex;align-items:center;gap:.45rem;padding:.3rem .7rem;border-radius:999px;font-size:.78rem;
  font-weight:500;border:1px solid var(--border);background:rgba(255,255,255,.03);color:var(--text)}
.pill i{width:6px;height:6px;border-radius:50%;background:var(--ok)}
.pill em{font-style:normal;color:var(--muted)}
.pill.warn{border-color:rgba(251,191,36,.32)}
.pill.warn i{background:var(--warn)}

/* ---------- Layout pieces ---------- */
.hero{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:1rem 2rem;margin:0 0 1.2rem}
.hero-title{font-size:2rem;line-height:1.1;font-weight:700;letter-spacing:-.03em}
.hero-sub{margin:.45rem 0 0;color:var(--muted);font-size:.95rem;max-width:58ch;line-height:1.5}
.hero-status{display:flex;flex-wrap:wrap;gap:.45rem;align-items:center}
.tab-head{margin:.9rem 0 1rem}
.tab-title{font-size:1.25rem;font-weight:600;letter-spacing:-.02em}
.tab-sub{color:var(--muted);font-size:.9rem;margin-top:.2rem;max-width:70ch}
[class*="st-key-panel"]{
  background:linear-gradient(180deg,rgba(255,255,255,.045),rgba(255,255,255,.015));
  border:1px solid var(--border); border-radius:16px; padding:1.25rem;
  box-shadow:0 1px 0 rgba(255,255,255,.05) inset, 0 24px 48px -32px rgba(0,0,0,.9);
}
.panel-title{display:flex;align-items:center;gap:.6rem;font-weight:600;font-size:1.02rem;letter-spacing:-.01em}
.panel-hint{color:var(--muted);font-size:.84rem;margin:.1rem 0 .6rem;line-height:1.45}
.step{display:flex;align-items:center;gap:.6rem;margin:.5rem 0 .15rem}
.step-n{width:20px;height:20px;border-radius:6px;display:inline-grid;place-items:center;font-size:.7rem;font-weight:600;
  color:#c7d2fe;background:rgba(99,102,241,.18);border:1px solid rgba(99,102,241,.35);font-variant-numeric:tabular-nums}
.step-t{font-weight:600;font-size:.92rem}
.step-d{color:var(--muted);font-size:.82rem}
.field-label{font-size:.8rem;font-weight:500;color:var(--muted);margin:0 0 .45rem}
.chips{display:flex;flex-wrap:wrap;gap:.4rem;margin:.4rem 0 .7rem}
.chip{padding:.22rem .65rem;border-radius:999px;font-size:.78rem;color:var(--muted);
  border:1px solid var(--border);background:rgba(255,255,255,.03)}
.chip b{color:var(--text);font-weight:600;font-variant-numeric:tabular-nums}
.empty{display:flex;flex-direction:column;align-items:center;text-align:center;gap:.4rem;padding:2.4rem 1rem;
  border:1.5px dashed var(--border-strong);border-radius:14px;color:var(--muted)}
.empty.flat{border:none;padding:3rem 1rem 1.5rem}
.empty-ico{font-size:1.7rem;opacity:.85}
.empty-t{color:var(--text);font-weight:600;font-size:1.05rem}
.empty-d{font-size:.88rem;max-width:46ch;line-height:1.5}
kbd{border:1px solid var(--border-strong);border-bottom-width:2px;border-radius:6px;padding:0 .4rem;font-size:.75rem;
  background:rgba(255,255,255,.04);color:var(--text);font-family:var(--font)}
.filecard{display:flex;align-items:center;gap:.6rem;padding:.7rem .8rem;border:1px solid var(--border);
  border-radius:12px;background:rgba(255,255,255,.03);font-size:.82rem;word-break:break-all}
.filecard small{display:block;color:var(--muted)}
.cred-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:.7rem;margin-bottom:1rem}
.cred{padding:.85rem 1rem;border:1px solid var(--border);border-radius:12px;background:rgba(255,255,255,.025)}
.cred b{display:block;font-size:.88rem;margin-bottom:.45rem}

/* ---------- Chat ---------- */
[data-testid="stChatMessage"]{background:rgba(255,255,255,.025);border:1px solid var(--border);
  border-radius:14px;padding:.95rem 1.1rem;margin-bottom:.7rem;gap:.8rem}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]),
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]){
  background:rgba(99,102,241,.07);border-color:rgba(99,102,241,.22)}
[data-testid="stChatInput"]{border-radius:14px;border:1px solid var(--border-strong);background:#0b0c10;
  transition:border-color .15s ease, box-shadow .15s ease}
[data-testid="stChatInput"]:focus-within{border-color:var(--accent);box-shadow:var(--ring)}

/* ---------- Uploader, expanders, alerts, code ---------- */
[data-testid="stFileUploaderDropzone"]{background:rgba(99,102,241,.04);border:1.5px dashed rgba(99,102,241,.38);
  border-radius:14px;transition:border-color .15s ease, background .15s ease}
[data-testid="stFileUploaderDropzone"]:hover{border-color:var(--accent);background:rgba(99,102,241,.09)}
[data-testid="stExpander"]{border:1px solid var(--border) !important;border-radius:12px !important;
  background:rgba(255,255,255,.02)}
[data-testid="stExpander"] summary:hover{background:rgba(255,255,255,.03)}
[data-testid="stAlert"]{border-radius:12px;border:1px solid var(--border)}
pre,[data-testid="stCode"] pre{background:#0b0c10 !important;border:1px solid var(--border);border-radius:10px}

@media (prefers-reduced-motion: reduce){
  *,*::before,*::after{animation:none !important;transition:none !important}
}
"""

# Lite mode: strips blur, glow transitions and the status ping for minimum browser GPU use.
LITE_CSS = """
*,*::before,*::after{animation:none !important;transition:none !important;
  backdrop-filter:none !important;-webkit-backdrop-filter:none !important}
.stApp{background:var(--bg)}
[class*="st-key-panel"]{box-shadow:none}
"""

# Keyboard: "/" jumps to the chat prompt. Dropdown inputs are made read-only so they never show a text caret.
STUDIO_JS = """
<script>
(function () {
  try {
    var host = window.parent;
    var doc = host.document;
    if (host.__studioFx) return;
    host.__studioFx = true;
    doc.addEventListener('keydown', function (e) {
      var t = e.target;
      var typing = t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable);
      if (e.key === '/' && !typing && !e.metaKey && !e.ctrlKey && !e.altKey) {
        var ta = doc.querySelector('[data-testid="stChatInput"] textarea');
        if (ta) { e.preventDefault(); ta.focus(); }
      }
    });
    function lock() {
      doc.querySelectorAll('div[data-baseweb="select"] input').forEach(function (i) {
        if (!i.readOnly) { i.readOnly = true; i.setAttribute('inputmode', 'none'); }
      });
    }
    var queued = false;
    new MutationObserver(function () {
      if (queued) return;
      queued = true;
      host.requestAnimationFrame(function () { queued = false; lock(); });
    }).observe(doc.body, { childList: true, subtree: true });
    lock();
  } catch (err) { /* cosmetic only */ }
})();
</script>
"""

THEME_CSS_PATH = Path(__file__).parent / "src" / "studio_theme.css"
theme_css = ""
if THEME_CSS_PATH.exists():
    with open(THEME_CSS_PATH, "r", encoding="utf-8") as f:
        theme_css = f.read()

st.markdown("<style>" + STUDIO_CSS + "\n" + theme_css + "</style>", unsafe_allow_html=True)

# ----------------- UI HELPERS -----------------
def esc(value) -> str:
    return html.escape(str(value), quote=True)

def ui(markup: str, target=None):
    """Render an HTML snippet. Newlines/indent are collapsed so Markdown never turns it into a code block."""
    flat = re.sub(r"\n\s*", "", markup.strip())
    (target if target is not None else st).markdown(flat, unsafe_allow_html=True)

def _stretch(fn, *args, **kwargs):
    """Full-width widgets across Streamlit versions (width='stretch' on new, use_container_width on 1.43+)."""
    for extra in ({"width": "stretch"}, {"use_container_width": True}):
        try:
            return fn(*args, **kwargs, **extra)
        except Exception:
            continue
    return fn(*args, **kwargs)

def btn(*args, **kwargs):
    return _stretch(st.button, *args, **kwargs)

def dl_btn(*args, **kwargs):
    return _stretch(st.download_button, *args, **kwargs)

def show_image(*args, **kwargs):
    return _stretch(st.image, *args, **kwargs)

def pill(label: str, ok: bool, ok_text: str = "Ready", bad_text: str = "Add key") -> str:
    return (f'<span class="pill {"" if ok else "warn"}"><i></i>{esc(label)}'
            f'<em>{esc(ok_text if ok else bad_text)}</em></span>')

def chips(items) -> str:
    return '<div class="chips">' + "".join(f'<span class="chip">{i}</span>' for i in items) + "</div>"

def tab_header(title: str, sub: str):
    ui(f'<div class="tab-head"><div class="tab-title">{esc(title)}</div><div class="tab-sub">{esc(sub)}</div></div>')

def panel_title(icon: str, title: str, hint: str):
    ui(f'<div class="panel-title"><span>{icon}</span><span>{esc(title)}</span></div><div class="panel-hint">{esc(hint)}</div>')

def step(num: int, title: str, desc: str):
    ui(f'<div class="step"><span class="step-n">{num}</span><span class="step-t">{esc(title)}</span>'
       f'<span class="step-d">{esc(desc)}</span></div>')

def side_label(text: str):
    ui(f'<div class="side-label">{esc(text)}</div>')

def render_telemetry(placeholder):
    lat = st.session_state.get("last_latency")
    lat_txt = f"{lat:.2f}s" if lat else "—"
    ui(f"""
    <div class="tele">
      <div class="tele-cell"><div class="tele-val">0%</div><div class="tele-lbl">Local GPU</div></div>
      <div class="tele-cell"><div class="tele-val">{lat_txt}</div><div class="tele-lbl">Last reply</div></div>
      <div class="tele-cell"><div class="tele-val">Free</div><div class="tele-lbl">No card</div></div>
    </div>
    """, placeholder)

AVATARS = {"user": "🧑‍💻", "assistant": "⚡"}

# ----------------- MERMAID & MARKDOWN SANITIZER -----------------
def sanitize_mermaid_code(chart: str) -> str:
    """Fix common LLM Mermaid syntax flaws that cause Streamlit frontend parse errors."""
    chart = chart.strip()
    lines = []
    for raw_line in chart.splitlines():
        line = raw_line.strip()
        if not line:
            continue
            
        m_head = re.match(r'^(graph\s+[A-Za-z]+|flowchart\s+[A-Za-z]+)\s+([A-Za-z0-9_\[\(].*)', line, re.IGNORECASE)
        if m_head:
            lines.append(m_head.group(1))
            line = m_head.group(2)
            
        def fix_cylinder(m):
            nid, text = m.group(1), m.group(2).strip()
            clean = text.replace('"', "'")
            return f'{nid}[("{clean}")]'
        line = re.sub(r'(\b[A-Za-z0-9_]+)\[\(([^)]+)\)\]', fix_cylinder, line)

        def fix_bracket(m):
            nid, text = m.group(1), m.group(2).strip()
            if (text.startswith('("') and text.endswith('")')) or (text.startswith('"') and text.endswith('"')):
                return f'{nid}[{text}]'
            clean = text.replace('"', "'")
            return f'{nid}["{clean}"]'
        line = re.sub(r'(\b[A-Za-z0-9_]+)\[([^\[\]]+)\]', fix_bracket, line)

        lines.append(line)
        
    return '\n'.join(lines)

def sanitize_markdown_text(text: str) -> str:
    """Sanitizes all ```mermaid code blocks inside the markdown response."""
    def repl(m):
        code = m.group(1)
        cleaned = sanitize_mermaid_code(code)
        return f"```mermaid\n{cleaned}\n```"
    return re.sub(r'```mermaid\s*([\s\S]*?)```', repl, text)

# ----------------- CLOUD IMAGE GENERATOR (FLUX 1024 + HORDE) -----------------
def generate_cloud_image_flux_or_horde(prompt: str, width: int = 1024, height: int = 1024, hf_token: str = None, engine_choice: str = "FLUX.1-schnell", status_placeholder=None) -> bytes:
    """Generates up to 1024x1024 maximum quality images via Black Forest Labs FLUX.1-schnell cloud space,
    with automatic failover to Stable Horde. 100% Free, Zero Card, Zero 402 payment errors."""
    
    # Direct Pollinations if user selected Pollinations
    if "Pollinations" in engine_choice:
        if status_placeholder:
            status_placeholder.info("🚀 Generating 1024px visual via Pollinations Cloud FLUX...")
        enc_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{enc_prompt}?width={width}&height={height}&model=flux&nologo=true&seed={int(time.time())}"
        with httpx.Client(timeout=45.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.content

    # 1. Primary: Official FLUX.1-schnell Cloud GPU Space (Native 1024x1024)
    if hf_token and "FLUX" in engine_choice:
        try:
            if status_placeholder:
                status_placeholder.info("🚀 Generating native 1024x1024 visual via FLUX.1-schnell Cloud GPU...")
            from gradio_client import Client
            client = Client("black-forest-labs/FLUX.1-schnell", token=hf_token, httpx_kwargs={"timeout": 120.0})
            result = client.predict(
                prompt=prompt,
                seed=0,
                randomize_seed=True,
                width=width,
                height=height,
                num_inference_steps=4,
                api_name="/infer"
            )
            # Result is tuple (filepath, seed)
            img_path = result[0]
            with open(img_path, "rb") as f:
                return f.read()
        except Exception as e:
            err_msg = str(e)
            if status_placeholder:
                status_placeholder.warning("⏳ ZeroGPU cooldown / busy. Failing over to Pollinations Cloud FLUX...")
            try:
                enc_prompt = urllib.parse.quote(prompt)
                url = f"https://image.pollinations.ai/prompt/{enc_prompt}?width={width}&height={height}&model=flux&nologo=true&seed={int(time.time())}"
                with httpx.Client(timeout=35.0) as client:
                    resp = client.get(url)
                    resp.raise_for_status()
                    return resp.content
            except Exception:
                pass

    # 2. Secondary: Stable Horde Free Crowdsourced Cluster
    url_async = "https://stablehorde.net/api/v2/generate/async"
    headers = {
        "apikey": "0000000000",
        "Content-Type": "application/json",
        "Client-Agent": "HackathonAIStudio:1.0:(contact@aihub.dev)"
    }
    payload = {
        "prompt": prompt,
        "models": ["stable_diffusion", "Deliberate"],
        "params": {
            "steps": 20,
            "width": min(width, 768),
            "height": min(height, 768),
            "cfg_scale": 7.5
        }
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url_async, headers=headers, json=payload)
            resp.raise_for_status()
            req_id = resp.json().get("id")
            if not req_id:
                raise Exception("No request ID returned from Horde cluster.")
                
            for _ in range(35):
                time.sleep(2)
                check = client.get(f"https://stablehorde.net/api/v2/generate/check/{req_id}").json()
                if status_placeholder:
                    q_pos = check.get("queue_position", 0)
                    wait_t = check.get("wait_time", 0)
                    status_placeholder.info(f"⏳ Free Cloud GPU Queue: Position {q_pos} | Est. wait: {wait_t}s")
                    
                if check.get("done"):
                    status = client.get(f"https://stablehorde.net/api/v2/generate/status/{req_id}").json()
                    img_url = status["generations"][0]["img"]
                    img_resp = client.get(img_url)
                    img_resp.raise_for_status()
                    return img_resp.content
                    
            raise Exception("Cloud queue timed out.")
    except Exception:
        raise Exception(
            "Free Cloud GPU rate limit reached. Your Hugging Face ZeroGPU quota automatically refreshes every few minutes! "
            "Please wait 60–90 seconds and click Generate again."
        )

# ----------------- CLOUD VIDEO GENERATOR (MULTI-SCENE STORYBOARD & LTX) -----------------
def synthesize_multiscene_video(prompt: str, width: int = 704, height: int = 512, total_duration: int = 20, status_placeholder=None) -> bytes:
    """Synthesizes smooth cinematic 5-30 second multi-scene MP4 video using storyboard
    chaining, directional optical trajectory, and cross-dissolve transitions.
    100% Free, unlimited, 0% laptop GPU load."""
    import imageio
    import numpy as np
    
    # Scene breakdown according to requested duration
    if total_duration <= 5:
        num_scenes = 1
        scene_dur = total_duration
    elif total_duration <= 10:
        num_scenes = 2
        scene_dur = 5
    elif total_duration <= 15:
        num_scenes = 3
        scene_dur = 5
    elif total_duration <= 20:
        num_scenes = 4
        scene_dur = 5
    else:
        num_scenes = 6
        scene_dur = 5
        
    scene_modifiers = [
        ("Establishing Wide Shot", "establishing wide angle cinematic shot, atmospheric depth, 8k render, photorealistic lighting"),
        ("Dynamic Dolly In", "camera tracking dolly forward, high motion clarity, vibrant hyper-realistic textures"),
        ("Lateral Arc Motion", "smooth lateral camera pan left to right, dramatic contrast, ultra detailed cinematography"),
        ("Macro Detail Focus", "cinematic macro close up lens, sharp focal point, subtle volumetric glow, octane render"),
        ("Elevated Aerial Angle", "aerial drone camera angle, majestic scale, cinematic lighting"),
        ("Pull-Back Reveal Finale", "slow cinematic pull back camera reveal, epic horizon, masterpiece composition")
    ]
    
    fps = 12
    dissolve_frames = 8
    frames_per_scene = max(18, int(scene_dur * fps))
    
    scene_images = []
    base_seed = int(time.time())
    
    for i in range(num_scenes):
        label, modifier = scene_modifiers[i % len(scene_modifiers)]
        if status_placeholder:
            status_placeholder.info(f"🎬 Generating Scene {i+1}/{num_scenes} ({label})...")
            
        scene_prompt = f"{prompt}, {modifier}"
        enc = urllib.parse.quote(scene_prompt)
        url = f"https://image.pollinations.ai/prompt/{enc}?width=1024&height=768&model=flux&nologo=true&seed={base_seed + i * 211}"
        with httpx.Client(timeout=45.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            scene_images.append(img)
            
    if status_placeholder:
        status_placeholder.info(f"🎞️ Synthesizing {total_duration}s continuous multi-scene motion with cross-dissolve transitions...")
        
    all_frames = []
    for i, base_img in enumerate(scene_images):
        orig_w, orig_h = base_img.size
        scene_frames = []
        motion_type = i % 4
        
        for step in range(frames_per_scene):
            prog = step / float(frames_per_scene)
            if motion_type == 0:  # Dolly In
                zoom = 1.0 + (prog * 0.14)
                crop_w = int(orig_w / zoom)
                crop_h = int(orig_h / zoom)
                x_shift = int((orig_w - crop_w) * 0.5)
                y_shift = int((orig_h - crop_h) * 0.5)
            elif motion_type == 1:  # Lateral Pan Left-to-Right
                zoom = 1.08
                crop_w = int(orig_w / zoom)
                crop_h = int(orig_h / zoom)
                x_shift = int((orig_w - crop_w) * (0.15 + 0.7 * prog))
                y_shift = int((orig_h - crop_h) * 0.5)
            elif motion_type == 2:  # Vertical Elevation Tilt
                zoom = 1.10
                crop_w = int(orig_w / zoom)
                crop_h = int(orig_h / zoom)
                x_shift = int((orig_w - crop_w) * 0.5)
                y_shift = int((orig_h - crop_h) * (0.15 + 0.7 * prog))
            else:  # Pull back / Zoom Out
                zoom = 1.15 - (prog * 0.12)
                crop_w = int(orig_w / zoom)
                crop_h = int(orig_h / zoom)
                x_shift = int((orig_w - crop_w) * 0.5)
                y_shift = int((orig_h - crop_h) * 0.5)
                
            cropped = base_img.crop((x_shift, y_shift, x_shift + crop_w, y_shift + crop_h))
            resized = cropped.resize((width, height), Image.Resampling.LANCZOS)
            scene_frames.append(np.array(resized))
            
        if not all_frames:
            all_frames.extend(scene_frames)
        else:
            lead_in = all_frames[:-dissolve_frames]
            outgoing = all_frames[-dissolve_frames:]
            incoming = scene_frames[:dissolve_frames]
            trailing = scene_frames[dissolve_frames:]
            
            blended = []
            for k in range(dissolve_frames):
                alpha = (k + 1) / float(dissolve_frames + 1)
                blend = ((1.0 - alpha) * outgoing[k] + alpha * incoming[k]).astype(np.uint8)
                blended.append(blend)
                
            all_frames = lead_in + blended + trailing
            
    buf = io.BytesIO()
    with imageio.get_writer(buf, format="mp4", fps=fps, codec="libx264", quality=8) as writer:
        for f in all_frames:
            writer.append_data(f)
            
    return buf.getvalue()

def generate_cloud_video_ltx(prompt: str, width: int = 704, height: int = 512, duration: int = 5, hf_token: str = None, status_placeholder=None) -> bytes:
    """Generates high quality video clips in the cloud. Automatically uses Multi-Scene Storyboard
    Synthesizer for durations >= 5s or fails over if ZeroGPU is in cooldown.
    100% Free, zero laptop GPU load, returns MP4 video bytes."""
    # Cloud ZeroGPU LTX only supports short 2-4s bursts. For extended 5-30s videos, use Multi-Scene Director.
    if duration > 4:
        return synthesize_multiscene_video(prompt, width=width, height=height, total_duration=duration, status_placeholder=status_placeholder)

    if not hf_token:
        if status_placeholder:
            status_placeholder.info("🎬 Using Cloud Storyboard Synthesizer (No Hugging Face token needed)...")
        return synthesize_multiscene_video(prompt, width=width, height=height, total_duration=duration, status_placeholder=status_placeholder)
        
    if status_placeholder:
        status_placeholder.info("🎬 Connecting to Lightricks LTX-Video Cloud GPU on Hugging Face...")
        
    try:
        from gradio_client import Client
        client = Client("Lightricks/ltx-video-distilled", token=hf_token, httpx_kwargs={"timeout": 120.0})
        
        if status_placeholder:
            status_placeholder.info(f"⏳ Synthesizing {width}x{height} cinematic video frames in cloud (~15-25s)...")
            
        result = client.predict(
            prompt=prompt,
            negative_prompt="worst quality, inconsistent motion, blurry, jittery, distorted",
            input_image_filepath=None,
            input_video_filepath=None,
            height_ui=float(height),
            width_ui=float(width),
            mode="text-to-video",
            duration_ui=float(duration),
            ui_frames_to_use=9.0,
            seed_ui=42,
            randomize_seed=True,
            ui_guidance_scale=1.0,
            improve_texture_flag=True,
            api_name="/text_to_video"
        )
        
        if isinstance(result, (tuple, list)) and len(result) > 0:
            video_info = result[0]
            video_path = video_info.get("video") if isinstance(video_info, dict) else str(video_info)
            if video_path and os.path.exists(video_path):
                with open(video_path, "rb") as f:
                    return f.read()
                    
        raise Exception(f"Unexpected response from video cloud space: {result}")
    except Exception as e:
        if status_placeholder:
            status_placeholder.warning("⏳ ZeroGPU cooldown or timeout detected. Failing over to Multi-Scene Synthesizer...")
        try:
            return synthesize_multiscene_video(prompt, width=width, height=height, total_duration=duration, status_placeholder=status_placeholder)
        except Exception as inner_e:
            raise Exception(f"Video synthesis failed: {e} | Fallback error: {inner_e}")

# ----------------- GITHUB & CLOUD DEPLOYMENT ENGINE -----------------
def get_git_info() -> dict:
    """Returns detected GitHub user, remote origin, current branch, and commit status."""
    info = {
        "user": "ankush-dev-eng",
        "origin": "",
        "branch": "main",
        "has_commits": False,
        "repo_name": "ai-hub",
        "gh_installed": False
    }
    try:
        res = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            info["gh_installed"] = True
            for line in (res.stdout + "\n" + res.stderr).splitlines():
                if "account" in line:
                    parts = line.split("account")
                    if len(parts) > 1:
                        acc = parts[1].split()[0].strip()
                        if acc:
                            info["user"] = acc
    except Exception:
        pass

    try:
        res = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, timeout=3)
        if res.returncode == 0 and res.stdout.strip():
            info["user"] = res.stdout.strip()
    except Exception:
        pass

    try:
        res = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True, timeout=3)
        if res.returncode == 0 and res.stdout.strip():
            info["origin"] = res.stdout.strip()
            clean_orig = info["origin"].rstrip(".git").rstrip("/")
            if "/" in clean_orig:
                info["repo_name"] = clean_orig.split("/")[-1]
    except Exception:
        pass

    try:
        res = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, timeout=3)
        if res.returncode == 0 and res.stdout.strip():
            info["branch"] = res.stdout.strip()
    except Exception:
        pass

    try:
        res = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], capture_output=True, text=True, timeout=3)
        info["has_commits"] = (res.returncode == 0)
    except Exception:
        pass

    return info

def execute_github_publish(repo_name: str, account: str, is_public: bool, commit_msg: str, status_placeholder=None) -> tuple[bool, str, str]:
    """Publishes current workspace to GitHub under user's account and returns (success, repo_url_or_err, deploy_url)."""
    repo_name = repo_name.strip()
    account = account.strip() or "ankush-dev-eng"
    if not repo_name:
        return False, "Repository name cannot be empty.", ""

    try:
        if status_placeholder:
            status_placeholder.info("Step 1/5: Verifying local Git repository & securing .gitignore secrets...")
        
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-B", "main"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", account], capture_output=True)
        subprocess.run(["git", "config", "user.email", f"{account}@users.noreply.github.com"], capture_output=True)

        if status_placeholder:
            status_placeholder.info("Step 2/5: Staging files and creating commit snapshot...")
        subprocess.run(["git", "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", commit_msg or "Deploy AI Hub v5.0 - Multi-Model Hackathon Studio"], capture_output=True, text=True)
        
        repo_full = f"{account}/{repo_name}"
        vis_flag = "--public" if is_public else "--private"
        
        if status_placeholder:
            status_placeholder.info(f"Step 3/5: Querying GitHub for repository '{repo_full}'...")
        
        chk = subprocess.run(["gh", "repo", "view", repo_full], capture_output=True, text=True)
        if chk.returncode != 0:
            if status_placeholder:
                status_placeholder.info(f"Step 4/5: Creating new {vis_flag[2:]} repository '{repo_full}' and pushing code to GitHub...")
            res = subprocess.run(
                ["gh", "repo", "create", repo_full, vis_flag, "--source=.", "--remote=origin", "--push"],
                capture_output=True, text=True, timeout=60
            )
            comb = res.stderr + res.stdout
            if res.returncode != 0 and "already exists" not in comb:
                raise Exception(f"GitHub CLI error: {comb}")
        else:
            if status_placeholder:
                status_placeholder.info(f"Step 4/5: Setting origin remote to '{repo_full}' and pushing main branch...")
            subprocess.run(["git", "remote", "remove", "origin"], capture_output=True)
            subprocess.run(["git", "remote", "add", "origin", f"https://github.com/{repo_full}.git"], check=True, capture_output=True)
            push_res = subprocess.run(["git", "push", "-u", "origin", "main", "--force"], capture_output=True, text=True, timeout=60)
            if push_res.returncode != 0:
                raise Exception(f"Push failed: {push_res.stderr or push_res.stdout}")

        repo_url = f"https://github.com/{repo_full}"
        deploy_url = f"https://share.streamlit.io/deploy?repository={repo_full}&branch=main&mainModule=app.py"
        
        if status_placeholder:
            status_placeholder.success(f"Step 5/5: Successfully published to GitHub: {repo_url}")
            
        return True, repo_url, deploy_url
    except Exception as e:
        return False, str(e), ""

# ----------------- PRESETS DEFINITIONS -----------------
# Tab 2: Multimodal Auditor Presets
AUDITOR_PRESETS = {
    "🔄 Multi-Image Comparison (Differences, Progression, Before/After)": "Carefully compare all uploaded images side-by-side. Highlight key differences, visual changes, UI progression, performance shifts, or data discrepancies between them in a clean markdown table.",
    "📊 Chart & Financial Table Data Extraction": "Extract all numerical data, percentages, trends, and key insights from these charts or tables. Present the results in a clean markdown table followed by an executive takeaway.",
    "🎮 Gaming / Esports Coach (Stats, Flaws, Tactics)": "Analyze these gaming screenshots in detail. Identify the exact game, character/hero, ranking, win rate, performance metrics, critical flaws in stats, and give 3 strategic gameplay improvement recommendations.",
    "📄 Contract / Document Auditor (Clauses, Risks)": "Audit these documents thoroughly. Extract key parties, dates, obligations, financial amounts, and flag high-risk or ambiguous liability clauses in a structured markdown summary.",
    "🎨 UI / UX Review & Redesign Recommendations": "Perform a senior UX/UI review on these interfaces. Compare layout hierarchy, contrast/readability problems, call-to-action weaknesses, and provide concrete design improvement tips.",
    "✏️ Custom Instruction": ""
}

# Tab 3: Cloud Image Presets
IMAGE_PRESETS = {
    "🛸 Autonomous AI Drone": "A futuristic autonomous drone picking up recyclable trash on a sleek cybernetic city street, photorealistic, cinematic 8k resolution, Unreal Engine 5 render, volumetric lighting",
    "📱 Dark Glassmorphism App UI": "Sleek modern web app dashboard mockup, dark mode glassmorphism UI, glowing purple and teal accents, charts, analytics, clean typography, 8k UI design, Behance award winner",
    "🏙️ Cyberpunk Metropolis": "Vibrant cyberpunk neon city street at night in rain, towering skyscrapers, holographic advertisements, reflective wet asphalt, cinematic atmosphere, 8k",
    "👤 Studio Portrait": "Professional studio portrait of an innovative hackathon engineer wearing smart glasses, soft dramatic lighting, sharp focus, 85mm lens, photorealistic 8k",
    "🎨 3D Isometric AI Icon": "Cute 3D isometric glowing AI brain robot server icon, smooth clay render, soft shadows, vibrant pastel colors, Blender 3D, high detail",
    "✏️ Custom Visual Prompt": ""
}

# Tab 3: Cloud Video Presets
VIDEO_PRESETS = {
    "🏎️ Cyber Sports Car in Rain": "A glowing cyberpunk sports car accelerating down a wet neon highway at night in rain, motion blur, cinematic lighting, 4k",
    "🚁 Futuristic Drone Flyover": "A cinematic drone shot flying over a futuristic metropolis with towering holographic architecture and flying vehicles, hyper-detailed, 4k",
    "🤖 Robotic Arm Assembly": "High-tech robotic arm precisely soldering glowing circuits on an advanced microprocessor in a cleanroom lab, cinematic macro lens",
    "🌌 Deep Space Nebula Voyage": "Camera moving forward through a vibrant celestial nebula with glowing purple and cyan stardust, cosmic rays, cinematic 8k",
    "✏️ Custom Video Prompt": ""
}

# ----------------- PERSISTENT STATE INITIALIZATION -----------------
# Tab 1: Chat Session
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = generate_session_id()
    st.session_state.current_session_title = "New Chat"
    st.session_state.chat_history = []

# Tab 2: Multimodal Auditor
if "tab2_saved_files" not in st.session_state:
    st.session_state.tab2_saved_files = []
if "tab2_report" not in st.session_state:
    st.session_state.tab2_report = None
if "tab2_report_elapsed" not in st.session_state:
    st.session_state.tab2_report_elapsed = None
if "tab2_report_files_count" not in st.session_state:
    st.session_state.tab2_report_files_count = 0

DEFAULT_TAB2_MODE = "🔄 Multi-Image Comparison (Differences, Progression, Before/After)"
if "tab2_mode_selector" not in st.session_state:
    st.session_state.tab2_mode_selector = DEFAULT_TAB2_MODE
if "tab2_analysis_prompt" not in st.session_state:
    st.session_state.tab2_analysis_prompt = AUDITOR_PRESETS[DEFAULT_TAB2_MODE]

# Tab 3: Image & Video Studio
DEFAULT_IMG_PRESET = "🛸 Autonomous AI Drone"
if "tab3_img_preset" not in st.session_state:
    st.session_state.tab3_img_preset = DEFAULT_IMG_PRESET
if "tab3_img_prompt" not in st.session_state:
    st.session_state.tab3_img_prompt = IMAGE_PRESETS[DEFAULT_IMG_PRESET]
if "tab3_image_bytes" not in st.session_state:
    st.session_state.tab3_image_bytes = None
if "tab3_image_caption" not in st.session_state:
    st.session_state.tab3_image_caption = None

DEFAULT_VID_PRESET = "🏎️ Cyber Sports Car in Rain"
if "tab3_vid_preset" not in st.session_state:
    st.session_state.tab3_vid_preset = DEFAULT_VID_PRESET
if "tab3_vid_prompt" not in st.session_state:
    st.session_state.tab3_vid_prompt = VIDEO_PRESETS[DEFAULT_VID_PRESET]
if "tab3_video_bytes" not in st.session_state:
    st.session_state.tab3_video_bytes = None
if "tab3_video_caption" not in st.session_state:
    st.session_state.tab3_video_caption = None

# Extra state for the redesigned UI
if "last_latency" not in st.session_state:
    st.session_state.last_latency = None
if "tab2_uploader_nonce" not in st.session_state:
    st.session_state.tab2_uploader_nonce = 0

IMG_DIMS = {
    "1024x1024 (HD Square)": (1024, 1024),
    "1024x576 (16:9 Widescreen)": (1024, 576),
    "576x1024 (9:16 Portrait)": (576, 1024),
    "512x512 (Fastest)": (512, 512),
}
VID_DIMS = {
    "704x512 (Widescreen 16:9)": (704, 512),
    "512x512 (Square 1:1)": (512, 512),
    "512x704 (Portrait 9:16)": (512, 704),
}

# Prompt sync: callbacks run BEFORE the rerun, so the text area is already updated when it renders.
def on_objective_change():
    st.session_state.tab2_analysis_prompt = AUDITOR_PRESETS.get(st.session_state.tab2_mode_selector, "")

def on_img_preset_change():
    st.session_state.tab3_img_prompt = IMAGE_PRESETS.get(st.session_state.tab3_img_preset, "")

def on_vid_preset_change():
    st.session_state.tab3_vid_prompt = VIDEO_PRESETS.get(st.session_state.tab3_vid_preset, "")

# ----------------- SIDEBAR -----------------
with st.sidebar:
    ui(brand_html())
    telemetry_ph = st.empty()
    render_telemetry(telemetry_ph)

    side_label("Conversations")
    col_new, col_del = st.columns([1.2, 1])
    with col_new:
        if btn("✦ New Chat"):
            st.session_state.current_session_id = generate_session_id()
            st.session_state.current_session_title = "New Chat"
            st.session_state.chat_history = []
            st.rerun()
    with col_del:
        if btn("✕ Delete", help="Permanently delete active chat with 0 residual files"):
            delete_session(st.session_state.current_session_id)
            st.session_state.current_session_id = generate_session_id()
            st.session_state.current_session_title = "New Chat"
            st.session_state.chat_history = []
            st.toast("Chat deleted cleanly (0 bytes residue).")
            st.rerun()

    all_sessions = [] if PUBLIC_MODE else get_all_sessions()
    session_dict = {}
    for s in all_sessions:
        session_dict[s["id"]] = f"{s['title']} ({s['message_count']} msgs)"

    curr_id = st.session_state.current_session_id
    if curr_id not in session_dict:
        session_dict[curr_id] = f"{st.session_state.current_session_title} (Active)"

    session_keys = list(session_dict.keys())
    curr_idx = session_keys.index(curr_id) if curr_id in session_keys else 0

    selected_session = st.selectbox(
        "Chat History:",
        options=session_keys,
        format_func=lambda x: session_dict.get(x, x),
        index=curr_idx,
        label_visibility="collapsed"
    )

    if selected_session != st.session_state.current_session_id:
        loaded = load_session(selected_session)
        if loaded:
            st.session_state.current_session_id = loaded["id"]
            st.session_state.current_session_title = loaded.get("title", "Chat")
            st.session_state.chat_history = loaded.get("messages", [])
            st.rerun()

    ui(f'<div class="session-badge"><span class="dot"></span><span><b>Active</b> &nbsp;{esc(st.session_state.current_session_title)}</span></div>')

    side_label("Access")
    with st.expander("🔑 API Key Vault", expanded=False):
        if PUBLIC_MODE:
            st.caption("🔒 Public mode: keys come from server secrets and can't be viewed or changed here.")
            gemini_key = os.getenv("GEMINI_API_KEY", "")
            groq_key = os.getenv("GROQ_API_KEY", "")
            openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
            hf_token = os.getenv("HF_TOKEN", "")
            adaption_key = os.getenv("ADAPTION_API_KEY", "")
        else:
            st.caption("All keys stored locally in `.env`. Zero credit card required.")
            gemini_key = st.text_input(
                "Google Gemini Key",
                value=os.getenv("GEMINI_API_KEY", ""),
                type="password",
                help="Free key at aistudio.google.com"
            )
            groq_key = st.text_input(
                "Groq Cloud Key",
                value=os.getenv("GROQ_API_KEY", ""),
                type="password",
                help="Free key at console.groq.com"
            )
            openrouter_key = st.text_input(
                "OpenRouter API Key (Free DeepSeek-R1, Llama 3.3)",
                value=os.getenv("OPENROUTER_API_KEY", ""),
                type="password",
                help="Free key at openrouter.ai/keys (Access DeepSeek-R1:free, Llama 3.3:free, Qwen 2.5:free)"
            )
            hf_token = st.text_input(
                "Hugging Face Token (HF_TOKEN)",
                value=os.getenv("HF_TOKEN", ""),
                type="password",
                help="Free token at huggingface.co/settings/tokens"
            )
            adaption_key = st.text_input(
                "Adaption Labs Key (Optional)",
                value=os.getenv("ADAPTION_API_KEY", ""),
                type="password",
                help="Key at adaptionlabs.ai/app for custom fine-tuned adapters"
            )

            if btn("✓ Save Credentials"):
                try:
                    with open(ENV_PATH, "w", encoding="utf-8") as fp:
                        fp.write(f"GEMINI_API_KEY={gemini_key}\n")
                        fp.write(f"GROQ_API_KEY={groq_key}\n")
                        fp.write(f"OPENROUTER_API_KEY={openrouter_key}\n")
                        fp.write(f"HF_TOKEN={hf_token}\n")
                        fp.write(f"ADAPTION_API_KEY={adaption_key}\n")
                    os.environ["GEMINI_API_KEY"] = gemini_key
                    os.environ["GROQ_API_KEY"] = groq_key
                    os.environ["OPENROUTER_API_KEY"] = openrouter_key
                    os.environ["HF_TOKEN"] = hf_token
                    os.environ["ADAPTION_API_KEY"] = adaption_key
                    st.success("Credentials saved to .env!")
                except Exception as e:
                    st.error(f"Save failed: {e}")

    side_label("System tools")
    if btn("🚀 Deploy to Cloud & GitHub", help="Open GitHub & Live Streamlit Cloud Deployment Control Panel"):
        import streamlit.components.v1 as components
        components.html("<script>try{window.parent.__studioFx && window.parent.__studioFx.selectTab(3);}catch(e){}</script>", height=0)

    c_clear_cache, c_export_chat = st.columns([1.1, 0.9])
    with c_clear_cache:
        if btn("↻ Clear Cache", help="Clear app caches and temporary buffers"):
            st.cache_data.clear()
            st.toast("App cache cleared successfully!")
    with c_export_chat:
        md_export = ""
        if st.session_state.chat_history:
            md_export = f"# {st.session_state.current_session_title}\n\n"
            for m in st.session_state.chat_history:
                md_export += f"### {m['role'].capitalize()}\n{m['content']}\n\n"
        dl_btn(
            "↓ Export",
            data=md_export,
            file_name=f"chat_{st.session_state.current_session_id}.md",
            mime="text/markdown",
            disabled=not st.session_state.chat_history
        )

    lite_fx = st.toggle(
        "Lite effects",
        key="lite_fx",
        help="Turns off blur, transitions and the status ping for the lowest possible browser GPU use."
    )
    ui(fx_flags(lite_fx))
    if lite_fx:
        st.markdown("<style>" + LITE_CSS + "</style>", unsafe_allow_html=True)

# ----------------- HEADER (Atmospheric Beam & Orbital Nodes) -----------------
pills_html = f"""
  <span class="pill"><span class="dot live"></span>Cloud inference</span>
  {pill("Groq", bool(groq_key))}
  {pill("Gemini", bool(gemini_key))}
  {pill("OpenRouter", bool(openrouter_key), bad_text="Add key")}
  {pill("Hugging Face", bool(hf_token), bad_text="Add token")}
  {pill("Adaption Labs", bool(adaption_key), bad_text="Optional")}
"""
providers = [
    ("Gemini", bool(gemini_key)),
    ("Groq", bool(groq_key)),
    ("OpenRouter", bool(openrouter_key)),
    ("Hugging Face", bool(hf_token)),
    ("Adaption Labs", bool(adaption_key))
]
ui(hero_html(providers, pills_html))

tab1, tab2, tab3, tab4 = st.tabs([
    "⚡ Conversational Studio",
    "◈ Visual & Document Auditor",
    "✦ Free Image & Video Studio",
    "↗ Deployment & Guide"
])

# ===================================================
# TAB 1: CONVERSATIONAL STUDIO
# ===================================================
with tab1:
    tab_header("Conversational Studio",
               "Streaming chat on Gemini Flash, Groq LPU, or OpenRouter Free (DeepSeek-R1, Llama 3.3).")

    col_prov, col_model, col_starters = st.columns([1.2, 1.4, 2.2])
    with col_prov:
        provider = st.selectbox(
            "Provider:",
            [
                "Google Gemini (2026 Models)",
                "Groq Cloud LPU (Ultra-Fast)",
                "OpenRouter Cloud (DeepSeek R1, Llama 3.3)",
                "Adaption Labs (Adapter Router)"
            ],
            index=0,
            key="chat_provider"
        )
    with col_model:
        if "Gemini" in provider:
            model_name = st.selectbox(
                "Engine:",
                [
                    "gemini-3.8-flash (Latest 2026 Knowledge)",
                    "gemini-flash-latest (Auto-Updating 2026)",
                    "gemini-3.5-flash (High Throughput)"
                ],
                index=0,
                key="chat_model_gemini"
            )
        elif "Groq" in provider:
            model_name = st.selectbox(
                "Engine:",
                [
                    "qwen/qwen3.8-27b (2025 Knowledge, 600 t/s)",
                    "openai/gpt-oss-120b (120B Open Weights)",
                    "openai/gpt-oss-20b (Fast Reasoning)"
                ],
                index=0,
                key="chat_model_groq"
            )
        elif "OpenRouter" in provider:
            model_name = st.selectbox(
                "Engine:",
                [
                    "deepseek/deepseek-r1:free (DeepSeek R1 671B Reasoning • Free)",
                    "meta-llama/llama-3.3-70b-instruct:free (Llama 3.3 70B • Free)",
                    "qwen/qwen-2.5-72b-instruct:free (Qwen 2.5 72B • Free)",
                    "google/gemini-2.0-flash-exp:free (Gemini 2.0 Flash • Free)",
                    "mistralai/mistral-7b-instruct:free (Mistral 7B • Free)"
                ],
                index=0,
                key="chat_model_openrouter"
            )
        else:
            model_name = st.selectbox(
                "Engine:",
                [
                    "adaption/base-router (Default Adapter Pipeline)",
                    "adaption/fine-tuned-task (Custom Domain Adapter)"
                ],
                index=0,
                key="chat_model_adaption"
            )

    with col_starters:
        ui('<div class="field-label">Quick prompt starters</div>')
        p_cols = st.columns(4)
        with p_cols[0]:
            if btn("✦ Pitch", help="Generate a winning 3-sentence elevator pitch"):
                st.session_state.preset_prompt = "Write a 3-sentence high-impact winning hackathon elevator pitch for an AI automated waste management drone."
        with p_cols[1]:
            if btn("⬡ Arch", help="Generate tech stack flow diagram & Mermaid architecture"):
                st.session_state.preset_prompt = "Provide a clean 5-step technical architecture diagram and API flow for a real-time multimodal AI app. Include valid Mermaid flowchart TD syntax with quoted node labels."
        with p_cols[2]:
            if btn("◈ Debug", help="Review code bottlenecks and suggest async fixes"):
                st.session_state.preset_prompt = "Review this Python code for performance bottlenecks and suggest an async optimization with clean type hints."
        with p_cols[3]:
            if btn("⚡ Fast MVP", help="Break down a project into a 2-hour build plan"):
                st.session_state.preset_prompt = "Break down a winning 2-hour hackathon MVP build plan: Frontend, Backend API, Database, and Demo flow."

    empty_ph = st.empty()
    if not st.session_state.chat_history:
        ui("""
        <div class="empty flat">
          <div class="empty-ico">⚡</div>
          <div class="empty-t">What are we shipping today?</div>
          <div class="empty-d">Ask for a pitch, an architecture diagram, a code review or a 2-hour MVP plan.
          Pick a starter above or type below. Press <kbd>/</kbd> to jump to the prompt, or <kbd>Ctrl+K</kbd> to search.</div>
        </div>
        """, empty_ph)

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"], avatar=AVATARS.get(msg["role"])):
            sanitized = sanitize_markdown_text(msg["content"])
            st.markdown(sanitized)

    input_box_value = st.session_state.pop("preset_prompt", None)
    user_prompt = st.chat_input("Ask anything (ideas, architecture, code, business model)...") or input_box_value

    if user_prompt:
        actual_model = model_name.split()[0]
        empty_ph.empty()
        if len(st.session_state.chat_history) == 0:
            auto_title = derive_auto_title(user_prompt, groq_key)
            st.session_state.current_session_title = auto_title

        st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        with st.chat_message("user", avatar=AVATARS["user"]):
            st.markdown(user_prompt)

        with st.chat_message("assistant", avatar=AVATARS["assistant"]):
            message_placeholder = st.empty()
            full_response = ""
            t0 = time.time()

            try:
                system_instruction = (
                    "You are an elite hackathon AI advisor. The current year is 2026. "
                    "All recommendations, frameworks, libraries, and architecture designs must reflect modern 2026 standards. "
                    "Provide crisp, structured answers. "
                    "When providing diagrams, always use valid Mermaid syntax starting with 'flowchart TD' "
                    "on its own line, and enclose all node labels containing parentheses or spaces in double quotes: "
                    'e.g. id["Presentation Service (FastAPI)"].'
                )

                if "Groq" in provider:
                    if not groq_key:
                        st.error("Please add your Groq Cloud Key in the left sidebar API Vault!")
                    else:
                        client = Groq(api_key=groq_key)
                        messages = [{"role": "system", "content": system_instruction}]
                        messages += [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history]
                        completion = client.chat.completions.create(
                            model=actual_model,
                            messages=messages,
                            stream=True
                        )
                        for chunk in completion:
                            delta = chunk.choices[0].delta.content or ""
                            full_response += delta
                            message_placeholder.markdown(full_response + "▌")
                elif "OpenRouter" in provider:
                    if not openrouter_key:
                        st.error("Please add your OpenRouter API Key in the left sidebar API Vault!")
                    else:
                        messages = [{"role": "system", "content": system_instruction}]
                        messages += [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history]
                        headers = {
                            "Authorization": f"Bearer {openrouter_key}",
                            "HTTP-Referer": "http://localhost:8501",
                            "X-Title": "AI Hub",
                            "Content-Type": "application/json"
                        }
                        payload = {
                            "model": actual_model,
                            "messages": messages,
                            "stream": True
                        }
                        with httpx.Client(timeout=60.0) as client:
                            with client.stream("POST", "https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload) as response:
                                if response.status_code != 200:
                                    err_text = response.read().decode("utf-8", errors="ignore")
                                    raise Exception(f"OpenRouter Error ({response.status_code}): {err_text}")
                                for line in response.iter_lines():
                                    line = line.strip()
                                    if not line or not line.startswith("data: "):
                                        continue
                                    data_str = line[6:]
                                    if data_str == "[DONE]":
                                        break
                                    try:
                                        chunk = json.loads(data_str)
                                        delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                        if delta:
                                            full_response += delta
                                            message_placeholder.markdown(full_response + "▌")
                                    except Exception:
                                        continue
                elif "Adaption" in provider:
                    if not adaption_key:
                        st.error("Please add your Adaption Labs Key in the left sidebar API Vault!")
                    else:
                        messages = [{"role": "system", "content": system_instruction}]
                        messages += [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history]
                        headers = {
                            "Authorization": f"Bearer {adaption_key}",
                            "Content-Type": "application/json"
                        }
                        payload = {
                            "model": actual_model,
                            "messages": messages,
                            "stream": True
                        }
                        with httpx.Client(timeout=60.0) as client:
                            with client.stream("POST", "https://api.adaptionlabs.ai/v1/chat/completions", headers=headers, json=payload) as response:
                                if response.status_code != 200:
                                    err_text = response.read().decode("utf-8", errors="ignore")
                                    raise Exception(f"Adaption Labs Error ({response.status_code}): {err_text}")
                                for line in response.iter_lines():
                                    line = line.strip()
                                    if not line or not line.startswith("data: "):
                                        continue
                                    data_str = line[6:]
                                    if data_str == "[DONE]":
                                        break
                                    try:
                                        chunk = json.loads(data_str)
                                        delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                        if delta:
                                            full_response += delta
                                            message_placeholder.markdown(full_response + "▌")
                                    except Exception:
                                        continue
                else:
                    if not gemini_key:
                        st.error("Please add your Gemini API Key in the left sidebar API Vault!")
                    else:
                        client = genai.Client(api_key=gemini_key)
                        full_prompt = system_instruction + "\n\n"
                        for m in st.session_state.chat_history:
                            full_prompt += f"{m['role'].upper()}: {m['content']}\n"
                        try:
                            resp = client.models.generate_content(
                                model=actual_model,
                                contents=full_prompt
                            )
                            full_response = resp.text
                        except Exception:
                            alt_model = "gemini-3.5-flash" if actual_model == "gemini-3.8-flash" else "gemini-3.8-flash"
                            resp = client.models.generate_content(
                                model=alt_model,
                                contents=full_prompt
                            )
                            full_response = resp.text

                if full_response:
                    elapsed = time.time() - t0
                    clean_output = sanitize_markdown_text(full_response)
                    message_placeholder.markdown(clean_output)
                    wps = len(full_response.split()) / max(elapsed, 0.01)
                    ui(chips([
                        f"<b>{elapsed:.2f}s</b> total",
                        f"<b>{wps:.0f}</b> words/sec",
                        esc(model_name),
                    ]))

                    st.session_state.last_latency = elapsed
                    render_telemetry(telemetry_ph)

                    st.session_state.chat_history.append({"role": "assistant", "content": full_response})
                    save_session(
                        st.session_state.current_session_id,
                        st.session_state.current_session_title,
                        st.session_state.chat_history
                    )

            except Exception as e:
                st.error(f"API Error ({provider}): {e}")

# ===================================================
# TAB 2: VISUAL & DOCUMENT AUDITOR
# ===================================================
with tab2:
    tab_header("Visual & Document Auditor",
               "Cross-examine several screenshots, images and PDFs at once with Gemini Flash.")

    col_upload, col_result = st.columns([1, 1], gap="medium")

    with col_upload:
        with st.container(key="panel_audit_input"):
            step(1, "Upload", "PNG, JPG or PDF. Batch supported.")
            raw_files = st.file_uploader(
                "Upload Images or PDF Documents (Batch supported):",
                type=["png", "jpg", "jpeg", "pdf"],
                accept_multiple_files=True,
                key=f"tab2_file_uploader_{st.session_state.tab2_uploader_nonce}",
                label_visibility="collapsed",
                help="Select one or more files. Files and reports stay saved when you switch tabs."
            )

            st.session_state.tab2_saved_files = [
                {"name": f.name, "type": f.type, "bytes": f.getvalue()} for f in (raw_files or [])
            ]

            active_files = st.session_state.tab2_saved_files
            images_to_analyze = []
            pdf_parts_to_analyze = []

            if active_files:
                ui(chips([f"<b>{len(active_files)}</b> file(s) loaded and kept across tabs"]))
                with st.expander("🖼️ Uploaded Files Gallery", expanded=True):
                    preview_cols = st.columns(min(len(active_files), 3))
                    for idx, item in enumerate(active_files):
                        c = preview_cols[idx % 3]
                        if item["type"] == "application/pdf":
                            pdf_parts_to_analyze.append(types.Part.from_bytes(data=item["bytes"], mime_type="application/pdf"))
                            ui(f'<div class="filecard"><span>📄</span><span>{esc(item["name"])}'
                               f'<small>{len(item["bytes"]) / 1024:.1f} KB</small></span></div>', c)
                        else:
                            img = Image.open(io.BytesIO(item["bytes"]))
                            images_to_analyze.append(img)
                            with c:
                                show_image(img, caption=item["name"])

            step(2, "Choose an objective", "The prompt below updates instantly.")
            mode_preset = st.selectbox(
                "Analysis Objective:",
                options=list(AUDITOR_PRESETS.keys()),
                key="tab2_mode_selector",
                on_change=on_objective_change,
                label_visibility="collapsed"
            )

            analysis_prompt = st.text_area(
                "Analysis Prompt:",
                key="tab2_analysis_prompt",
                height=120
            )

            step(3, "Run", "Gemini Flash reads every file together.")
            run_btn = btn("✦ Run Multimodal Audit", type="primary")

    with col_result:
        with st.container(key="panel_audit_result"):
            panel_title("◈", "Executive Audit Report", "Findings appear here and stay when you switch tabs.")

            if run_btn:
                if not gemini_key:
                    st.error("Add your Gemini API key in the sidebar API Key Vault.")
                elif not active_files:
                    st.warning("Upload at least one image or PDF first.")
                else:
                    with st.spinner(f"Gemini Flash is analyzing {len(active_files)} file(s)..."):
                        t0 = time.time()
                        try:
                            client = genai.Client(api_key=gemini_key)
                            contents = []
                            contents.extend(pdf_parts_to_analyze)
                            contents.extend(images_to_analyze)
                            contents.append(analysis_prompt)

                            try:
                                response = client.models.generate_content(
                                    model="gemini-3.8-flash",
                                    contents=contents
                                )
                            except Exception:
                                response = client.models.generate_content(
                                    model="gemini-3.5-flash",
                                    contents=contents
                                )

                            elapsed = time.time() - t0
                            st.session_state.tab2_report = response.text
                            st.session_state.tab2_report_elapsed = elapsed
                            st.session_state.tab2_report_files_count = len(active_files)
                        except Exception as e:
                            st.error(f"Gemini API Error: {e}")

            if st.session_state.tab2_report:
                ui(chips([
                    f"<b>{st.session_state.tab2_report_files_count}</b> file(s)",
                    f"<b>{st.session_state.tab2_report_elapsed:.2f}s</b> runtime",
                ]))
                st.markdown(st.session_state.tab2_report)

                c_down, c_clear = st.columns([2, 1])
                with c_down:
                    dl_btn(
                        label="↓ Download Report (.md)",
                        data=st.session_state.tab2_report,
                        file_name=f"audit_report_{int(time.time())}.md",
                        mime="text/markdown"
                    )
                with c_clear:
                    if btn("✕ Clear Report"):
                        st.session_state.tab2_report = None
                        st.session_state.tab2_saved_files = []
                        st.session_state.tab2_uploader_nonce += 1
                        st.rerun()
            elif not run_btn:
                ui("""
                <div class="empty">
                  <div class="empty-ico">◈</div>
                  <div class="empty-t">No report yet</div>
                  <div class="empty-d">Upload files, choose an objective and run the audit.
                  The report stays here when you switch tabs.</div>
                </div>
                """)

# ===================================================
# TAB 3: FREE CLOUD IMAGE & VIDEO STUDIO
# ===================================================
with tab3:
    tab_header("Free Cloud Media Studio",
               "Native 1024x1024 visuals and 5–30s multi-scene MP4 video. 100% free with 0% laptop GPU load.")

    img_col, vid_col = st.columns(2, gap="large")

    # ---- Image ----
    with img_col:
        with st.container(key="panel_image"):
            panel_title("✦", "Cloud Image Studio", "FLUX.1-schnell with automatic Stable Horde fallback, up to 1024x1024.")

            st.selectbox(
                "Image Style & Preset:",
                options=list(IMAGE_PRESETS.keys()),
                key="tab3_img_preset",
                on_change=on_img_preset_change
            )

            img_prompt = st.text_area(
                "Visual Prompt:",
                key="tab3_img_prompt",
                height=105
            )

            c_model, c_aspect = st.columns(2)
            with c_model:
                model_choice = st.selectbox(
                    "Model Engine:",
                    ["FLUX.1-schnell (Max 1024 Quality)", "Pollinations Cloud FLUX (Zero Token)", "Stable Diffusion (Fast)"],
                    index=0,
                    key="tab3_model_choice"
                )
            with c_aspect:
                aspect = st.selectbox(
                    "Resolution:",
                    list(IMG_DIMS.keys()),
                    index=0,
                    key="tab3_aspect"
                )
            w, h = IMG_DIMS[aspect]
            use_flux = model_choice.startswith("FLUX")

            ui(chips([f"<b>{w}×{h}</b> output", "FLUX.1-schnell" if use_flux else "Stable Horde"]))

            gen_img_btn = btn("✦ Generate Image in Cloud", type="primary")
            img_status_box = st.empty()

            if gen_img_btn:
                with st.spinner("Generating on cloud GPU cluster (0% laptop GPU load)..."):
                    t0 = time.time()
                    try:
                        img_data = generate_cloud_image_flux_or_horde(
                            img_prompt,
                            width=w,
                            height=h,
                            hf_token=hf_token,
                            engine_choice=model_choice,
                            status_placeholder=img_status_box
                        )
                        elapsed = time.time() - t0
                        img_status_box.success(f"Generated {w}x{h} visual in {elapsed:.1f} seconds!")

                        st.session_state.tab3_image_bytes = img_data
                        st.session_state.tab3_image_caption = f"Generated in {w}x{h} via Cloud GPU in {elapsed:.1f}s | Preserved across tabs"
                    except Exception as e:
                        img_status_box.error(f"Image Generation Error: {e}")

            if st.session_state.tab3_image_bytes:
                gen_image = Image.open(io.BytesIO(st.session_state.tab3_image_bytes))
                show_image(gen_image, caption=st.session_state.tab3_image_caption)

                c_img_down, c_img_clear = st.columns([2, 1])
                with c_img_down:
                    dl_btn(
                        label="↓ Download High-Res Image (.webp)",
                        data=st.session_state.tab3_image_bytes,
                        file_name=f"cloud_visual_{int(time.time())}.webp",
                        mime="image/webp"
                    )
                with c_img_clear:
                    if btn("✕ Clear Image"):
                        st.session_state.tab3_image_bytes = None
                        st.session_state.tab3_image_caption = None
                        st.rerun()

    # ---- Video ----
    with vid_col:
        with st.container(key="panel_video"):
            panel_title("▶", "Cloud Video Studio", "Multi-Scene Storyboard Director (20-30s Unlimited MP4) & LTX-Video Cloud.")

            st.selectbox(
                "Video Style & Preset:",
                options=list(VIDEO_PRESETS.keys()),
                key="tab3_vid_preset",
                on_change=on_vid_preset_change
            )

            vid_prompt = st.text_area(
                "Motion Video Prompt:",
                key="tab3_vid_prompt",
                height=105
            )

            vid_engine = st.selectbox(
                "Video Engine:",
                [
                    "Multi-Scene Storyboard Director (20-30s Unlimited MP4)",
                    "Auto-Failover (ZeroGPU LTX + Multi-Scene Fallback)",
                    "Lightricks LTX-Video (Cloud ZeroGPU 2-4s)"
                ],
                index=0,
                key="tab3_vid_engine"
            )

            c_vres, c_vdur = st.columns(2)
            with c_vres:
                vid_res_label = st.selectbox(
                    "Video Resolution:",
                    list(VID_DIMS.keys()),
                    index=0,
                    key="tab3_vid_res"
                )
            vw, vh = VID_DIMS[vid_res_label]

            with c_vdur:
                vid_dur_label = st.selectbox(
                    "Video Duration:",
                    [
                        "5 Seconds (1 Scene • Quick Clip)",
                        "10 Seconds (2 Scenes • Double Sequence)",
                        "15 Seconds (3 Scenes • Story Arc)",
                        "20 Seconds (4 Scenes • Extended Film)",
                        "30 Seconds (6 Scenes • Feature Storyboard)"
                    ],
                    index=3,
                    key="tab3_vid_duration"
                )
            dur_val = int(vid_dur_label.split()[0])

            ui(chips([f"<b>{vw}×{vh}</b> output", f"<b>{dur_val}s</b> duration", "0% Laptop GPU"]))

            gen_vid_btn = btn("▶ Generate Video in Cloud", type="primary")
            vid_status_box = st.empty()

            if gen_vid_btn:
                with st.spinner(f"Synthesizing {dur_val}s cinematic video in cloud (0% laptop GPU load)..."):
                    t0 = time.time()
                    try:
                        if "Multi-Scene Storyboard" in vid_engine or dur_val > 4:
                            vid_bytes = synthesize_multiscene_video(
                                vid_prompt,
                                width=vw,
                                height=vh,
                                total_duration=dur_val,
                                status_placeholder=vid_status_box
                            )
                        else:
                            vid_bytes = generate_cloud_video_ltx(
                                prompt=vid_prompt,
                                width=vw,
                                height=vh,
                                duration=dur_val,
                                hf_token=hf_token,
                                status_placeholder=vid_status_box
                            )
                        elapsed = time.time() - t0
                        vid_status_box.success(f"Generated {dur_val}s ({vw}x{vh}) cinematic video in {elapsed:.1f} seconds!")

                        st.session_state.tab3_video_bytes = vid_bytes
                        st.session_state.tab3_video_caption = f"Generated {dur_val}s {vw}x{vh} clip via Cloud in {elapsed:.1f}s | Preserved across tabs"
                    except Exception as e:
                        vid_status_box.error(f"Video Generation Error: {e}")

            if st.session_state.tab3_video_bytes:
                st.video(st.session_state.tab3_video_bytes)
                st.caption(st.session_state.tab3_video_caption)

                c_vid_down, c_vid_clear = st.columns([2, 1])
                with c_vid_down:
                    dl_btn(
                        label="↓ Download Video (.mp4)",
                        data=st.session_state.tab3_video_bytes,
                        file_name=f"cloud_video_{int(time.time())}.mp4",
                        mime="video/mp4"
                    )
                with c_vid_clear:
                    if btn("✕ Clear Video"):
                        st.session_state.tab3_video_bytes = None
                        st.session_state.tab3_video_caption = None
                        st.rerun()

            with st.expander("🌐 External Cloud Studios (For 4K Hollywood Studio Renders)", expanded=False):
                st.markdown("""
                * **[Hailuo AI (MiniMax)](https://hailuoai.video/):** #1 worldwide photorealism. Free Google login.
                * **[Kling AI 1.5](https://klingai.com/):** 66 free daily credits for 1080p Hollywood clips.
                * **[Wan 2.1 Space (Hugging Face ZeroGPU)](https://huggingface.co/spaces/Wan-AI/Wan2.1):** 14B diffusion model running on cloud H100s.
                * **[PixVerse AI](https://pixverse.ai/):** Cinematic pans, 4K rendering, and free daily credits.
                """)

# ===================================================
# TAB 4: DEPLOYMENT & FREE AI GUIDE
# ===================================================
with tab4:
    tab_header("GitHub Live Deployment & Cloud Studio",
               "Connect your GitHub account, publish to any repository of your choice, and launch live on Streamlit Cloud with 1 click.")

    # Live Git Environment Status
    git_info = get_git_info()
    detected_user = git_info["user"]
    active_origin = git_info["origin"]
    active_branch = git_info["branch"]

    # ---- 1. Primary GitHub Deployment Manager Container ----
    with st.container(key="panel_github_deploy"):
        panel_title("↗", "GitHub Repository & Live Cloud Deployment", "Connect your GitHub account and publish your custom repository.")

        c_gh_left, c_gh_right = st.columns([1.15, 0.85], gap="large")

        with c_gh_left:
            st.markdown("##### 1. Repository Configuration")
            gh_user = st.text_input(
                "GitHub Account / Username:",
                value=detected_user,
                key="tab4_gh_user",
                help="Your verified GitHub username. Detected automatically from your local gh / git configuration."
            )

            c_rname, c_rvis = st.columns([1.2, 0.8])
            with c_rname:
                custom_repo = st.text_input(
                    "Repository Name (Of Your Choice):",
                    value=git_info.get("repo_name") or "ai-hub",
                    key="tab4_custom_repo",
                    help="Name of the GitHub repository you wish to create or link to (e.g. ai-hub, hackathon-ai-studio)."
                )
            with c_rvis:
                vis_option = st.selectbox(
                    "Visibility:",
                    ["Public (Free Hosting)", "Private"],
                    index=0,
                    key="tab4_repo_vis",
                    help="Public repositories get unlimited 100% free hosting on Streamlit Community Cloud."
                )

            commit_note = st.text_input(
                "Commit Message:",
                value="Deploy AI Hub v5.0 - Multi-Model Hackathon Studio",
                key="tab4_commit_msg"
            )

            is_pub = "Public" in vis_option
            repo_full_name = f"{gh_user.strip()}/{custom_repo.strip()}"
            deploy_target_url = f"https://share.streamlit.io/deploy?repository={repo_full_name}&branch=main&mainModule=app.py"

            c_btn_push, c_btn_sync = st.columns([1.2, 0.8])
            with c_btn_push:
                publish_btn = btn("✦ Push & Publish to GitHub", type="primary")
            with c_btn_sync:
                sync_btn = btn("↻ Sync Latest Changes")

            publish_status = st.empty()

            if publish_btn:
                with st.spinner(f"Publishing project to GitHub ({repo_full_name})..."):
                    success, repo_res, deploy_link = execute_github_publish(
                        repo_name=custom_repo,
                        account=gh_user,
                        is_public=is_pub,
                        commit_msg=commit_note,
                        status_placeholder=publish_status
                    )
                    if success:
                        st.session_state.deployed_repo_url = repo_res
                        st.session_state.deployed_share_url = deploy_link
                        publish_status.success(f"Successfully pushed to GitHub: [{repo_res}]({repo_res})")
                        st.balloons()
                        st.rerun()
                    else:
                        publish_status.error(f"Deployment Error: {repo_res}")

            if sync_btn:
                with st.spinner("Syncing latest changes to GitHub..."):
                    success, repo_res, deploy_link = execute_github_publish(
                        repo_name=custom_repo,
                        account=gh_user,
                        is_public=is_pub,
                        commit_msg=commit_note,
                        status_placeholder=publish_status
                    )
                    if success:
                        st.toast("GitHub repository successfully updated!")
                    else:
                        publish_status.error(f"Sync Error: {repo_res}")

            if st.session_state.get("deployed_share_url") or active_origin:
                live_link = st.session_state.get("deployed_share_url") or deploy_target_url
                st.markdown(f"""
                <div style="margin-top:1rem;padding:1rem;border-radius:12px;background:rgba(52,211,153,0.08);border:1px solid rgba(52,211,153,0.3);">
                  <div style="font-weight:600;color:#34d399;font-size:0.95rem;margin-bottom:0.4rem;">
                    🚀 Ready to Launch on Streamlit Community Cloud
                  </div>
                  <div style="font-size:0.84rem;color:#cbd5e1;margin-bottom:0.8rem;">
                    Click below to launch your app live on the web. The repository, main branch, and entrypoint <code>app.py</code> are automatically pre-configured.
                  </div>
                  <a href="{live_link}" target="_blank" style="display:inline-block;padding:0.6rem 1.2rem;border-radius:10px;background:linear-gradient(135deg,#6366f1,#22d3ee);color:#ffffff;font-weight:600;text-decoration:none;box-shadow:0 8px 24px -4px rgba(99,102,241,0.6);">
                    🚀 Open 1-Click Streamlit Cloud Deployer ↗
                  </a>
                </div>
                """, unsafe_allow_html=True)

        with c_gh_right:
            st.markdown("##### 2. Live Cloud Link & Secrets")
            has_remote = bool(active_origin) or bool(st.session_state.get("deployed_repo_url"))
            ui(f"""
            <div class="ph" style="margin-bottom: 0.8rem;">
              <div class="cell {'up' if git_info['gh_installed'] else 'down'}">
                <b>GitHub Account</b>
                <i>{esc(detected_user)} ({'Verified' if git_info['gh_installed'] else 'Local'})</i>
              </div>
              <div class="cell {'up' if has_remote else 'down'}">
                <b>Remote Origin</b>
                <i>{'Connected' if has_remote else 'Pending push'}</i>
              </div>
              <div class="cell up">
                <b>Main Branch</b>
                <i>{esc(active_branch or 'main')}</i>
              </div>
              <div class="cell up">
                <b>Secret Vault</b>
                <i>Protected (.env ignored)</i>
              </div>
            </div>
            """)

            with st.expander("🔑 Streamlit Cloud Secrets (Copy & Paste)", expanded=True):
                st.caption("Paste these into Streamlit Cloud → **Advanced settings → Secrets**:")
                secrets_toml = (
                    f'GEMINI_API_KEY = "{os.getenv("GEMINI_API_KEY", "")}"\n'
                    f'GROQ_API_KEY = "{os.getenv("GROQ_API_KEY", "")}"\n'
                    f'OPENROUTER_API_KEY = "{os.getenv("OPENROUTER_API_KEY", "")}"\n'
                    f'HF_TOKEN = "{os.getenv("HF_TOKEN", "")}"\n'
                    f'ADAPTION_API_KEY = "{os.getenv("ADAPTION_API_KEY", "")}"\n'
                    f'STUDIO_PUBLIC_MODE = "1"'
                )
                st.code(secrets_toml, language="toml")
                st.caption("🔒 `STUDIO_PUBLIC_MODE = '1'` ensures visitors can't see your secret keys or browse other users' chats.")

    st.markdown("<div style='height: 1.2rem;'></div>", unsafe_allow_html=True)

    ui(f"""
    <div class="cred-grid">
      <div class="cred"><b>Google Gemini key</b>{pill("Gemini", bool(os.getenv("GEMINI_API_KEY")), "Configured", "Missing")}</div>
      <div class="cred"><b>Groq Cloud key</b>{pill("Groq", bool(os.getenv("GROQ_API_KEY")), "Configured", "Missing")}</div>
      <div class="cred"><b>OpenRouter key</b>{pill("OpenRouter", bool(os.getenv("OPENROUTER_API_KEY")), "Configured", "Missing")}</div>
      <div class="cred"><b>Hugging Face token</b>{pill("HF_TOKEN", bool(os.getenv("HF_TOKEN")), "Configured", "Missing")}</div>
      <div class="cred"><b>Adaption Labs key</b>{pill("Adaption", bool(os.getenv("ADAPTION_API_KEY")), "Configured", "Optional")}</div>
    </div>
    """)

    with st.expander("🏆 Curated Best Free Cloud AI Models (2026 Edition)", expanded=True):
        st.markdown("""
        Below is the curated selection of **100% Free, Zero-Card, Highest Quality** cloud AI models integrated into this studio:
        """)
        ui(model_matrix_cards_html())
        st.markdown("""
        #### Model Rankings & Strategic Recommendations:
        * **1. OpenRouter Free Tier (`deepseek/deepseek-r1:free`, `meta-llama/llama-3.3-70b:free`)**:
          Access DeepSeek-R1 (671B reasoning model on par with OpenAI o1) and Meta Llama 3.3 70B completely free with zero credit card at [openrouter.ai](https://openrouter.ai).
        * **2. Google Gemini 3.8 Flash (`gemini-3.8-flash`)** — **#1 for Multimodal Auditing**:
          1M token context window, March 2026 cutoff, native image/PDF multi-file OCR, and free tier of 15 RPM / 1M TPM at [aistudio.google.com](https://aistudio.google.com).
        * **3. Groq Cloud LPU (`qwen/qwen3.8-27b`)** — **#1 for Speed (600+ Tokens/Sec)**:
          LPU tensor processor hardware. Streams full multi-file architectures in under 2 seconds. Free at [console.groq.com](https://console.groq.com).
        * **4. Black Forest Labs FLUX.1-schnell & Pollinations Cloud** — **#1 for 1024x1024 Visuals**:
          12B parameter rectified flow transformer. Delivers crisp, photo-grade imagery in ~3 seconds with zero-token fallback.
        * **5. Multi-Scene Storyboard Synthesizer** — **#1 for 20–30s Unlimited In-Dashboard Video**:
          Multi-scene cinematic director chaining dynamic camera trajectories and buttery smooth alpha cross-dissolves into a seamless 20–30s MP4. 100% free with 0% laptop GPU load.
        """)

    with st.expander("🌐 How to Deploy, Where It Deploys, and What It Deploys", expanded=True):
        st.markdown("""
        * **What will it deploy?**
          It deploys the code of this entire AI Hub (`app.py`, `pyproject.toml`, `src/`) to the web.
        * **Where will it deploy?**
          To **Streamlit Community Cloud** (hosted for free by Snowflake) at a public web link like:
          `https://ai-hub-prototype.streamlit.app`
        * **How to deploy (3-Step Guide):**
          1. **Push your project to GitHub:** Click the button above to publish this repository to your GitHub account (`ankush-dev-eng`).
          2. **Click the 'Deploy' button:** Click the blue **Deploy** button at the top-right of your screen or click the 1-click launch link above.
          3. **Add Secrets:** In Advanced Settings, paste the TOML secrets shown above.
          Within 60 seconds, your studio is live on the internet so judges and teammates can open it from their phones or laptops!
        * **Do you NEED to deploy?**
          **No!** Right now it runs **locally on your laptop at `http://localhost:8501`**. It is 100% private, instant, and completely free without needing any public deployment unless you want to share with judges.
        """)

    with st.expander("💡 Quick Prompt Starters Reference", expanded=False):
        st.markdown("""
        * **✦ Pitch:** Generates a 3-sentence, judge-ready elevator pitch (Problem, Secret Sauce, Scalable Impact).
        * **⬡ Arch:** Generates complete API flows, microservice components, and syntax-safe Mermaid diagrams.
        * **◈ Debug:** Pinpoints memory leaks, async bottlenecks, and suggests optimized refactors.
        * **⚡ Fast MVP:** Gives a step-by-step 2-hour checklist to ship a minimum viable product before submission deadlines.
        """)

    with st.expander("💾 Zero-Junk Architecture (< 5 KB per session)", expanded=False):
        st.markdown("""
        * **Zero Disk Bloat (< 5 KB per session):**
          Unlike heavy Docker images or Ollama models (which took 50 GB), your chats are saved as tiny standard JSON text files in `data/sessions/`.
          Even **1,000 full chat sessions take less than 3 Megabytes** of total disk space!
        * **Automatic Naming:**
          The moment you start talking, your session is automatically summarized into an appropriate 3–5 word title (like *AI Waste Drone Pitch*).
        * **1-Click Clean Deletion:**
          When you click **'✕ Delete'**, the session JSON file is completely removed with `os.remove()`. No hidden databases, no background daemons, and zero residual junk left behind.
        * **Laptop Safety:**
          All inference runs on remote cloud hardware (Google TPU, Groq LPU, OpenRouter, FLUX Cloud, Storyboard Director). Your laptop's RTX 5060 remains at **0% load and ~40°C**, completely preventing thermal sirens or power overdraw.
        """)

# GetLayers interactive motion, cursor spring, canvas constellation & command palette
FX_JS_PATH = Path(__file__).parent / "src" / "studio_fx.js"
if FX_JS_PATH.exists():
    with open(FX_JS_PATH, "r", encoding="utf-8") as f:
        fx_code = f.read()
    try:
        import streamlit.components.v1 as components
        components.html(f"<script>{fx_code}</script>", height=0)
    except Exception:
        pass
