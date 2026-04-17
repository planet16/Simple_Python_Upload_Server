#!/usr/bin/env python3
import cgi, html, sys, time, os, socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime, timezone

UPLOAD_DIR  = Path.home() / "CHANGE_ME'"   # Change this to the local folder location
PORT        = 8080                         # Change to any port you want
LOG_FILE    = UPLOAD_DIR / "access.log"
CHUNK_SIZE  = 1024 * 1024       # 1MB read chunks
MAX_SIZE_MB = 2048               # 2GB total POST limit — raise if needed
TIMEOUT_SEC = 300                # 5 min — enough for large batches on WiFi

FORM = b"""<!DOCTYPE html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font-family:-apple-system,sans-serif;max-width:500px;margin:60px auto;padding:20px}
input[type=submit]{background:#007aff;color:white;border:none;padding:12px 24px;border-radius:8px;font-size:1rem}
.note{color:#666;font-size:.85rem;margin-top:8px}</style>
<title>Upload</title></head><body>
<h2>Upload Photos</h2>
<form method="POST" enctype="multipart/form-data">
  <input type="file" name="photos" multiple accept="image/*,video/*"><br><br>
  <input type="submit" value="Upload">
</form>
<p class="note">Large batches are fine — be patient, page will reload when done.</p>
</body></html>"""

def w3c_header(f):
    f.write("#Version: 1.0\n")
    f.write(f"#Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("#Fields: date time c-ip cs-method cs-uri-stem sc-status "
            "sc-bytes cs-bytes time-taken cs(User-Agent) x-saved-files x-error\n")

class Handler(BaseHTTPRequestHandler):
    timeout = TIMEOUT_SEC

    def log_w3c(self, method, status, bytes_sent, bytes_recv, saved="", error=""):
        now     = datetime.now(timezone.utc)
        ua      = self.headers.get("User-Agent", "-").replace(" ", "+")
        elapsed = round((time.time() - self._start) * 1000)
        line    = (f"{now.strftime('%Y-%m-%d')}\t"
                   f"{now.strftime('%H:%M:%S')}\t"
                   f"{self.client_address[0]}\t"
                   f"{method}\t{self.path}\t{status}\t"
                   f"{bytes_sent}\t{bytes_recv}\t{elapsed}ms\t"
                   f"{ua}\t{saved or '-'}\t{error or '-'}")
        print(line)
        with open(LOG_FILE, "a") as f:
            if os.path.getsize(LOG_FILE) == 0:
                w3c_header(f)
            f.write(line + "\n")

    def log_request_headers(self):
        print(f"\n{'='*60}")
        print(f"REQUEST  {self.command} {self.path}")
        print(f"{'='*60}")
        for k, v in self.headers.items():
            print(f"  {k}: {v}")
        print()

    def do_GET(self):
        self._start = time.time()
        self.log_request_headers()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(FORM)))
        self.end_headers()
        self.wfile.write(FORM)
        self.log_w3c("GET", 200, len(FORM), 0)

    def do_POST(self):
        self._start  = time.time()
        ctype        = self.headers.get("Content-Type", "")
        clength      = int(self.headers.get("Content-Length", 0))
        self.log_request_headers()

        # Reject oversized requests early
        limit = MAX_SIZE_MB * 1024 * 1024
        if clength > limit:
            msg = f"Upload too large: {clength//1024//1024}MB exceeds {MAX_SIZE_MB}MB limit"
            print(f"REJECTED: {msg}")
            self._respond(413, msg)
            self.log_w3c("POST", 413, 0, clength, error=msg)
            return

        print(f"Receiving {clength/1024/1024:.1f} MB ...")

        try:
            form = cgi.FieldStorage(
                fp=self.rfile, headers=self.headers,
                environ={"REQUEST_METHOD": "POST",
                         "CONTENT_TYPE":   ctype,
                         "CONTENT_LENGTH": str(clength)})
        except Exception as e:
            self._respond(500, f"Parse error: {e}")
            self.log_w3c("POST", 500, 0, clength, error=str(e))
            return

        saved, errors = [], []
        items = form["photos"] if "photos" in form else []
        if not isinstance(items, list):
            items = [items]

        total = len(items)
        for i, item in enumerate(items, 1):
            if not hasattr(item, "filename") or not item.filename:
                continue
            dest = UPLOAD_DIR / Path(item.filename).name
            try:
                # Stream to disk in chunks — never holds whole file in RAM
                with open(dest, "wb") as out:
                    while True:
                        chunk = item.file.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        out.write(chunk)
                saved.append(item.filename)
                print(f"  [{i}/{total}] Saved: {dest.name}")
            except Exception as e:
                errors.append(f"{item.filename}: {e}")
                print(f"  [{i}/{total}] ERROR: {e}")

        elapsed = round(time.time() - self._start, 1)
        summary = f"Saved {len(saved)} files in {elapsed}s"
        if errors:
            summary += f" | {len(errors)} errors: {'; '.join(errors)}"

        print(f"\n{'='*60}")
        print(f"DONE: {summary}")
        print(f"{'='*60}\n")

        self._respond(200, summary)
        self.log_w3c("POST", 200, 0, clength,
                     saved=f"{len(saved)}_files", error="; ".join(errors))

    def _respond(self, code, message):
        body = f"""<html><body>
        <p>{html.escape(message)}</p>
        <a href='/'>Upload more</a>
        </body></html>""".encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # silenced — w3c logger handles output

# Tune socket buffers for large transfers
class BufferedHTTPServer(HTTPServer):
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
        super().server_bind()

with open(LOG_FILE, "a") as f:
    if os.path.getsize(LOG_FILE) == 0:
        w3c_header(f)

print(f"HTTP upload server   → http://192.168.0.233:{PORT}")
print(f"Max upload size      → {MAX_SIZE_MB}MB")
print(f"Connection timeout   → {TIMEOUT_SEC}s")
print(f"W3C log              → {LOG_FILE}")
BufferedHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
