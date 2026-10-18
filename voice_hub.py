"""
voice_hub.py - Voice in/out for the AI Hub chat.

STT: Groq Whisper (whisper-large-v3-turbo) with automatic fallback to local faster-whisper on CPU.
TTS: Edge-TTS (free, Microsoft Neural voices: Indian English, Hindi, Marathi, US English).
No re-send loop: Hashes recordings and rotates widget keys on completion.
"""
import asyncio
import hashlib
import io
import os
import re
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
load_dotenv()

import streamlit as st

WHISPER_MODEL = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")
LOCAL_WHISPER = os.getenv("LOCAL_WHISPER", "small")

VOICES = {
    "English (India) - Neerja": "en-IN-NeerjaNeural",
    "English (India) - Prabhat": "en-IN-PrabhatNeural",
    "Hindi - Swara": "hi-IN-SwaraNeural",
    "Marathi - Aarohi": "mr-IN-AarohiNeural",
    "English (US) - Aria": "en-US-AriaNeural",
    "English (US) - Guy": "en-US-GuyNeural",
}
LANGS = {"Auto-detect": None, "English": "en", "Hindi": "hi", "Marathi": "mr"}
MODES = ["Only after voice input", "Always", "Off"]


# ---------- STT ----------
@st.cache_resource(show_spinner="Loading local Whisper...")
def _local_model():
    from faster_whisper import WhisperModel
    return WhisperModel(LOCAL_WHISPER, device="cpu", compute_type="int8")


def transcribe(audio: bytes, lang=None) -> str:
    key = os.getenv("GROQ_API_KEY")
    if key:
        try:
            from openai import OpenAI
            c = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=key, timeout=30)
            kw = {"language": lang} if lang else {}
            r = c.audio.transcriptions.create(
                model=WHISPER_MODEL, file=("speech.wav", audio, "audio/wav"),
                response_format="text", **kw,
            )
            return (r if isinstance(r, str) else getattr(r, "text", "")).strip()
        except Exception as e:
            st.toast(f"Groq STT failed ({str(e)[:60]}) - using local Whisper", icon="⚠️")
    try:
        segs, _ = _local_model().transcribe(io.BytesIO(audio), language=lang, vad_filter=True)
        return " ".join(s.text.strip() for s in segs).strip()
    except Exception as e:
        st.error(f"STT unavailable: {e}")
        return ""


# ---------- TTS ----------
def speakable(t: str, limit: int = 900) -> str:
    t = re.sub(r"<think>.*?</think>", " ", t, flags=re.S)
    t = re.sub(r"```.*?```", " (code omitted) ", t, flags=re.S)
    t = re.sub(r"`([^`]*)`", r"\1", t)
    t = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"^\s{0,3}(#{1,6}|>|[-*+]|\d+\.)\s+", "", t, flags=re.M)
    t = re.sub(r"[*_~|]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > limit:
        cut = t[:limit]
        end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "), cut.rfind("। "))
        t = cut[: end + 1] if end > 200 else cut
    return t


async def _synth(text, voice, rate):
    import edge_tts
    buf = bytearray()
    async for ch in edge_tts.Communicate(text, voice, rate=rate).stream():
        if ch["type"] == "audio":
            buf += ch["data"]
    return bytes(buf)


@st.cache_data(show_spinner=False, max_entries=64)
def synth(text: str, voice: str, rate: str) -> bytes:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_synth(text, voice, rate))
    with ThreadPoolExecutor(1) as ex:  # a loop is already running in this thread
        return ex.submit(lambda: asyncio.run(_synth(text, voice, rate))).result()


def speak(text: str, cfg: dict, via_voice: bool = False):
    if cfg["mode"] == "Off" or (cfg["mode"] == MODES[0] and not via_voice):
        return
    clean = speakable(text)
    if not clean:
        return
    voice = cfg["voice"]
    if re.search(r"[\u0900-\u097F]", clean) and not voice.startswith(("hi-", "mr-")):
        voice = "hi-IN-SwaraNeural"  # Devanagari text with an English voice reads as garbage
    try:
        audio = synth(clean, voice, cfg["rate"])
        st.audio(audio, format="audio/mp3", autoplay=True)
    except Exception as e:
        st.toast(f"TTS failed: {str(e)[:70]}", icon="🔇")


# ---------- UI ----------
def sidebar() -> dict:
    sb = st.sidebar
    sb.markdown("### 🎙️ Voice Settings")
    mode = sb.selectbox("Speak replies", MODES, key="vh_mode")
    voice = VOICES[sb.selectbox("Voice", list(VOICES.keys()), key="vh_voice")]
    rate = sb.slider("Speed", -30, 50, 0, 5, format="%d%%", key="vh_rate")
    lang = LANGS[sb.selectbox("Speech language", list(LANGS.keys()), key="vh_lang")]
    return {"mode": mode, "voice": voice, "rate": f"{rate:+d}%", "lang": lang}


def mic_input(cfg: dict):
    """Render recorder. Returns transcript once per recording."""
    ss = st.session_state
    ss.setdefault("mic_n", 0)
    with st.popover("🎙️ Voice Input", use_container_width=True):
        audio = st.audio_input("Record message (click to stop & send)", key=f"mic_{ss.mic_n}")
    if audio is None:
        return None
    data = audio.getvalue()
    h = hashlib.md5(data).hexdigest()
    if h == ss.get("mic_last"):
        return None
    ss.mic_last = h
    with st.spinner("Transcribing with Whisper..."):
        text = transcribe(data, cfg["lang"])
    ss.mic_n += 1  # fresh widget key next run -> recorder resets, no re-send loop
    return text or None
