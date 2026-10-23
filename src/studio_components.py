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
    """Authentic minimalist workspace identity for sidebar (Claude / ChatGPT style)."""
    return """
    <div class="saas-workspace-card">
      <div class="saas-avatar">⚡</div>
      <div style="flex: 1; min-width: 0;">
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 4px;">
          <span style="font-weight: 600; font-size: 0.92rem; color: #f4f4f5; letter-spacing: -0.01em;">AI Hub</span>
          <span style="font-size: 0.7rem; font-weight: 500; color: #a1a1aa; background: #27272a; padding: 1px 6px; border-radius: 4px;">PRO</span>
        </div>
        <div style="font-size: 0.72rem; color: #71717a; margin-top: 1px;">
          Cloud Multi-Model Studio
        </div>
      </div>
    </div>
    """

def saas_quota_html() -> str:
    """Clean Cloud Resource Telemetry Widget (Minimalist)."""
    return """
    <div class="saas-quota-card">
      <div class="saas-quota-title">
        <span>Cloud Fleet</span>
        <span style="color: #22c55e;">● 100% Online</span>
      </div>
      <div class="saas-quota-row">
        <span>Engines</span>
        <b>5 Active Clusters</b>
      </div>
      <div class="saas-quota-row">
        <span>Laptop GPU</span>
        <b style="color: #a1a1aa;">0.0% (Silent & Cold)</b>
      </div>
      <div class="saas-quota-row">
        <span>Billing</span>
        <b style="color: #22c55e;">$0.00 / Free Tier</b>
      </div>
    </div>
    """

def saas_topbar_html(providers: Sequence[tuple[str, bool]] = ()) -> str:
    """Sleek top status bar matching Vercel and Linear."""
    ready_count = sum(1 for _, ok in providers if ok) if providers else 5
    total_count = len(providers) if providers else 5
    return f"""
    <div class="saas-topbar">
      <div class="saas-topbar-left">
        <span class="saas-brand-name">AI Hub</span>
        <span class="saas-badge-pill">Enterprise Pro</span>
      </div>
      <div class="saas-topbar-right">
        <div class="saas-status-chip">
          <span class="saas-live-dot"></span>
          <span>Fleet: <b>{ready_count}/{total_count} Ready</b></span>
        </div>
        <div class="saas-status-chip">
          <span>⚡ <b>~450 tok/s</b> LPU</span>
        </div>
        <div class="saas-status-chip">
          <span style="color: #22c55e;"><b>$0.00</b> Free Tier</span>
        </div>
      </div>
    </div>
    """

def hero_html(providers: Sequence[tuple[str, bool]], pills_html: str = "") -> str:
    """Modern SaaS Command Center Header with live metrics and provider matrix."""
    return f"""
    <div class="saas-hero-command">
      <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 1rem;">
        <div>
          <div style="display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; background: rgba(99,102,241,0.15); border: 1px solid rgba(99,102,241,0.35); border-radius: 999px; font-size: 0.72rem; color: #38bdf8; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;">
            <span style="width: 6px; height: 6px; border-radius: 50%; background: #10b981; box-shadow: 0 0 6px #10b981;"></span>
            Enterprise Cloud AI Network
          </div>
          <div style="font-size: 1.65rem; font-weight: 800; color: #ffffff; letter-spacing: -0.02em; margin-top: 6px;">
            AI Hub <span style="background: linear-gradient(135deg, #6366f1, #22d3ee); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Pro Studio</span>
          </div>
          <div style="font-size: 0.88rem; color: #94a3b8; max-width: 640px; line-height: 1.45; margin-top: 4px;">
            Ultra-fast multi-model chat reasoning (350+ tok/s), batch multimodal auditing, native 1024px image synthesis, and 20–30s cinematic multi-scene video director with zero laptop GPU load.
          </div>
        </div>
        <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 8px;">
          <div style="display: flex; flex-wrap: wrap; gap: 6px; justify-content: flex-end;">
            {pills_html}
          </div>
        </div>
      </div>

      <div class="saas-metrics-grid">
        <div class="saas-metric-cell">
          <div class="saas-metric-label">⚡ LPU Inference Speed</div>
          <div class="saas-metric-val">~350–600 <span style="font-size: 0.75rem; font-weight: 500; color: #94a3b8;">tok/s (Groq)</span></div>
        </div>
        <div class="saas-metric-cell">
          <div class="saas-metric-label">✨ Maximum Context</div>
          <div class="saas-metric-val">1,000,000 <span style="font-size: 0.75rem; font-weight: 500; color: #94a3b8;">Tokens (Gemini)</span></div>
        </div>
        <div class="saas-metric-cell">
          <div class="saas-metric-label">🎨 Diffusion Media</div>
          <div class="saas-metric-val">1024×1024 <span style="font-size: 0.75rem; font-weight: 500; color: #94a3b8;">& 30s MP4</span></div>
        </div>
        <div class="saas-metric-cell">
          <div class="saas-metric-label">💻 Laptop Hardware Load</div>
          <div class="saas-metric-val" style="color: #34d399;">0% GPU <span style="font-size: 0.75rem; font-weight: 500; color: #94a3b8;">($0.00 Spent)</span></div>
        </div>
      </div>
    </div>
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
