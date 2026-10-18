# Colab (T4 runtime). One cell:
#   MODEL = "qwen2.5:7b"   # or llama3.1:8b, deepseek-r1:8b, gemma2:9b, phi3:medium ...
#   !MODEL=$MODEL python colab_llm_server.py
# Paste the printed Base URL + model into the AI Hub sidebar -> "Add endpoint".
# Run one copy of this per Colab account/notebook to get multiple endpoints.
import os
import re
import subprocess
import time

MODEL = os.getenv("MODEL", "qwen2.5:7b")


def sh(cmd):
    return subprocess.run(cmd, shell=True, check=False)


sh("apt-get -qq install -y zstd")
sh("curl -fsSL https://ollama.com/install.sh | sh")

env = {**os.environ, "OLLAMA_HOST": "0.0.0.0:11434", "OLLAMA_ORIGINS": "*"}
subprocess.Popen(["ollama", "serve"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(6)
sh(f"ollama pull {MODEL}")

sh("wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O cloudflared && chmod +x cloudflared")
log = open("tunnel.log", "w")
subprocess.Popen(
    ["./cloudflared", "tunnel", "--url", "http://localhost:11434", "--http-host-header", "localhost:11434"],
    stdout=log, stderr=log,
)

url = None
for _ in range(60):
    time.sleep(1)
    m = re.search(r"https://[-a-z0-9]+\.trycloudflare\.com", open("tunnel.log").read())
    if m:
        url = m.group(0)
        break

print("\n" + "=" * 50)
print("Base URL :", f"{url}/v1" if url else "tunnel failed - see tunnel.log")
print("Model    :", MODEL)
print("API key  : (leave blank)")
print("=" * 50, flush=True)

while True:  # keep the cell alive
    time.sleep(60)
