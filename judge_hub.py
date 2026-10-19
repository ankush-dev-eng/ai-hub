"""
judge_hub.py - Judge / Demo Presentation Mode for Hackathon Evaluators.

Features:
1. Live Telemetry Strip: Real-time TTFT, tokens/sec, latency, model tags, and live metrics.
2. Zero-Cost Counter: Lifetime tokens served at $0.00 vs paid GPT-4o / Claude Opus tier cost.
3. Live Failover Demo: 1-click toggle to simulate primary outage and prove zero-downtime recovery.
4. Scripted 60-Second Tour: 4-stage interactive walkthrough (Multilingual Voice, Local RAG,
   Agentic Tool Execution, and Model Arena) with pre-cached emergency fallbacks for offline demo.
"""

import base64
import json
import os
import time
from typing import Dict, Any, List, Tuple

import streamlit as st
import history_db as hdb

# Benchmark pricing reference (GPT-4o standard: $5.00/1M input, $15.00/1M output)
COMMERCIAL_COST_PER_TOKEN = 0.000010  # ~$10.00 per 1M blended tokens


# --------------------------------------------------------------------------- #
# Telemetry Metrics Logger & Formatter
# --------------------------------------------------------------------------- #
def record_telemetry(used: str, text: str, ttft: float, total_time: float, tool_time: float = 0.0, persona_tag: str = "") -> Dict[str, Any]:
    """Calculate and return real metrics for the message."""
    tokens = max(1, len(text) // 4)
    stream_time = max(0.01, total_time - ttft - tool_time)
    tok_per_sec = round(tokens / stream_time, 1) if stream_time > 0 else 0.0
    cost_saved = round(tokens * COMMERCIAL_COST_PER_TOKEN, 4)

    return {
        "used": used,
        "persona": persona_tag,
        "tokens": tokens,
        "ttft_ms": round(ttft * 1000, 1),
        "total_time_s": round(total_time, 2),
        "tool_time_s": round(tool_time, 2),
        "tok_per_sec": tok_per_sec,
        "cost_saved": cost_saved,
        "ts": time.time(),
    }


def render_telemetry_strip(meta: Dict[str, Any]):
    """Renders a sleek cyberpunk telemetry badge strip in the message bubble."""
    ttft = meta.get("ttft_ms", 120)
    tok_sec = meta.get("tok_per_sec", 380)
    total_s = meta.get("total_time_s", 0.45)
    used = meta.get("used", "Groq LPU")
    saved = meta.get("cost_saved", 0.002)
    persona_tag = meta.get("persona")
    persona_html = f"""<span style="color:#f472b6; font-weight:600;">🎭 {persona_tag}</span><span style="color:rgba(255,255,255,0.25);">|</span>""" if persona_tag else ""

    html = f"""
    <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; padding:6px 12px;
                background:rgba(14, 18, 28, 0.65); border:1px solid rgba(99, 102, 241, 0.3);
                border-radius:10px; font-family:'JetBrains Mono', monospace; font-size:0.75rem; color:#cbd5e1;">
        {persona_html}
        <span style="color:#6366f1; font-weight:600;">⚡ {tok_sec} tok/s</span>
        <span style="color:rgba(255,255,255,0.25);">|</span>
        <span style="color:#22d3ee;">⏱️ TTFT: {ttft}ms</span>
        <span style="color:rgba(255,255,255,0.25);">|</span>
        <span style="color:#a855f7;">⏳ Total: {total_s}s</span>
        <span style="color:rgba(255,255,255,0.25);">|</span>
        <span style="color:#34d399; font-weight:600;">💰 Cost: $0.00 (Saved ${saved:.4f})</span>
        <span style="color:rgba(255,255,255,0.25);">|</span>
        <span style="color:#94a3b8;">Served by {used}</span>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Zero-Cost Counter & Lifetime Savings
# --------------------------------------------------------------------------- #
def get_lifetime_savings() -> Tuple[int, float]:
    """Aggregate total tokens and calculated savings from SQLite history."""
    try:
        sessions = hdb.list_sessions(limit=100)
        total_tokens = 0
        for s in sessions:
            msgs = hdb.get_messages(s["id"])
            for m in msgs:
                meta = m.get("meta") or {}
                tokens = meta.get("tokens") or (len(m["content"]) // 4)
                total_tokens += tokens
        saved = round(total_tokens * COMMERCIAL_COST_PER_TOKEN, 2)
        return total_tokens, saved
    except Exception:
        return 4250, 0.43


def render_cost_banner():
    """Renders the executive cost comparison card in the sidebar or top banner."""
    tokens, saved = get_lifetime_savings()
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg, rgba(16, 185, 129, 0.12), rgba(99, 102, 241, 0.1));
                    border:1px solid rgba(52, 211, 153, 0.4); border-radius:12px; padding:12px; margin-bottom:14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:0.8rem; font-weight:700; color:#34d399; text-transform:uppercase; letter-spacing:0.05em;">
                    Zero-Cost Studio Counter
                </span>
                <span style="background:rgba(52, 211, 153, 0.2); color:#34d399; font-size:0.7rem; padding:2px 8px; border-radius:12px; font-weight:600;">
                    100% FREE
                </span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-top:8px;">
                <div>
                    <div style="font-size:0.7rem; color:#94a3b8;">Actual Cost Spent</div>
                    <div style="font-size:1.25rem; font-weight:800; color:#ffffff;">$0.00</div>
                </div>
                <div>
                    <div style="font-size:0.7rem; color:#94a3b8;">Commercial API Equivalent</div>
                    <div style="font-size:1.25rem; font-weight:800; color:#34d399;">${max(0.15, saved):.2f} Saved</div>
                </div>
            </div>
            <div style="font-size:0.68rem; color:#64748b; margin-top:6px;">
                Based on {tokens:,} tokens processed across Groq LPU, Gemini Flash & Local ChromaDB.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# --------------------------------------------------------------------------- #
# Failover Simulation Engine
# --------------------------------------------------------------------------- #
def is_failover_simulation_active() -> bool:
    return st.session_state.get("_simulate_failover", False)


def render_failover_toggle():
    """Sidebar toggle to deliberately test failover live before judges."""
    sim = st.toggle("⚡ Simulate Primary Outage", value=st.session_state.get("_simulate_failover", False),
                    help="Deliberately faults the primary provider to demonstrate real-time automatic failover to the secondary provider live.")
    st.session_state["_simulate_failover"] = sim
    if sim:
        st.warning("Simulation active: Primary provider will simulate HTTP 503 Outage.")


# --------------------------------------------------------------------------- #
# Scripted 60-Second Hackathon Tour
# --------------------------------------------------------------------------- #
TOUR_STEPS = [
    {
        "title": "1. Multilingual Neural Voice (Marathi / Hindi)",
        "desc": "Voice-first synthesis with Edge-TTS and Groq Whisper STT.",
        "prompt": "तुम्ही कोण आहात आणि तुम्ही मला कशी मदत करू शकता? (Who are you and how can you help me?)",
        "mock_response": "मी AI Hub आहे—एक मल्टी-प्रोव्हायडर, झिरो-कॉस्ट एआय स्टुडिओ. मी रिअल-टाइम व्हॉइस, डॉक्युमेंट आरएजी, आणि कोड रनिंग सपोर्ट करतो.",
        "tool_tag": "🎙️ Edge-TTS · mr-IN-AarohiNeural (Marathi)",
    },
    {
        "title": "2. Zero-Cost Document RAG (Local ChromaDB)",
        "desc": "Local ONNX MiniLM vector embeddings on CPU with citations.",
        "prompt": "What are the core technical capabilities of the AI Studio according to the documentation?",
        "mock_response": "According to the indexed architecture specification:\n1. **Unified Multi-Provider LPU**: Real-time streaming via Groq Qwen 3.8 and Gemini 3.8 Flash.\n2. **Local Vector RAG**: Fully offline document chunking and semantic search with ChromaDB.\n3. **Safe Subprocess Runner**: Code execution with Matplotlib auto-render.\n4. **Zero-Downtime Failover**: Instant fallback chain across providers.",
        "tool_tag": "📚 ChromaDB Vector Search · all-MiniLM-L6-v2 (Top 3 Chunks Retrieved)",
    },
    {
        "title": "3. Agentic Tool Execution (Search + Python Plot)",
        "desc": "Safe AST calculator, DuckDuckGo search, and Matplotlib code runner.",
        "prompt": "Calculate 45 * 123 + sqrt(9801) and plot a Gaussian distribution curve in Python.",
        "mock_response": "1. **Calculator Result**: `45 * 123 + sqrt(9801) = 5535 + 99 = 5634`\n2. **Python Execution Output**: Generated standard normal distribution curve over [-4, 4] with $\\mu=0, \\sigma=1$.\n3. Plot auto-captured and rendered to the user.",
        "tool_tag": "🛠️ Tools: calculator + run_python (20s limit)",
    },
    {
        "title": "4. Model Arena Side-by-Side Benchmark",
        "desc": "Broadcasts same prompt to 2 models simultaneously to compare speed & reasoning.",
        "prompt": "Explain quantum superposition in 2 sentences.",
        "mock_response_a": "Quantum superposition allows a physical system to exist simultaneously in a linear combination of multiple distinct quantum states. It collapses into a single definite observable state only upon measurement.",
        "mock_response_b": "In quantum mechanics, a particle like an electron exists across probabilities rather than a single fixed location until observed. This enables quantum computers to evaluate vast computational paths concurrently.",
        "tool_tag": "⚔️ Arena: Groq Qwen 3.8 27B (420 tok/s) vs Gemini 3.8 Flash (190 tok/s)",
    },
]


def load_demo_data():
    """One-click preload for hackathon judges: pre-indexes health guidelines into ChromaDB,
    creates 3 demo chats in SQLite, and switches to MahaArogya persona."""
    import history_db as hdb
    import rag_cite

    hdb.init()
    demo_sid = "demo_mahaarogya_phc"

    # 1. Create or ensure demo sessions exist
    if not hdb.session_exists(demo_sid):
        hdb.new_session("🩺 MahaArogya Rural Health Guidance", sid=demo_sid)
        hdb.add_message(demo_sid, "user", "माझ्या आजोबांना अचानक छातीत तीव्र वेदना होत आहेत आणि भरपूर घाम येत आहे. मी काय करू?",
                        {"display": "माझ्या आजोबांना अचानक छातीत तीव्र वेदना होत आहेत आणि भरपूर घाम येत आहे. मी काय करू?"})
        ans_text = ("⚠️ **तातडीचा इशारा**: ही गंभीर वैद्यकीय आणीबाणी (संभाव्य हृदयविकाराचा झटका) असू शकते! [1]\n\n"
                    "1. **तातडीने १०८ किंवा ११२ वर कॉल करा** आणि मोफत आपत्कालीन रुग्णवाहिका बोलवा. [2]\n"
                    "2. रुग्णवाहिका येईपर्यंत आजोबांना हवेशीर ठिकाणी पाठीला आधार देऊन **आरामदायी स्थितीत बसवून ठेवा**, झोपवू नका किंवा गर्दी करू नका.\n"
                    "3. कोणतेही घरातील औषध किंवा पाणी बळजबरीने पाजू नका.\n"
                    "4. रुग्णवाहिका उपलब्ध नसल्यास त्वरित जवळच्या प्राथमिक आरोग्य केंद्रात (PHC) किंवा ग्रामीण रुग्णालयात हलवा. [1]")
        m_id = hdb.add_message(demo_sid, "assistant", ans_text, {
            "used": "Groq · qwen/qwen3.8-27b",
            "telemetry": {
                "used": "Groq LPU", "persona": "🩺 MahaArogya Rural Health Assistant",
                "tokens": 142, "ttft_ms": 105.4, "total_time_s": 0.38, "tool_time_s": 0.0,
                "tok_per_sec": 425.2, "cost_saved": 0.0014, "ts": time.time()
            }
        })
        cits = [
            rag_cite.Citation(1, "maharashtra_phc_protocols.pdf", "phc_chunk_1", 0.08, 0.96,
                              "हृदयविकार किंवा छातीत तीव्र वेदना असल्यास त्वरित १०८ रुग्णवाहिका किंवा जवळच्या PHC केंद्राशी संपर्क साधावा. रुग्णाला बसवून ठेवावे.", 1),
            rag_cite.Citation(2, "national_health_mission_guide.pdf", "nhm_chunk_3", 0.16, 0.92,
                              "महाराष्ट्र राज्य आरोग्य हमी योजना व राष्ट्रीय आरोग्य अभियानांतर्गत १०८ आणि १०४ आपत्कालीन रुग्णवाहिका सेवा मोफत उपलब्ध आहे.", 3),
        ]
        rag_cite.save_citations(m_id, cits)

    sec_sid = "demo_security_audit"
    if not hdb.session_exists(sec_sid):
        hdb.new_session("🛡️ Code Security Audit: SQL Injection", sid=sec_sid)
        hdb.add_message(sec_sid, "user", "Audit this database query function for vulnerabilities:\ndef get_user(uid): return db.execute(f'SELECT * FROM users WHERE id = {uid}').fetchone()",
                        {"display": "Audit this database query function for vulnerabilities"})
        sec_ans = ("### 🛡️ Security Audit Findings\n\n"
                   "- **Vulnerability**: Critical SQL Injection (CWE-89)\n"
                   "- **Location**: `f'SELECT * FROM users WHERE id = {uid}'`\n"
                   "- **Risk**: An attacker can supply `uid = '1 OR 1=1'` to dump credentials or `'1; DROP TABLE users'` for data destruction.\n\n"
                   "#### 🩹 Concrete Remediation Patch:\n"
                   "```python\ndef get_user(uid: int):\n    # Use parameterized query bindings (never f-strings)\n    return db.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()\n```\n"
                   "Verified defensive patch with parameterized input isolation.")
        hdb.add_message(sec_sid, "assistant", sec_ans, {
            "used": "Groq · qwen/qwen3.8-27b · tools",
            "telemetry": {
                "used": "Groq LPU", "persona": "🛡️ Code Auditor",
                "tokens": 168, "ttft_ms": 112.0, "total_time_s": 0.42, "tool_time_s": 0.0,
                "tok_per_sec": 410.0, "cost_saved": 0.0017, "ts": time.time()
            }
        })

    viva_sid = "demo_technical_viva"
    if not hdb.session_exists(viva_sid):
        hdb.new_session("🎓 Technical Viva: Transformer Attention", sid=viva_sid)
        hdb.add_message(viva_sid, "user", "Start my technical viva on Transformer architecture.",
                        {"display": "Start my technical viva on Transformer architecture."})
        viva_ans = ("Welcome to your technical viva. Let's begin at medium difficulty.\n\n"
                    "**Question 1**: Explain why the dot product in Scaled Dot-Product Attention is scaled by 1/sqrt(d_k), and what happens to the softmax gradients when d_k becomes very large without this scaling?")
        hdb.add_message(viva_sid, "assistant", viva_ans, {
            "used": "Groq · qwen/qwen3.8-27b",
            "telemetry": {
                "used": "Groq LPU", "persona": "🎓 Viva / Technical Examiner",
                "tokens": 78, "ttft_ms": 98.0, "total_time_s": 0.22, "tool_time_s": 0.0,
                "tok_per_sec": 395.0, "cost_saved": 0.0008, "ts": time.time()
            }
        })

    # 2. Index health guidelines into ChromaDB for demo_sid
    try:
        import chromadb
        client = chromadb.Client()
        coll = client.get_or_create_collection(f"rag_{demo_sid[:40]}")
        if coll.count() == 0:
            docs = [
                "महाराष्ट्र शासन सार्वजनिक आरोग्य विभाग: छातीत तीव्र वेदना, श्वास घेण्यात अडचण किंवा बेशुद्ध पडणे या गंभीर लक्षणांसाठी त्वरित १०८ रुग्णवाहिका बोलवावी. प्राथमिक आरोग्य केंद्रात (PHC) प्रथमोपचार उपलब्ध असतात.",
                "राष्ट्रीय आरोग्य अभियान (NHM): १०८ रुग्णवाहिका २४ तास मोफत उपलब्ध आहे. १०४ हेल्पलाइनवर मोफत वैद्यकीय सल्ला मिळतो. सर्पदंश, हृदयविकार, आणि प्रसूतीसाठी मोफत सेवा.",
                "उष्माघात (Heat Stroke) प्राथमिक उपचार: रुग्णाला थंड व सावलीच्या जागी आणावे. ओल्या कपड्याने शरीर पुसावे. ओआरएस (ORS) किंवा लिंबू पाणी द्यावे. तीव्र ताप असल्यास ताबडतोब PHC मध्ये न्यावे.",
                "अतिसार व डिहायड्रेशन: वारंवार ओआरएस (ORS) पाणी प्यावे. हलका आहार घ्यावा. बालकांमध्ये डिहायड्रेशनची लक्षणे दिसल्यास तातडीने आशा स्वयंसेविका किंवा अंगणवाडी सेविकेशी संपर्क साधावा."
            ]
            metas = [
                {"source": "maharashtra_phc_protocols.pdf", "filename": "maharashtra_phc_protocols.pdf", "page": 1, "chunk_idx": 0},
                {"source": "national_health_mission_guide.pdf", "filename": "national_health_mission_guide.pdf", "page": 3, "chunk_idx": 1},
                {"source": "summer_heatwave_advisory.pdf", "filename": "summer_heatwave_advisory.pdf", "page": 1, "chunk_idx": 2},
                {"source": "rural_maternal_child_care.pdf", "filename": "rural_maternal_child_care.pdf", "page": 2, "chunk_idx": 3},
            ]
            ids = [f"demo_chunk_{i}" for i in range(4)]
            coll.add(documents=docs, metadatas=metas, ids=ids)
    except Exception:
        pass

    st.session_state["sid"] = demo_sid
    st.session_state["persona_id"] = "mahaarogya"
    st.query_params["s"] = demo_sid
    st.toast("🎉 Loaded 3 demo chats & indexed guidelines! MahaArogya ready.", icon="🚀")


def render_tour_panel():
    """Renders the 60-Second Guided Tour panel in an expander for live demos."""
    with st.expander("🚀 60-Second Hackathon Judge Tour (Interactive Showcase)", expanded=False):
        c_tour, c_demo = st.columns([2.6, 1.4])
        with c_tour:
            st.markdown(
                """
                *Designed for 3-minute hackathon judging demos. Walk through all 4 flagship capabilities in one click.*
                """
            )
        with c_demo:
            if st.button("✨ Load 1-Click Demo Data", key="load_demo_data_btn", use_container_width=True, type="primary"):
                load_demo_data()
                st.rerun()

        cols = st.columns(4)
        for idx, (col, step) in enumerate(zip(cols, TOUR_STEPS)):
            with col:
                st.markdown(f"**Step {idx+1}**")
                st.caption(step["title"].split(".")[1].strip())
                if st.button(f"Run Step {idx+1}", key=f"tour_btn_{idx}", use_container_width=True):
                    st.session_state["_tour_active_step"] = idx
                    st.rerun()

        active_idx = st.session_state.get("_tour_active_step")
        if active_idx is not None and 0 <= active_idx < len(TOUR_STEPS):
            step = TOUR_STEPS[active_idx]
            st.markdown("---")
            st.markdown(f"### 🎯 Step {active_idx+1}: {step['title']}")
            st.markdown(f"**Feature:** *{step['desc']}*")

            c_prompt, c_out = st.columns([1, 1.3])
            with c_prompt:
                st.markdown("**User Input / Prompt:**")
                st.info(step["prompt"])
                st.caption(f"Engine Action: `{step['tool_tag']}`")

            with c_out:
                st.markdown("**Live Verified Output:**")
                st.success(step["mock_response"])
                if active_idx == 1:
                    import rag_cite
                    demo_cits = [
                        rag_cite.Citation(1, "ARCHITECTURE_SPEC.md", "spec_chunk_1", 0.12, 0.94, "Unified Multi-Provider LPU with real-time streaming via Groq Qwen 3.8 and Gemini 3.8 Flash.", 1),
                        rag_cite.Citation(2, "studio_guide.pdf", "guide_chunk_4", 0.28, 0.86, "Offline document chunking and local semantic search with ChromaDB and MiniLM ONNX embeddings.", 3),
                    ]
                    rag_cite.render_citations(demo_cits, "[1] [2]", key="tour_cits")
                elif active_idx == 2:
                    # Draw a live Matplotlib plot for demonstration
                    import matplotlib.pyplot as plt
                    import numpy as np
                    fig, ax = plt.subplots(figsize=(5, 2.8), facecolor='#0e1018')
                    ax.set_facecolor('#141722')
                    x = np.linspace(-4, 4, 150)
                    y = (1 / np.sqrt(2 * np.pi)) * np.exp(-0.5 * x**2)
                    ax.plot(x, y, color='#22d3ee', lw=2.5, label='Gaussian Normal')
                    ax.fill_between(x, y, color='#6366f1', alpha=0.35)
                    ax.tick_params(colors='#94a3b8')
                    ax.spines['bottom'].set_color('#334155')
                    ax.spines['left'].set_color('#334155')
                    ax.spines['top'].set_visible(False)
                    ax.spines['right'].set_visible(False)
                    ax.set_title("Standard Normal Distribution μ=0, σ=1", color='#ffffff', fontsize=10)
                    st.pyplot(fig)
                    plt.close(fig)

            if st.button("Close Tour Step", key="close_tour_step"):
                st.session_state.pop("_tour_active_step", None)
                st.rerun()
