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
import re
import io
import sys
from pathlib import Path
from typing import Callable, Iterator, Union, List, Dict, Any

_SRC_PATH = str(Path(__file__).parent / "src")
if _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)

import streamlit as st
import streamlit.components.v1 as components

# --------------------------------------------------------------------------- #
# 0. Navigation & Models Configuration
# --------------------------------------------------------------------------- #
NAV = [
    "💬 Chat",
    "◈ Auditor",
    "🎨 Studio",
    "🚀 Deploy",
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
    dict(id="gemini:gemini-3.8-flash", provider="Gemini", name="Google Gemini 3.8 Flash",
         ctx="1M", cutoff="Apr 2026", speed="~180 tok/s"),
    dict(id="gemini:gemini-2.5-flash-lite", provider="Gemini", name="Google Gemini 2.5 Flash Lite",
         ctx="1M", cutoff="Feb 2026", speed="~210 tok/s"),
    dict(id="gemini:gemini-3.1-flash-lite", provider="Gemini", name="Google Gemini 3.1 Flash Lite",
         ctx="1M", cutoff="Mar 2026", speed="~250 tok/s"),

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
    "Write pitch strategy": "Write a 60-second hackathon pitch for this project with target audience, problem, solution, and business model.",
    "Draft architecture flow": "Draw the architecture flow for this project as a clean Mermaid flowchart TD with quoted labels.",
    "Review code for vulnerabilities": "Review the attached code for bugs, security issues, performance bottlenecks, and quick wins.",
    "Create 24h MVP roadmap": "Give me the fastest 24-hour MVP build plan with an actionable task split for 3 engineers.",
}

# --------------------------------------------------------------------------- #
# 1. CSS Design Tokens & Styling
# --------------------------------------------------------------------------- #
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root{
  --bg:#09090b; --panel:#141417; --panel-2:#18181b; --line:rgba(255,255,255,.08);
  --line-soft:rgba(255,255,255,.06); --accent:#ffffff;
  --accent-soft:rgba(255,255,255,.08); --text:#f4f4f5; --muted:#a1a1aa;
  --ease:120ms cubic-bezier(0.16, 1, 0.3, 1);
  --dock-h:5.5rem;
}

/* RULE: Never put backdrop-filter/transform/filter on root wrappers (.stApp, stMain, .block-container).
   Only style leaf elements to preserve fixed overlay and dialog behaviors. */
.stApp{background:var(--bg);color:var(--text)}
.stApp, .stApp p, .stApp label, .stApp li, .stApp input, .stApp textarea,
.stApp button, .stApp h1, .stApp h2, .stApp h3{
  font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif}
header[data-testid="stHeader"],
[data-testid="stHeader"] {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  height: 3.75rem !important;
  z-index: 100000 !important;
  background: transparent !important;
  border-bottom: none !important;
  box-shadow: none !important;
  pointer-events: none !important;
}
[data-testid="stToolbar"] {
  pointer-events: none !important;
}
[data-testid="stToolbarActions"],
[data-testid="stToolbarActions"] *,
[data-testid="stAppDeployButton"],
[data-testid="stAppDeployButton"] *,
[data-testid="stMainMenu"],
[data-testid="stMainMenu"] *,
button[data-testid="stBaseButton-header"] {
  pointer-events: auto !important;
}
[data-testid="stSidebar"],
section[data-testid="stSidebar"] {
  background: var(--panel) !important;
  border-right: 1px solid var(--line) !important;
  z-index: 1000005 !important;
}
[data-testid="stSidebarCollapseButton"] {
  z-index: 1000010 !important;
  pointer-events: auto !important;
  display: flex !important;
}
[data-testid="stSidebarCollapseButton"] button {
  pointer-events: auto !important;
  cursor: pointer !important;
  display: flex !important;
  opacity: 1 !important;
  visibility: visible !important;
}
[data-testid="stExpandSidebarButton"] {
  position: fixed !important;
  top: 1rem !important;
  left: 1rem !important;
  z-index: 1000010 !important;
  pointer-events: auto !important;
  display: flex !important;
  background: rgba(18, 22, 34, 0.9) !important;
  border: 1px solid rgba(255, 255, 255, 0.15) !important;
  border-radius: 8px !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
}
[data-testid="stExpandSidebarButton"] button {
  pointer-events: auto !important;
  cursor: pointer !important;
}
.block-container, [data-testid="stMainBlockContainer"] {
  max-width: 1200px !important;
  padding-top: 4.5rem !important;
  padding-bottom: 7rem !important;
  padding-left: 1.5rem !important;
  padding-right: 1.5rem !important;
}

/* ---- Full-Width Translucent Glass Segmented Navigation ---- */
[data-testid="stLayoutWrapper"]:has(.st-key-nav_wrapper),
[data-testid="stElementContainer"]:has(.st-key-nav_wrapper),
[data-testid="stLayoutWrapper"]:has(.st-key-hub_nav_segmented),
[data-testid="stElementContainer"]:has(.st-key-hub_nav_segmented),
[data-testid="stLayoutWrapper"]:has(.st-key-hub_nav_radio),
[data-testid="stElementContainer"]:has(.st-key-hub_nav_radio) {
  display: contents !important;
}

.st-key-nav_wrapper,
.st-key-hub_nav_segmented,
.st-key-hub_nav_radio,
.st-key-nav {
  position: sticky !important;
  top: 3.75rem !important;
  z-index: 990 !important;
  width: 100% !important;
  background: transparent !important;
  border-bottom: none !important;
  padding: 0 !important;
  margin: 0 0 1rem 0 !important;
  box-shadow: none !important;
}

/* 1. NATIVE st.segmented_control STYLING */
div[data-testid="stSegmentedControl"],
.st-key-hub_nav_segmented div[data-testid="stSegmentedControl"] {
  max-width: 100% !important;
  width: 100% !important;
  margin: 0 auto !important;
  display: flex !important;
  justify-content: stretch !important;
  align-items: center !important;
  background: rgba(24, 24, 27, 0.75) !important;
  backdrop-filter: blur(20px) !important;
  -webkit-backdrop-filter: blur(20px) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-radius: 12px !important;
  padding: 4px !important;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3) !important;
}

div[data-testid="stSegmentedControl"] button {
  flex: 1 1 0 !important;
  min-width: 0 !important;
  border: 1px solid transparent !important;
  border-radius: 10px !important;
  padding: 0.5rem 0.6rem !important;
  font-size: 0.88rem !important;
  font-weight: 500 !important;
  color: #94a3b8 !important;
  background: transparent !important;
  cursor: pointer !important;
  transition: all 0.15s cubic-bezier(0.16, 1, 0.3, 1) !important;
  white-space: nowrap !important;
  text-align: center !important;
}

div[data-testid="stSegmentedControl"] button:hover {
  color: #ffffff !important;
  background: rgba(255, 255, 255, 0.07) !important;
  border-color: rgba(255, 255, 255, 0.14) !important;
}

div[data-testid="stSegmentedControl"] button:active {
  transform: scale(0.97) !important;
}

div[data-testid="stSegmentedControl"] button[aria-checked="true"],
div[data-testid="stSegmentedControl"] button[aria-selected="true"],
div[data-testid="stSegmentedControl"] button[data-active="true"] {
  background: #27272a !important;
  color: #ffffff !important;
  font-weight: 600 !important;
  border: 1px solid rgba(255, 255, 255, 0.16) !important;
  box-shadow: none !important;
}

/* 2. FALLBACK st.radio STYLING (Eradicates radio circles & raw outlines) */
.st-key-nav_wrapper [role="radiogroup"],
.st-key-hub_nav_radio [role="radiogroup"],
.st-key-nav [role="radiogroup"] {
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  justify-content: stretch !important;
  align-items: center !important;
  gap: 0.35rem !important;
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 auto !important;
  padding: 4px !important;
  background: rgba(24, 24, 27, 0.75) !important;
  backdrop-filter: blur(20px) !important;
  -webkit-backdrop-filter: blur(20px) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-radius: 12px !important;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3) !important;
}

.st-key-nav_wrapper [role="radiogroup"] input[type="radio"],
.st-key-nav_wrapper [role="radiogroup"] label > div:first-child,
.st-key-nav_wrapper [role="radiogroup"] label svg,
.st-key-nav_wrapper [data-baseweb="radio"] > div:first-child,
.st-key-hub_nav_radio [role="radiogroup"] input[type="radio"],
.st-key-hub_nav_radio [role="radiogroup"] label > div:first-child,
.st-key-hub_nav_radio [role="radiogroup"] label svg,
.st-key-hub_nav_radio [data-baseweb="radio"] > div:first-child,
.st-key-nav [role="radiogroup"] input[type="radio"],
.st-key-nav [role="radiogroup"] label > div:first-child,
.st-key-nav [role="radiogroup"] label svg,
.st-key-nav [data-baseweb="radio"] > div:first-child {
  display: none !important;
  width: 0 !important;
  height: 0 !important;
  opacity: 0 !important;
  visibility: hidden !important;
  position: absolute !important;
  pointer-events: none !important;
}

.st-key-nav_wrapper [role="radiogroup"] label,
.st-key-hub_nav_radio [role="radiogroup"] label,
.st-key-nav [role="radiogroup"] label {
  flex: 1 1 0 !important;
  min-width: 0 !important;
  margin: 0 !important;
  padding: 0.48rem 0.55rem !important;
  border-radius: 10px !important;
  cursor: pointer !important;
  color: #94a3b8 !important;
  white-space: nowrap !important;
  border: 1px solid transparent !important;
  transition: all 0.15s cubic-bezier(0.16, 1, 0.3, 1) !important;
  font-size: 0.85rem !important;
  font-weight: 500 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  user-select: none !important;
  text-align: center !important;
}

.st-key-nav_wrapper [role="radiogroup"] label *,
.st-key-hub_nav_radio [role="radiogroup"] label *,
.st-key-nav [role="radiogroup"] label *,
div[data-testid="stSegmentedControl"] button * {
  overflow: visible !important;
  text-overflow: clip !important;
  white-space: nowrap !important;
}

.st-key-nav_wrapper [role="radiogroup"] label:hover,
.st-key-hub_nav_radio [role="radiogroup"] label:hover,
.st-key-nav [role="radiogroup"] label:hover {
  background: rgba(255, 255, 255, 0.07) !important;
  color: #ffffff !important;
  border-color: rgba(255, 255, 255, 0.14) !important;
}

.st-key-nav_wrapper [role="radiogroup"] label:active,
.st-key-hub_nav_radio [role="radiogroup"] label:active,
.st-key-nav [role="radiogroup"] label:active {
  transform: scale(0.97) !important;
}

.st-key-nav_wrapper [role="radiogroup"] label:has(input:checked),
.st-key-hub_nav_radio [role="radiogroup"] label:has(input:checked),
.st-key-nav [role="radiogroup"] label:has(input:checked) {
  background: #27272a !important;
  color: #ffffff !important;
  font-weight: 600 !important;
  border: 1px solid rgba(255, 255, 255, 0.14) !important;
  box-shadow: none !important;
}

.st-key-nav_wrapper [role="radiogroup"] label:has(input:checked) *,
.st-key-hub_nav_radio [role="radiogroup"] label:has(input:checked) *,
.st-key-nav [role="radiogroup"] label:has(input:checked) * {
  color: #ffffff !important;
  font-weight: 600 !important;
}

/* Claude / ChatGPT-style Floating Down-Arrow Button */
.fx-scroll-bottom-btn {
  position: fixed !important;
  bottom: 5.85rem !important;
  left: 50% !important;
  transform: translate(-50%, 10px) scale(0.9) !important;
  width: 36px !important;
  height: 36px !important;
  border-radius: 50% !important;
  background: #18181b !important;
  border: 1px solid rgba(255, 255, 255, 0.14) !important;
  color: #f4f4f5 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4) !important;
  backdrop-filter: blur(12px) !important;
  -webkit-backdrop-filter: blur(12px) !important;
  cursor: pointer !important;
  z-index: 998 !important;
  opacity: 0 !important;
  visibility: hidden !important;
  transition: opacity 0.15s ease, transform 0.15s cubic-bezier(0.16, 1, 0.3, 1), background 0.12s ease !important;
  pointer-events: none !important;
}

.fx-scroll-bottom-btn.visible {
  opacity: 1 !important;
  visibility: visible !important;
  transform: translate(-50%, 0) scale(1) !important;
  pointer-events: auto !important;
}

.fx-scroll-bottom-btn:hover {
  background: #202024 !important;
  border-color: rgba(255, 255, 255, 0.25) !important;
  color: #ffffff !important;
  transform: translate(-50%, -1px) scale(1.04) !important;
}

.fx-scroll-bottom-btn:active {
  transform: translate(-50%, 1px) scale(0.96) !important;
}

/* ---- Chat Messages (Claude / ChatGPT Typography) ---- */
[data-testid="stChatMessage"]{
  background: transparent !important;
  border: none !important;
  padding: 0.85rem 0 !important;
  margin-bottom: 0.4rem !important;
  box-shadow: none !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]){
  display: flex !important;
  justify-content: flex-end !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stMarkdownContainer"]{
  background: #27272a !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-radius: 18px !important;
  padding: 8px 16px !important;
  color: #f4f4f5 !important;
  max-width: 85% !important;
}
[data-testid="stCode"] pre, pre{
  background: #121215 !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-radius: 8px !important;
}

/* ---- Bottom Prompt Dock (Claude 3.5 & ChatGPT 4o Style) ---- */
[data-testid="stBottom"]>div{background: linear-gradient(to top, var(--bg) 80%, transparent) !important;}
[data-testid="stChatInput"]{
  background: #18181b !important;
  border: 1px solid rgba(255, 255, 255, 0.12) !important;
  border-radius: 20px !important;
  padding: 4px 10px !important;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4) !important;
  transition: border-color var(--ease) !important;
}
[data-testid="stChatInput"]:focus-within{
  border-color: rgba(255, 255, 255, 0.28) !important;
  box-shadow: none !important;
}
.st-key-dock_toolbar{position:sticky;bottom:var(--dock-h);z-index:50;padding:.25rem 0}

/* ---- Buttons (Minimalist Monochrome) ---- */
button[data-testid^="stBaseButton"]{
  background: #18181b !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: 8px !important;
  color: #f4f4f5 !important;
  transition: all var(--ease) !important;
  box-shadow: none !important;
}
button[data-testid^="stBaseButton"]:hover{
  background: #202024 !important;
  border-color: rgba(255, 255, 255, 0.2) !important;
  transform: translateY(-1px) !important;
}
button[data-testid="stBaseButton-primary"]{
  background: #ffffff !important;
  border-color: #ffffff !important;
  color: #09090b !important;
  font-weight: 600 !important;
}

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
}
/* ---- Images: Keep Fullscreen Button Anchored on Top-Right of Image ---- */
[data-testid="stImage"] {
  display: inline-flex !important;
  position: relative !important;
  width: fit-content !important;
  max-width: 100% !important;
}
[data-testid="stImage"] > div {
  position: relative !important;
  width: fit-content !important;
  display: inline-block !important;
}
[data-testid="stImage"] .stImageHoverButton,
[data-testid="stImage"] [data-testid="StyledFullScreenButton"] {
  position: absolute !important;
  top: 10px !important;
  right: 10px !important;
  left: auto !important;
  z-index: 25 !important;
  opacity: 0.85 !important;
}
[data-testid="stImage"]:hover .stImageHoverButton,
[data-testid="stImage"]:hover [data-testid="StyledFullScreenButton"] {
  opacity: 1 !important;
}

/* Media layout stability (CLS = 0) */
[data-testid="stImage"] img {
  border-radius: 12px !important;
  max-width: 100% !important;
  object-fit: contain !important;
  transform: translate3d(0, 0, 0);
}
[data-testid="stVideo"] video {
  border-radius: 12px !important;
  aspect-ratio: 16 / 9 !important;
  width: 100% !important;
  max-width: 100% !important;
  transform: translate3d(0, 0, 0);
}

/* Instant tactile feedback on button clicks */
button:active, [role="button"]:active {
  transform: scale(0.96) !important;
  transition: transform 0.05s ease-out !important;
}

[data-testid="stMainBlockContainer"],
.block-container,
[data-testid="stVerticalBlock"],
[data-testid="stVerticalBlockBorderWrapper"] {
  overflow: visible !important;
}

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
def inject_js():
    fx_path = Path(__file__).parent / "src" / "studio_fx.js"
    fx_code = ""
    if fx_path.exists():
        try:
            fx_code = fx_path.read_text(encoding="utf-8")
        except Exception:
            fx_code = ""
    components.html(f"""<script>
      try {{
        if (!window.parent.__studioFx) {{
          {fx_code}
        }} else if (window.parent.__studioFx.checkGreeting) {{
          window.parent.__studioFx.checkGreeting();
        }}
      }} catch (e) {{}}
    </script>""", height=0)

def scroll_bottom():
    components.html(f"""<script>/*{time.time()}*/
      const m = window.parent.document.querySelector('[data-testid="stMain"]');
      if (m) m.scrollTo({{top: m.scrollHeight, behavior: 'smooth'}});
    </script>""", height=0)

# --------------------------------------------------------------------------- #
# 3. Sticky Segmented Navigation
# --------------------------------------------------------------------------- #
def nav() -> str:
    if "nav_view" not in st.session_state or st.session_state.nav_view not in NAV:
        st.session_state.nav_view = NAV[0]

    with st.container(key="nav_wrapper"):
        if hasattr(st, "segmented_control"):
            chosen = st.segmented_control(
                "Navigation",
                NAV,
                default=st.session_state.nav_view,
                selection_mode="single",
                width="stretch",
                label_visibility="collapsed",
                key="hub_nav_segmented"
            )
            if chosen and chosen in NAV:
                st.session_state.nav_view = chosen
            return st.session_state.nav_view
        else:
            chosen = st.radio(
                "Navigation",
                NAV,
                index=NAV.index(st.session_state.nav_view),
                horizontal=True,
                label_visibility="collapsed",
                key="hub_nav_radio"
            )
            if chosen and chosen in NAV:
                st.session_state.nav_view = chosen
            return st.session_state.nav_view

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

# ----------------- BULLETPROOF MERMAID & MARKDOWN SANITIZER -----------------
def sanitize_mermaid_block(code: str) -> str:
    """Sanitizes raw Mermaid syntax so that browser Mermaid.js renders cleanly without parse errors."""
    code = code.strip()
    if not code:
        return 'flowchart TD\n    A["Empty Diagram"]'
    lines = [l.rstrip() for l in code.splitlines()]
    first = lines[0].strip() if lines else ""
    valid_headers = ("flowchart", "graph", "sequenceDiagram", "classDiagram", "stateDiagram", "erDiagram", "gantt", "pie", "gitGraph", "journey", "mindmap")
    if not any(first.startswith(h) for h in valid_headers):
        lines.insert(0, "flowchart TD")
    
    subgraph_count = 0
    end_count = 0
    cleaned_lines = []
    
    for line in lines:
        stripped = line.strip()
        if re.match(r'^subgraph\b', stripped, re.IGNORECASE):
            subgraph_count += 1
            m_sub = re.match(r'^(subgraph\s+)(.*)$', stripped, re.IGNORECASE)
            if m_sub:
                t = m_sub.group(2).strip()
                if t and not (t.startswith('"') and t.endswith('"')):
                    clean_t = t.replace('"', '')
                    line = f'{m_sub.group(1)}"{clean_t}"'
        elif re.match(r'^end\b', stripped, re.IGNORECASE):
            end_count += 1
        
        # Quote node labels with special characters
        def quote_label(m):
            nid = m.group(1)
            text = m.group(2).strip()
            if (text.startswith('"') and text.endswith('"')) or (text.startswith('("') and text.endswith('")')):
                return f'{nid}[{text}]'
            clean = text.replace('"', "'")
            return f'{nid}["{clean}"]'
        line = re.sub(r'(\b[A-Za-z0-9_]+)\[([^\[\]]+)\]', quote_label, line)
        cleaned_lines.append(line)
    
    while subgraph_count > end_count:
        cleaned_lines.append("    end")
        end_count += 1
    
    return "\n".join(cleaned_lines)

def safe_markdown(text: str) -> str:
    """Ensures markdown with ```mermaid blocks is 100% syntactically valid and never crashes."""
    if not text:
        return ""
    
    # Auto-close unclosed code block if response was truncated
    if text.count("```") % 2 != 0:
        if "```mermaid" in text:
            last_idx = text.rfind("```mermaid")
            after = text[last_idx + len("```mermaid"):]
            sub_c = len(re.findall(r'\bsubgraph\b', after, re.I))
            end_c = len(re.findall(r'\bend\b', after, re.I))
            if sub_c > end_c:
                text += "\n" + "\n".join(["    end"] * (sub_c - end_c))
        text += "\n```\n"
    
    def _repl(m):
        code = m.group(1)
        cleaned = sanitize_mermaid_block(code)
        return f"```mermaid\n{cleaned}\n```"
    
    return re.sub(r'```mermaid\s*([\s\S]*?)```', _repl, text)

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
                    msgs = loaded.get("messages", [])
                    for m in msgs:
                        if m.get("content"):
                            m["content"] = safe_markdown(m["content"])
                    ss.sessions[s["id"]] = {
                        "title": loaded.get("title", s.get("title", "Chat")),
                        "messages": msgs,
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

_TEXT_EXT = (
    ".py", ".js", ".ts", ".tsx", ".json", ".md", ".markdown", ".txt", ".notes", ".note",
    ".csv", ".tsv", ".html", ".css", ".yml", ".yaml", ".ipynb", ".java", ".c", ".cpp",
    ".h", ".hpp", ".cs", ".go", ".rs", ".v", ".sv", ".sh", ".bash", ".zsh", ".bat",
    ".ps1", ".sql", ".log", ".rst", ".xml", ".ini", ".env", ".toml", ".conf"
)

def _badges(meta: Dict[str, Any]):
    secs = max(0.01, float(meta.get("secs", 0.1)))
    toks = max(1, int(meta.get("tokens", 1)))
    tps = int(toks / secs)
    speed_tag = f" · {tps} tok/s" if tps > 0 else ""
    parts = [
        f'⚡ {secs:.2f}s',
        f'≈ {toks} tok{speed_tag}',
        f'☁️ {meta["provider"]} · {meta["model"]}'
    ]
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

    for m_idx, m in enumerate(sess["messages"]):
        with st.chat_message(m["role"]):
            if m.get("files"):
                st.caption("📎 " + ", ".join(m["files"]))
            if m.get("images"):
                for img_b in m["images"]:
                    try:
                        st.image(img_b, width=320)
                    except Exception:
                        pass
            if m.get("media"):
                for idx, med in enumerate(m["media"]):
                    media_card(med.get("kind", "image"), med.get("data"), key=f"chat_med_hist_{m_idx}_{idx}")
            st.markdown(safe_markdown(m["content"]))
            if m["role"] == "assistant" and m.get("meta"):
                _badges(m["meta"])

    queued = None
    if not sess["messages"]:
        components.html("""<script>
          try {
            const m = window.parent.document.querySelector('[data-testid="stMain"]');
            if (m && m.scrollTop > 0) m.scrollTop = 0;
          } catch (e) {}
        </script>""", height=0)
        st.markdown("""
        <div class="chat-empty-greeting">
          <h2>What can I help you ship?</h2>
          <p>Ultra-fast multi-model cloud reasoning, multimodal document auditing, and creative media synthesis — 100% cloud powered with zero local GPU load.</p>
        </div>
        """, unsafe_allow_html=True)

        st_keys = list(STARTERS.keys())
        c1, c2 = st.columns(2)
        with c1:
            if st.button(f"{st_keys[0]}  →", key=f"st_{st_keys[0]}", use_container_width=True):
                queued = STARTERS[st_keys[0]]
            if st.button(f"{st_keys[2]}  →", key=f"st_{st_keys[2]}", use_container_width=True):
                queued = STARTERS[st_keys[2]]
        with c2:
            if st.button(f"{st_keys[1]}  →", key=f"st_{st_keys[1]}", use_container_width=True):
                queued = STARTERS[st_keys[1]]
            if st.button(f"{st_keys[3]}  →", key=f"st_{st_keys[3]}", use_container_width=True):
                queued = STARTERS[st_keys[3]]

    # Floating prompt dock with sticky model selector
    if hasattr(st, "bottom"):
        b_ctx = st.bottom() if callable(st.bottom) else st.bottom
        with b_ctx:
            with st.container(key="dock_toolbar"):
                c1, _ = st.columns([3.5, 6.5], vertical_alignment="center")
                with c1:
                    model = model_selector()
            _raw_inp = _chat_input()
    else:
        with st.container(key="dock_toolbar"):
            c1, _ = st.columns([3.5, 6.5], vertical_alignment="center")
            with c1:
                model = model_selector()
        _raw_inp = _chat_input()

    text, files = _read_input(_raw_inp)
    text = queued or text
    if not text:
        if ss.pop("_scroll", False):
            scroll_bottom()
        return

    attachments, inline = [], []
    chat_imgs = []
    for f in files:
        data = f.getvalue()
        fname_lower = f.name.lower()
        if fname_lower.endswith(_TEXT_EXT):
            try:
                decoded_text = data.decode("utf-8", errors="replace")
            except Exception:
                decoded_text = str(data)
            inline.append(f"\n\n--- 📄 ATTACHED FILE: {f.name} ---\n```{f.name.split('.')[-1]}\n{decoded_text}\n```\n--- END OF FILE {f.name} ---\n")
        elif fname_lower.endswith(".pdf"):
            extracted = ""
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(data))
                pages_text = []
                for p_idx, page in enumerate(reader.pages):
                    t = page.extract_text()
                    if t and t.strip():
                        pages_text.append(f"[Page {p_idx+1}]\n{t.strip()}")
                if pages_text:
                    extracted = "\n\n".join(pages_text)
            except Exception:
                pass

            if not extracted:
                try:
                    import pdfplumber
                    with pdfplumber.open(io.BytesIO(data)) as pdf:
                        p_texts = []
                        for p_idx, page in enumerate(pdf.pages):
                            pt = page.extract_text()
                            if pt and pt.strip():
                                p_texts.append(f"[Page {p_idx+1}]\n{pt.strip()}")
                        if p_texts:
                            extracted = "\n\n".join(p_texts)
                except Exception:
                    pass

            if extracted:
                inline.append(f"\n\n--- 📑 ATTACHED PDF: {f.name} ---\n{extracted}\n--- END OF PDF {f.name} ---\n")
            else:
                inline.append(f"\n\n--- 📑 ATTACHED PDF: {f.name} ({len(data)} bytes, document ready for analysis) ---\n")
            attachments.append({"name": f.name, "mime": "application/pdf", "data": data})
        elif f.type.startswith("image/") or fname_lower.endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif')):
            attachments.append({"name": f.name, "mime": f.type or "image/png", "data": data})
            chat_imgs.append(data)
        else:
            try:
                decoded_text = data.decode("utf-8")
                inline.append(f"\n\n--- 📄 ATTACHED FILE: {f.name} ---\n```\n{decoded_text}\n```\n--- END OF FILE {f.name} ---\n")
            except Exception:
                attachments.append({"name": f.name, "mime": f.type, "data": data})
    full = text + "".join(inline)

    msg_record = {"role": "user", "content": full, "files": [f.name for f in files]}
    if chat_imgs:
        msg_record["images"] = chat_imgs
    sess["messages"].append(msg_record)
    if sess["title"] == "New chat":
        sess["title"] = text[:36]
    sess["ts"] = time.time()
    with st.chat_message("user"):
        if files:
            st.caption("📎 " + ", ".join(f.name for f in files))
        if chat_imgs:
            for img_b in chat_imgs:
                try:
                    st.image(img_b, width=320)
                except Exception:
                    pass
        st.markdown(safe_markdown(full))

    msgs = [{"role": m["role"], "content": m["content"]} for m in sess["messages"]]
    with st.chat_message("assistant"):
        t0 = time.perf_counter()
        try:
            out = generate(model, msgs, attachments)
            if isinstance(out, str):
                st.markdown(safe_markdown(out))
                reply = out
            else:
                reply = st.write_stream(out)
        except Exception as e:
            reply = f"⚠️ {model['provider']} failed: `{e}`"
            st.error(reply)

        gen_media = ss.pop("_last_generated_media", None)
        if gen_media:
            if not isinstance(gen_media, list):
                gen_media = [gen_media]
            for idx, med in enumerate(gen_media):
                media_card(med.get("kind", "image"), med.get("data"), key=f"chat_med_live_{int(time.time())}_{idx}")

        meta = {"secs": time.perf_counter() - t0, "tokens": max(1, len(reply) // 4),
                "provider": model["provider"], "model": model["name"]}
        _badges(meta)

    msg_record = {"role": "assistant", "content": safe_markdown(reply), "meta": meta}
    if gen_media:
        msg_record["media"] = gen_media
    sess["messages"].append(msg_record)
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
    is_min = st.session_state.get(f"min_{key}", False)
    if is_min:
        m_c1, m_c2 = st.columns([7.5, 2.5], vertical_alignment="center")
        icon = "🎵" if kind == "audio" else ("🎬" if kind == "video" else "🖼️")
        m_c1.caption(f"{icon} {kind.capitalize()} minimized")
        def _unmin():
            st.session_state[f"min_{key}"] = False
        m_c2.button(f"➕ Expand {kind.capitalize()}", key=f"unmin_{key}", on_click=_unmin, use_container_width=True)
        return

    if kind == "image":
        st.image(src, use_container_width=True)
    elif kind == "video":
        st.video(src)
    elif kind == "audio":
        st.audio(src)

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("⛶ Fullscreen", key=f"exp_{key}", use_container_width=True):
            _preview(kind, src)
    with c2:
        def _min():
            st.session_state[f"min_{key}"] = True
        st.button("➖ Minimize", key=f"min_btn_{key}", on_click=_min, use_container_width=True)
    with c3:
        if isinstance(src, bytes):
            ext = "png" if kind == "image" else ("mp4" if kind == "video" else "wav")
            mime = f"image/{ext}" if kind == "image" else (f"video/{ext}" if kind == "video" else f"audio/{ext}")
            st.download_button("⬇️ Download", data=src, file_name=f"{key}.{ext}", mime=mime, key=f"dl_card_{key}", use_container_width=True)

