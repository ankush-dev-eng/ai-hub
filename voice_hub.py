"""
voice_hub.py - Voice in/out for the AI Hub chat.

pip install edge-tts            # TTS (free, unofficial MS endpoint)
pip install faster-whisper      # optional local STT fallback (CPU)
Needs streamlit>=1.39 (st.audio_input). Mic needs HTTPS or localhost.

Public API:
    cfg   = voice_hub.sidebar()                 # settings in sidebar
    text  = voice_hub.mic_input(cfg)            # str | None  (put in dock toolbar)
    speaker = voice_hub.make_speaker(cfg, via_voice)   # streaming TTS; pass into run_chain
    voice_hub.speak(reply, cfg, via_voice)      # whole-reply fallback (non-streaming paths)
"""
import asyncio
import base64
import hashlib
import io
import json
import os
import re
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import streamlit.components.v1 as components

WHISPER_MODEL = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")  # edit if Groq renames it
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
def sidebar(default_voice: str | None = None) -> dict:
    sb = st.sidebar
    sb.markdown("### 🎙️ Voice")
    mode = sb.selectbox("Speak replies", MODES)
    v_keys = list(VOICES.keys())
    default_idx = 0
    if default_voice:
        for idx, k in enumerate(v_keys):
            if VOICES[k] == default_voice:
                default_idx = idx
                break
    voice = VOICES[sb.selectbox("Voice", v_keys, index=default_idx)]
    rate = sb.slider("Speed", -30, 50, 0, 5, format="%d%%")
    lang = LANGS[sb.selectbox("Speech language", list(LANGS.keys()))]
    if sb.button("🔇 Stop audio", use_container_width=True):
        _run_js("window.parent.__ttsq && window.parent.__ttsq.stop();")
    return {"mode": mode, "voice": voice, "rate": f"{rate:+d}%", "lang": lang}


def replay_audio(text: str, cfg: dict):
    """Enqueues audio playback for an existing message into the parent audio queue."""
    clean = speakable(text)
    if not clean:
        return
    voice = cfg.get("voice", "en-IN-NeerjaNeural")
    if re.search(r"[\u0900-\u097F]", clean) and not voice.startswith(("hi-", "mr-")):
        voice = "hi-IN-SwaraNeural"
    try:
        audio = synth(clean, voice, cfg.get("rate", "+0%"))
        b64 = base64.b64encode(audio).decode("ascii")
        _run_js(f"window.parent.__ttsq && window.parent.__ttsq.push('{b64}');")
    except Exception as e:
        st.toast(f"Audio replay failed: {str(e)[:60]}", icon="🔇")


def mic_input(cfg: dict):
    """Render recorder (put inside the dock toolbar). Returns transcript once per recording."""
    ss = st.session_state
    ss.setdefault("mic_n", 0)
    with st.popover("🎙️ Speak"):
        audio = st.audio_input("Click to record, click again to send", key=f"mic_{ss.mic_n}")
    if audio is None:
        return None
    data = audio.getvalue()
    h = hashlib.md5(data).hexdigest()
    if h == ss.get("mic_last"):
        return None
    ss.mic_last = h
    with st.spinner("Transcribing..."):
        text = transcribe(data, cfg["lang"])
    ss.mic_n += 1  # fresh widget key next run -> recorder resets, no re-send loop
    return text or None


# =====================================================================
# Sentence-level streaming TTS
# ---------------------------------------------------------------------
# Server: text deltas -> sentence splitter -> parallel edge-tts workers (ordered) -> base64 mp3.
# Client: a tiny player living in the PARENT window (survives Streamlit reruns/iframe
# teardown) plays clips back-to-back. Per-sentence st.audio(autoplay=True) would make
# every clip start at once, hence the queue.
# =====================================================================
PLAYER_SRC = """(function(){var q=[],cur=null;
function next(){if(cur||!q.length)return;var a=new Audio(q.shift());cur=a;
a.onended=a.onerror=function(){cur=null;next();};
var p=a.play();if(p&&p.catch)p.catch(function(){cur=null;q=[];window.__ttsq.blocked=true;});}
window.__ttsq={blocked:false,
add:function(s,r){if(r)this.stop();for(var i=0;i<s.length;i++)q.push(s[i]);next();},
stop:function(){q=[];if(cur){cur.onended=cur.onerror=null;cur.pause();cur=null;}}};})();"""

_ADD_HTML = ("<script>(function(){var P=window.parent;"
             "if(!P.__ttsq){var s=P.document.createElement('script');s.textContent=__PLAYER__;P.document.head.appendChild(s);}"
             "P.__ttsq.add(__SRCS__,__RESET__);})();</script>")


def _run_js(js: str):
    components.html(f"<script>{js}</script>", height=0)


def synth_raw(text: str, voice: str, rate: str) -> bytes:
    """Uncached, no Streamlit calls - safe in worker threads."""
    return asyncio.run(_synth(text, voice, rate))


def _pick_voice(clean: str, voice: str) -> str:
    if re.search(r"[\u0900-\u097F]", clean) and not voice.startswith(("hi-", "mr-")):
        return "hi-IN-SwaraNeural"
    return voice


class NullSpeaker:
    def feed(self, delta): pass
    def flush(self): pass
    def restart(self): pass
    def close(self): pass


class SentenceSpeaker:
    FIRST_MIN = 20     # chars before the FIRST clip may be cut (low = faster first audio)
    NEXT_MIN = 45      # later clips are longer -> smoother prosody
    FORCE_CUT = 240    # no punctuation for this long -> cut at a comma/space
    MAX_CHARS = 1400   # stop speaking after this many chars (edge-tts + patience)

    def __init__(self, cfg, synth_fn=None, emit_fn=None):
        self.cfg = cfg
        self.synth = synth_fn or synth_raw
        self._emit_fn = emit_fn or self._emit_default
        self.pool = ThreadPoolExecutor(3)
        self.q = deque()          # futures, in sentence order
        self.buf = ""
        self.sent = 0
        self.chars = 0
        self.started = False
        self.err = None
        self._sink = None

    # ---- public ----
    def feed(self, delta: str):
        self.buf += delta
        self._pump(final=False)
        self._drain(wait=False)

    def flush(self):
        self._pump(final=True)
        self._drain(wait=True)
        self.pool.shutdown(wait=False)
        if self.err and not self.started:
            st.toast(f"TTS failed: {self.err[:70]}", icon="🔇")

    def restart(self):
        """Provider failed mid-stream: drop pending speech, silence what is playing."""
        for f in self.q:
            f.cancel()
        self.q.clear()
        self.buf, self.sent, self.chars = "", 0, 0
        if self.started:
            self._emit_fn([], True)
        self.started = False

    def close(self):
        self.pool.shutdown(wait=False, cancel_futures=True)

    # ---- internals ----
    def _pump(self, final: bool):
        buf = re.sub(r"```.*?```", "\n(code omitted)\n", self.buf, flags=re.S)
        buf = re.sub(r"<think>.*?</think>", "", buf, flags=re.S)
        cut = len(buf)
        for mark in ("```", "<think>"):          # unterminated block: hold it back
            i = buf.find(mark)
            if i != -1:
                cut = min(cut, i)
        head, held = buf[:cut], buf[cut:]
        if not final:                              # half-typed marker like "``" or "<thi"
            m = re.search(r"(`{1,2}|<(?:t|th|thi|thin|think)?)$", head)
            if m:
                head, held = head[: m.start()], head[m.start():] + held
        if final:
            held = ""
        segs, rest = self._split(head, final)
        self.buf = rest + held
        for s in segs:
            self._submit(s)

    def _split(self, head: str, final: bool):
        segs, start, n = [], 0, len(head)
        for k, ch in enumerate(head):
            if ch == "\n":
                end = k + 1
            elif ch in ".!?।" and k + 1 < n and head[k + 1].isspace():
                end = k + 1
            else:
                continue
            need = self.FIRST_MIN if (self.sent + len(segs)) == 0 else self.NEXT_MIN
            if len(speakable(head[start:end], 10**6)) >= need:   # also merges "1." / "e.g."
                segs.append(head[start:end])
                start = end
        rest = head[start:]
        if not final and len(rest) > self.FORCE_CUT:
            j = max(rest.rfind(", "), rest.rfind("; "), rest.rfind(": "))
            if j <= 60:
                j = rest.rfind(" ")
            if j > 60:
                segs.append(rest[: j + 1])
                rest = rest[j + 1:]
        if final and rest.strip():
            segs.append(rest)
            rest = ""
        return segs, rest

    def _submit(self, seg: str):
        clean = speakable(seg, 10**6)
        if not clean or self.chars >= self.MAX_CHARS:
            return
        self.chars += len(clean)
        self.sent += 1
        voice = _pick_voice(clean, self.cfg["voice"])
        self.q.append(self.pool.submit(self.synth, clean, voice, self.cfg["rate"]))

    def _drain(self, wait: bool):
        ready = []
        while self.q and (wait or self.q[0].done()):   # strictly in order
            f = self.q.popleft()
            try:
                b = f.result(timeout=25)
            except Exception as e:
                self.err = str(e)
                continue
            if b:
                ready.append(b)
        if ready:
            self._emit_fn(ready, not self.started)
            self.started = True

    def _emit_default(self, blobs, reset):
        if self._sink is None:
            self._sink = st.container(key=f"tts_sink_{uuid.uuid4().hex[:8]}")
        srcs = ["data:audio/mp3;base64," + base64.b64encode(b).decode() for b in blobs]
        html = (_ADD_HTML.replace("__PLAYER__", json.dumps(PLAYER_SRC))
                         .replace("__SRCS__", json.dumps(srcs))
                         .replace("__RESET__", "true" if reset else "false"))
        with self._sink:
            components.html(html, height=0)


def make_speaker(cfg: dict, via_voice: bool = False):
    if cfg["mode"] == "Off" or (cfg["mode"] == MODES[0] and not via_voice):
        return NullSpeaker()
    return SentenceSpeaker(cfg)


def prune_tts_cache(max_files: int = 200):
    """Keep the TTS cache folder bounded."""
    import pathlib
    tts_dir = pathlib.Path(os.getenv("CHAT_DATA", "chat_data")) / "tts"
    if not tts_dir.exists():
        return
    files = sorted(tts_dir.glob("*.mp3"), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files[max_files:]:
        try:
            f.unlink(missing_ok=True)
        except Exception:
            pass

