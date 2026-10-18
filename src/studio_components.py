"""
studio_components.py - Pure HTML builders for GetLayers-Grade UI & Visual Elements.
Every function returns a clean HTML string to be rendered with ui(markup).
"""
from __future__ import annotations
from html import escape as _esc
from typing import Iterable, Sequence

def esc(v) -> str:
    return _esc(str(v), quote=True)

def fx_flags(lite: bool) -> str:
    """Marker that JS/CSS read to switch off cursor, aurora and canvas."""
    return f'<span id="fx-flags" data-lite="{1 if lite else 0}" hidden></span>'

def brand_html() -> str:
    """Authentic cyberpunk anime mecha emblem and typography for sidebar."""
    return """
    <div class="brand">
      <div class="brand-mark">
        <svg width="26" height="26" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
          <!-- Cyber Hex Shield -->
          <polygon points="16,2 30,9 30,23 16,30 2,23 2,9" fill="#0b0e18" stroke="#6366f1" stroke-width="1.5"/>
          <!-- Mecha Crown V-Fin -->
          <polygon points="16,6 10,2 9,4 15,8" fill="#f43f5e"/>
          <polygon points="16,6 22,2 23,4 17,8" fill="#f43f5e"/>
          <!-- Core Power Gem -->
          <polygon points="16,7 18,9 18,11 16,13 14,11 14,9" fill="#22d3ee" stroke="#ffffff" stroke-width="0.8"/>
          <!-- Slanted Anime Visor Eyes -->
          <polygon points="9,14 14,15 13.5,17 9.5,16" fill="#22d3ee"/>
          <polygon points="23,14 18,15 18.5,17 22.5,16" fill="#22d3ee"/>
          <!-- Mecha Faceplate & Slits -->
          <polygon points="11,18 21,18 19,25 16,27 13,25" fill="#151928" stroke="#818cf8" stroke-width="0.8"/>
          <line x1="14" y1="20" x2="18" y2="20" stroke="#22d3ee" stroke-width="0.8"/>
          <line x1="14.5" y1="22" x2="17.5" y2="22" stroke="#6366f1" stroke-width="0.8"/>
          <!-- Chin Accent -->
          <polygon points="15,26 17,26 16,28.5" fill="#f43f5e"/>
        </svg>
      </div>
      <div>
        <div class="brand-name">AI Hub</div>
        <div class="brand-sub">Multi-model prototyping • 0% GPU load</div>
      </div>
    </div>
    """

def hero_html(providers: Sequence[tuple[str, bool]], pills_html: str = "") -> str:
    """Hero banner with rotating conic border beam, constellation canvas, rolling ticker,
    and celestial orbital rings representing live cloud providers."""
    classes = ["g", "q", "f", "r", "o"]
    rings = ["", "r2", "r3", "r4", "r5"]
    orbit = ""
    for i, (label, ok) in enumerate(list(providers)[:4]):
        ring_cls = rings[i] if i < len(rings) else ""
        node_cls = classes[i] if i < len(classes) else "g"
        orbit += (
            f'<div class="hx-ring {ring_cls}">'
            f'<span class="hx-node {node_cls} {"" if ok else "off"}" '
            f'title="{esc(label)}: {"Connected" if ok else "Needs API Key"}"></span>'
            f'</div>'
        )

    phrases = [
        "Write the winning pitch",
        "Synthesize the architecture",
        "Audit screens & documents",
        "Generate 1024px visuals & 30s video",
        "DeepSeek-R1 & Llama 3.3 Free"
    ]
    ticker = "".join(f"<span>{esc(p)}</span>" for p in phrases + phrases[:1])

    star_svg = """
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 2C12 7.52285 7.52285 12 2 12C7.52285 12 12 16.4772 12 22C12 16.4772 16.4772 12 22 12C16.4772 12 12 7.52285 12 2Z" fill="url(#starGrad)"/>
      <defs>
        <linearGradient id="starGrad" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
          <stop stop-color="#ffffff"/>
          <stop offset="0.5" stop-color="#38bdf8"/>
          <stop offset="1" stop-color="#6366f1"/>
        </linearGradient>
      </defs>
    </svg>
    """

    return f"""
    <section class="hx-wrap hx-in">
      <div class="hx-slot" id="fx-hero-slot"></div>
      <div class="hx-copy">
        <div class="hx-chip">
          <span class="dot live"></span>Cloud inference • 0% local GPU load
        </div>
        <div class="hx-title" role="heading" aria-level="1">Pitch it. Audit it. <span style="white-space:nowrap;">Render it.</span></div>
        <p class="hx-sub">High-velocity multimodal workspace for AI prototyping. 100% free cloud models (Gemini, Groq, OpenRouter DeepSeek-R1, FLUX & Multi-Scene Video) with zero card requirement.</p>
        <div class="hx-ticker"><div>{ticker}</div></div>
        <div class="hx-pills">{pills_html}</div>
      </div>
      <div class="hx-orbit">
        {orbit}
        <div class="hx-core"><b>{star_svg}</b></div>
      </div>
    </section>
    """

def gen_log(lines: Iterable[tuple[str, str]]) -> str:
    """Terminal-style event log."""
    body = "".join(f'<div class="{s if s in ("ok", "bad", "run") else ""}">{esc(t)}</div>' for s, t in lines)
    return f'<div class="gl">{body}</div>'

def provider_health_html(stats: dict) -> str:
    """Live provider telemetry cards."""
    if not stats:
        return '<div class="ph"><div class="cell"><b>All Systems Active</b><i>Cloud clusters healthy & ready</i></div></div>'
    cells = ""
    for name, s in stats.items():
        down = bool(s.get("cooling")) or (s.get("fail", 0) > 0 and s.get("ok", 0) == 0)
        ms = s.get("last_ms")
        latency = f'{ms:.2f}s' if isinstance(ms, (int, float)) else "Ready"
        cells += (
            f'<div class="cell {"down" if down else "up"}"><b>{esc(name)}</b>'
            f'<i>{s.get("status", "Active")} • {latency}</i></div>'
        )
    return f'<div class="ph">{cells}</div>'

def model_matrix_cards_html() -> str:
    """Curated showcase of the Best Free Cloud AI Models in 2026."""
    models = [
        {
            "cat": "Reasoning & Coding",
            "name": "OpenRouter DeepSeek-R1 & Llama 3.3",
            "badge": "671B MoE • Free Tier",
            "desc": "DeepSeek-R1 reasoning matching o1 + Meta Llama 3.3 70B. Zero payment, zero local GPU load.",
            "color": "var(--c-indigo)"
        },
        {
            "cat": "Multimodal LLM",
            "name": "Google Gemini 3.8 Flash",
            "badge": "1M Context • Free",
            "desc": "Official Google 2026 model. March 2026 cutoff, native multimodal reasoning, batch PDF/image auditing.",
            "color": "var(--c-cyan)"
        },
        {
            "cat": "Ultra-Fast LPU",
            "name": "Groq Qwen 3.8 (27B)",
            "badge": "600+ Tokens/Sec",
            "desc": "Hardware-accelerated LPU tensor inference. Instantaneous code generation and chat with sub-second time-to-first-token.",
            "color": "var(--c-mint)"
        },
        {
            "cat": "1024px Image",
            "name": "FLUX.1-schnell & Pollinations",
            "badge": "12B DiT • 4-Step",
            "desc": "Black Forest Labs state-of-the-art visual generator. Generates native 1024x1024 HD photorealism in ~3s with zero-token fallback.",
            "color": "var(--c-fuchsia)"
        },
        {
            "cat": "20-30s Motion Video",
            "name": "Multi-Scene Video Synthesizer",
            "badge": "20-30s Unlimited MP4",
            "desc": "Cinematic multi-scene storyboard director with smooth camera pans and cross-dissolve transitions. 100% free with 0% laptop GPU load.",
            "color": "var(--c-amber)"
        }
    ]

    cards_html = ""
    for m in models:
        cards_html += f"""
        <div class="filecard fx-card" style="display:flex; flex-direction:column; align-items:flex-start; padding:1.2rem; gap:0.4rem;">
          <div style="display:flex; justify-content:space-between; width:100%; align-items:center;">
            <span style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.06em; color:{m['color']}; font-weight:700;">{m['cat']}</span>
            <span class="chip" style="font-size:0.74rem;"><b>{m['badge']}</b></span>
          </div>
          <div style="font-size:1.05rem; font-weight:700; color:#ffffff; margin-top:2px;">{m['name']}</div>
          <div style="font-size:0.84rem; color:var(--muted); line-height:1.45;">{m['desc']}</div>
        </div>
        """
    return f'<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:1rem; margin-top:0.6rem;">{cards_html}</div>'
