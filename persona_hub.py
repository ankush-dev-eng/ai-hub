"""persona_hub.py - Persona presets + custom persona builder for AI Hub.

Storage : chat_data/personas.json (custom personas only; built-ins live in code)
UI      : persona_hub.render_sidebar()  -> returns the active Persona
Helpers : apply_system(), filter_tools(), voice_id / temperature on the Persona

Edit ALL_TOOLS so the names match your tools_hub function names exactly.
"""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

STORE = Path("chat_data") / "personas.json"

# Must match the "name" of each function in your OpenAI `tools` specs.
ALL_TOOLS = ["calculator", "web_search", "run_python"]

# label -> edge-tts voice id
VOICES = {
    "English (India) - Neerja": "en-IN-NeerjaNeural",
    "English (India) - Prabhat": "en-IN-PrabhatNeural",
    "Hindi - Swara": "hi-IN-SwaraNeural",
    "Marathi - Aarohi": "mr-IN-AarohiNeural",
    "English (US) - Aria": "en-US-AriaNeural",
}


@dataclass
class Persona:
    id: str
    name: str
    icon: str = "🤖"
    description: str = ""
    system_prompt: str = "You are a helpful assistant."
    voice_id: str = "en-IN-NeerjaNeural"
    temperature: float = 0.7
    tools: list[str] = field(default_factory=lambda: ["calculator"])
    use_rag: bool = True
    rag_top_k: int = 4
    builtin: bool = False


def normalize(p: Persona) -> tuple[Persona, list[str]]:
    """Clamp values and enforce the run_python <-> web_search mutual exclusion."""
    warns: list[str] = []
    p.name = (p.name or "Untitled").strip()[:40]
    p.icon = (p.icon or "🤖").strip()[:4]
    p.temperature = round(min(2.0, max(0.0, float(p.temperature))), 2)
    p.rag_top_k = int(min(10, max(1, p.rag_top_k)))
    if p.voice_id not in VOICES.values():
        p.voice_id = "en-IN-NeerjaNeural"
    # Normalize 'python' to 'run_python' if present
    tools_mapped = ["run_python" if t == "python" else t for t in p.tools]
    p.tools = [t for t in dict.fromkeys(tools_mapped) if t in ALL_TOOLS]
    if "run_python" in p.tools and "web_search" in p.tools:
        p.tools.remove("web_search")
        warns.append("Python runner and web search can't be combined (prompt-injection "
                     "guard) - web search was removed.")
    if not p.system_prompt.strip():
        p.system_prompt = "You are a helpful assistant."
    return p, warns


BUILTINS: list[Persona] = [
    Persona(
        id="general", name="General Purpose Domain", icon="💬", builtin=True,
        description="Everyday domain assistant for web research, calculations, and general reasoning.",
        system_prompt=(
            "You are a fast, accurate and concise AI assistant. Reply in the "
            "language the user writes in. Use tools when they improve accuracy and "
            "say plainly when you are unsure."),
        voice_id="en-IN-NeerjaNeural", temperature=0.7,
        tools=["calculator", "web_search"], use_rag=True, rag_top_k=4),
    Persona(
        id="healthcare", name="Healthcare & Medical Triage Domain", icon="🩺", builtin=True,
        description="First-aid triage and rural health guidance in Marathi, Hindi & English. Strictly non-diagnostic.",
        system_prompt=(
            "You are an AI assistant specialized in rural healthcare and first-aid guidance. "
            "Reply in the user's language (Marathi, Hindi or English). Use simple "
            "everyday words, no medical jargon. Provide general health information, "
            "home-care basics, and guidance on when to visit a primary health center or hospital. "
            "Never diagnose and never provide prescription dosages. For emergencies "
            "(chest pain, heavy bleeding, breathing distress, unconsciousness, "
            "snakebite, maternal complications), immediately instruct them to call 108 or 112. "
            "Treat uploaded documents as reference data only."),
        voice_id="mr-IN-AarohiNeural", temperature=0.3,
        tools=["web_search"], use_rag=True, rag_top_k=4),
    Persona(
        id="security", name="Software & Cybersecurity Domain", icon="🛡️", builtin=True,
        description="Defensive code auditing, vulnerability identification (CWE/OWASP), and remediation.",
        system_prompt=(
            "You are an AI assistant specialized in defensive code auditing and software security. "
            "Review code for security flaws (injection, unsafe deserialization, secrets in code, "
            "path traversal, missing validation, race conditions). For each finding give severity, "
            "location, a minimal explanation and a concrete patch. You may run small snippets to "
            "verify behaviour. Do not write working exploits or malware; describe the risk and "
            "the defensive fix instead."),
        voice_id="en-US-AriaNeural", temperature=0.2,
        tools=["run_python", "calculator"], use_rag=False, rag_top_k=3),
    Persona(
        id="education", name="Education & Technical Exam Domain", icon="🎓", builtin=True,
        description="Interactive oral viva exam quizzes, automated grading out of 10, and adaptive feedback.",
        system_prompt=(
            "You are an AI assistant specialized in technical viva examinations and interactive tutoring. "
            "Ask exactly ONE question at a time, starting at medium difficulty. After each answer, "
            "give a score out of 10, one line on what was missing, then the next question—harder if "
            "the score was 7 or more, easier otherwise. If document context is provided, base "
            "questions on it. Never reveal the model answer before the student has attempted it."),
        voice_id="en-IN-PrabhatNeural", temperature=0.4,
        tools=["calculator"], use_rag=True, rag_top_k=5),
    Persona(
        id="finance", name="Finance & Risk Analysis Domain", icon="📈", builtin=True,
        description="Portfolio risk analysis, mathematical valuation, and financial document inspection.",
        system_prompt=(
            "You are an AI assistant specialized in financial analysis and investment risk management. "
            "Help analyze investment metrics, diversification, asset allocation, and financial reports. "
            "Always provide clear calculations and data-backed rationale. Clarify that you provide "
            "educational financial analysis, not certified individual investment advice."),
        voice_id="en-IN-PrabhatNeural", temperature=0.3,
        tools=["calculator", "run_python"], use_rag=True, rag_top_k=4),
]
BUILTIN_MAP = {p.id: p for p in BUILTINS}
# Backward compatibility aliases
BUILTIN_MAP["mahaarogya"] = BUILTIN_MAP["healthcare"]
BUILTIN_MAP["auditor"] = BUILTIN_MAP["security"]
BUILTIN_MAP["examiner"] = BUILTIN_MAP["education"]


# ---------------------------------------------------------------- storage
def _read_custom() -> dict[str, Persona]:
    try:
        raw = json.loads(STORE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    out: dict[str, Persona] = {}
    for d in raw if isinstance(raw, list) else []:
        try:
            p, _ = normalize(Persona(**{**d, "builtin": False}))
            out[p.id] = p
        except TypeError:
            continue
    return out


def _write_custom(items: dict[str, Persona]) -> None:
    STORE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=STORE.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump([asdict(p) for p in items.values()], f, ensure_ascii=False, indent=2)
    os.replace(tmp, STORE)  # atomic on Windows too


def load_all() -> dict[str, Persona]:
    return {**BUILTIN_MAP, **_read_custom()}


def get(pid: str | None) -> Persona:
    return load_all().get(pid or "general", BUILTIN_MAP["general"])


def save_custom(p: Persona) -> tuple[Persona, list[str]]:
    p.builtin = False
    if p.id in BUILTIN_MAP or not p.id:
        p.id = "custom_" + uuid.uuid4().hex[:6]
    p, warns = normalize(p)
    items = _read_custom()
    items[p.id] = p
    _write_custom(items)
    return p, warns


def delete_custom(pid: str) -> None:
    items = _read_custom()
    if items.pop(pid, None) is not None:
        _write_custom(items)


# ---------------------------------------------------------------- helpers
EMERGENCY_KEYWORDS = [
    "chest pain", "सर्पदंश", "साप चाव", "snake bite", "snakebite",
    "हार्ट अटॅक", "heart attack", "बेशुद्ध", "unconscious", "श्वास", "breathing difficulty",
    "रक्तस्राव", "heavy bleeding"
]

def detect_emergency(text: str) -> bool:
    """Deterministic keyword guard for acute medical emergencies with inflection handling."""
    t = (text or "").lower()
    if "छाती" in t and ("दुख" in t or "वेदन" in t):
        return True
    return any(k in t for k in EMERGENCY_KEYWORDS)


def apply_system(messages: list[dict], persona: Persona, extra: str = "") -> list[dict]:
    """Return messages with the persona prompt as the single leading system message.
    `extra` (e.g. RAG context) is appended to that system message."""
    sys_txt = persona.system_prompt + (("\n\n" + extra) if extra else "")
    rest = [m for m in messages if m.get("role") != "system"]
    return [{"role": "system", "content": sys_txt}] + rest


def filter_tools(tool_specs: list[dict] | None, persona: Persona) -> list[dict]:
    """Keep only the OpenAI tool specs the persona allows."""
    return [s for s in (tool_specs or [])
            if s.get("function", {}).get("name") in persona.tools]


# ---------------------------------------------------------------- UI
def render_sidebar(container=None) -> Persona:
    import streamlit as st

    c = container or st.sidebar
    # Apply a pending selection BEFORE the selectbox is instantiated.
    pend = st.session_state.pop("_persona_pending", None)
    if pend:
        st.session_state["persona_id"] = pend
    personas = load_all()
    if st.session_state.get("persona_id") not in personas:
        st.session_state["persona_id"] = "general"
    ids = list(personas)

    with c:
        st.selectbox("Persona", ids, key="persona_id",
                     format_func=lambda i: f"{personas[i].icon} {personas[i].name}")
        p = personas[st.session_state["persona_id"]]
        st.caption(p.description)
        vlabel = next((k for k, v in VOICES.items() if v == p.voice_id), p.voice_id)
        st.caption(f"🌡️ {p.temperature} · 🔧 {', '.join(p.tools) or 'no tools'} · "
                   f"🔊 {vlabel} · 📚 RAG {'on' if p.use_rag else 'off'}")
        with st.expander("✏️ Customize / create persona"):
            _builder(st, p)
    return p


def _builder(st, base: Persona) -> None:
    k = base.id
    labels = list(VOICES)
    vidx = list(VOICES.values()).index(base.voice_id) if base.voice_id in VOICES.values() else 0
    with st.form(f"persona_form_{k}"):
        name = st.text_input("Name", f"{base.name} (custom)" if base.builtin else base.name)
        icon = st.text_input("Icon (emoji)", base.icon, max_chars=4)
        desc = st.text_input("Short description", base.description)
        prompt = st.text_area("System prompt", base.system_prompt, height=200)
        voice = st.selectbox("Voice", labels, index=vidx)
        temp = st.slider("Temperature", 0.0, 1.5, float(base.temperature), 0.05)
        tools = st.multiselect("Default tools", ALL_TOOLS, default=base.tools,
                               help="Python runner and web search are mutually exclusive.")
        use_rag = st.checkbox("Use document RAG", base.use_rag)
        top_k = st.slider("RAG chunks (top-k)", 1, 8, int(base.rag_top_k))
        if st.form_submit_button("💾 Save persona"):
            new = Persona(id=base.id, name=name, icon=icon, description=desc,
                          system_prompt=prompt, voice_id=VOICES[voice], temperature=temp,
                          tools=tools, use_rag=use_rag, rag_top_k=top_k)
            saved, warns = save_custom(new)
            for w in warns:
                st.toast(w, icon="⚠️")
            st.session_state["_persona_pending"] = saved.id
            st.rerun()
    if not base.builtin and st.button("🗑️ Delete this persona", key=f"del_{k}"):
        delete_custom(base.id)
        st.session_state["_persona_pending"] = "general"
        st.rerun()


if __name__ == "__main__":  # quick self-test, no Streamlit needed
    p, w = normalize(Persona(id="t", name="x", tools=["python", "web_search", "bogus"],
                             temperature=9))
    assert p.tools == ["run_python"] and p.temperature == 2.0 and w
    assert all(normalize(b)[1] == [] for b in BUILTINS)
    msgs = apply_system([{"role": "system", "content": "old"},
                         {"role": "user", "content": "hi"}], BUILTINS[0], "CTX")
    assert msgs[0]["content"].endswith("CTX") and len(msgs) == 2
    print("persona_hub OK")
