# Local File Upload Server

A lightweight Python HTTPS/HTTP upload server for transferring photos from a mobile device to a Mac over a local network. No third-party dependencies — stdlib only.

## Use Case

Designed for locked-down phones (MDM/corporate profiles) that can access local networks but restrict cloud services. The phone hits a simple upload form in Safari and sends files directly to a Mac on the same WiFi network.

**Tested with:**
- MacBook Pro M1 Max 32gb
- iPhone iOS 17.3 / Safari
- 321 files / 678MB in a single batch (~80 seconds over WiFi)

---

## Setup

### 1. Clone or download

```bash
git clone https://github.com/yourname/yourrepo.git
cd yourrepo
```

### 2. Configure

Open `upload_server.py` and set your upload directory:

```python
UPLOAD_DIR = Path("/your/target/folder")   # change CHANGE_ME to your path
```

Other tunables at the top of the file:

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8080` | Port to listen on |
| `MAX_SIZE_MB` | `2048` | Max POST size in MB |
| `TIMEOUT_SEC` | `300` | Connection timeout (seconds) |
| `CHUNK_SIZE` | `1048576` | Read chunk size (1MB) |

### 3. Run

```bash
python3 upload_server.py
```

```
HTTP upload server   -> http://192.168.0.x:8080
Max upload size      -> 2048MB
Connection timeout   -> 300s
W3C log              -> /your/target/folder/access.log
```

### 4. Open on phone

Make sure the phone is on the same WiFi network, then open Safari and navigate to:

```
http://192.168.0.x:8080
```

Replace `192.168.0.x` with your Mac's LAN IP. Find it with:

```bash
ipconfig getifaddr en0
```

---

## Features

- **Multi-file upload** — select hundreds of files in one batch
- **Streaming writes** — files written to disk in 1MB chunks, never fully loaded into RAM
- **W3C Extended logging** — persistent `access.log` in the upload directory
- **Verbose terminal output** — full request headers and per-file save progress
- **Size guard** — rejects uploads over `MAX_SIZE_MB` before reading the body
- **Socket tuning** — 4MB send/recv buffers for large transfers
- **Zero dependencies** — pure Python 3 stdlib, no pip installs

---

## Logging

A W3C Extended Format log is written to `access.log` in the upload directory:

```
#Version: 1.0
#Date: 2026-04-17 15:07:25
#Fields: date time c-ip cs-method cs-uri-stem sc-status sc-bytes cs-bytes time-taken cs(User-Agent) x-saved-files x-error
2026-04-17  15:11:10  192.168.0.159  POST  /  200  0  678031509  80367ms  Mozilla/5.0+...  321_files  -
```

Terminal output shows full request headers and per-file progress:

```
============================================================
REQUEST  POST /
============================================================
  Host: 192.168.0.233:8080
  Content-Type: multipart/form-data; boundary=----...
  Content-Length: 678031509

Receiving 646.5 MB ...
  [1/321] Saved: IMG_0001.jpeg
  [2/321] Saved: IMG_0002.jpeg
  ...
============================================================
DONE: Saved 321 files in 80.4s
============================================================
```

---

## macOS Firewall

If the Mac firewall is enabled, allow incoming connections for Python:

**System Settings → Network → Firewall → Options**

Add `/usr/local/bin/python3` (or your Anaconda path) and set to **Allow incoming connections**.

Or temporarily disable for testing:

```bash
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off
```

---

## Finding Your Mac's IP

```bash
ipconfig getifaddr en0        # WiFi
ipconfig getifaddr en1        # Ethernet
ifconfig | grep "inet " | grep -v 127.0.0.1
```

---

## Killing the Server

```bash
# Find the PID
lsof -i :8080

# Kill it
kill <PID>
```

Or run with a saved PID:

```bash
python3 upload_server.py &
echo "PID: $!"
```

---

## Limitations

- **Single-threaded** — one upload session at a time
- **HTTP only** — no TLS. Suitable for trusted local networks only
- **iOS browser conversion** — Safari may convert HEIC photos to JPEG before upload. Use a file manager app (e.g. FE File Explorer, FileBrowser) if you need raw originals

---

## License

MIT
