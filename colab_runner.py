# Colab (T4 or CPU runtime). One cell:
#   !python colab_runner.py
# Paste the printed PY_RUNNER_URL into your .env or AI Hub settings.
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = int(os.getenv("PORT", "8000"))
TOKEN = os.getenv("PY_RUNNER_TOKEN", "")

# Install cloudflared tunnel
subprocess.run("wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O cloudflared && chmod +x cloudflared", shell=True)

class RunnerHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/run":
            self.send_response(404)
            self.end_headers()
            return

        if TOKEN:
            auth = self.headers.get("X-Token", "")
            if auth != TOKEN:
                self.send_response(401)
                self.end_headers()
                return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        try:
            data = json.loads(body)
            code = data.get("code", "")
        except Exception as e:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())
            return

        # Execute code in temp directory
        tmp = tempfile.mkdtemp(prefix="colab_run_")
        t0 = time.time()
        try:
            with open(os.path.join(tmp, "user.py"), "w", encoding="utf-8") as f:
                f.write(code)
            with open(os.path.join(tmp, "runner.py"), "w", encoding="utf-8") as f:
                f.write(r'''
import atexit, os, runpy, sys
os.environ["MPLBACKEND"] = "Agg"
_n = [0]
def _save():
    try:
        import matplotlib.pyplot as plt
        for num in plt.get_fignums():
            plt.figure(num).savefig("out_%d.png" % _n[0], dpi=110, bbox_inches="tight"); _n[0] += 1
        plt.close("all")
    except Exception:
        pass
try:
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as _plt
    _plt.show = lambda *a, **k: _save()
except Exception:
    pass
atexit.register(_save)
runpy.run_path("user.py", run_name="__main__")
''')
            env = {**os.environ, "MPLBACKEND": "Agg"}
            so_file = open(os.path.join(tmp, "stdout.txt"), "wb")
            se_file = open(os.path.join(tmp, "stderr.txt"), "wb")
            p = subprocess.Popen([sys.executable, "runner.py"], cwd=tmp, env=env, stdout=so_file, stderr=se_file)
            timed_out = False
            try:
                p.wait(timeout=30)
            except subprocess.TimeoutExpired:
                timed_out = True
                p.kill()
                p.wait()
            so_file.close()
            se_file.close()

            out = open(os.path.join(tmp, "stdout.txt"), "rb").read()
            err = open(os.path.join(tmp, "stderr.txt"), "rb").read()
            import base64, glob
            images = []
            for img_path in sorted(glob.glob(os.path.join(tmp, "out_*.png")))[:4]:
                raw = open(img_path, "rb").read()
                images.append("data:image/png;base64," + base64.b64encode(raw).decode())

            resp_payload = {
                "ok": p.returncode == 0 and not timed_out,
                "stdout": out[:6000].decode("utf-8", "replace"),
                "stderr": err[:3000].decode("utf-8", "replace"),
                "images": images,
                "timed_out": timed_out,
                "seconds": round(time.time() - t0, 2)
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp_payload).encode())
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

# Start background Cloudflare tunnel
log = open("tunnel.log", "w")
subprocess.Popen(
    ["./cloudflared", "tunnel", "--url", f"http://localhost:{PORT}"],
    stdout=log, stderr=log,
)

url = None
for _ in range(60):
    time.sleep(1)
    if os.path.exists("tunnel.log"):
        m = re.search(r"https://[-a-z0-9]+\.trycloudflare\.com", open("tunnel.log").read())
        if m:
            url = m.group(0)
            break

print("\n" + "=" * 55)
print("PY_RUNNER_URL   :", url or "tunnel failed - see tunnel.log")
print("PY_RUNNER_TOKEN :", TOKEN or "(none)")
print("=" * 55, flush=True)

server = HTTPServer(("0.0.0.0", PORT), RunnerHandler)
print(f"Server listening on port {PORT}...")
server.serve_forever()
