# Hosting the RPS server (Linux + Nginx + systemd)

Notes for running the FastAPI app behind Nginx on a Linux host, with TLS on port 443 and the app on `127.0.0.1:8000`.

---

## 1. Self-signed TLS certificate

Creates a key and cert under `/etc/nginx/ssl/` for **testing or internal use**. Browsers will show a **warning** until you trust the cert or use a real hostname certificate (e.g. Let’s Encrypt).

```bash
sudo mkdir -p /etc/nginx/ssl
sudo openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/selfsigned.key \
  -out /etc/nginx/ssl/selfsigned.crt
```

For production on the public internet, prefer **Let’s Encrypt** (or your host’s managed TLS) instead of a long-lived self-signed cert.

---

## 2. nip.io and CA-issued certificates (Let’s Encrypt)

If you do not own a domain but you have a **public static IP**, you can still get a **browser-trusted** certificate by using a free hostname that resolves to that IP.

### nip.io

[**nip.io**](https://nip.io) is a public DNS service that answers queries for names of the form:

```text
<your-static-ip>.nip.io
```

Example: if your server’s public IPv4 is `203.0.113.7`, then **`203.0.113.7.nip.io`** resolves to `203.0.113.7`. You can put that hostname in Nginx’s `server_name` and in URLs (e.g. `https://203.0.113.7.nip.io/game`).

Requirements for this to be useful with a real CA:

- The address must be reachable on the **internet** (not only on a private LAN).
- **TCP 80** and **443** should be open to the world (or at least to Let’s Encrypt’s validation servers) while you obtain and renew certificates.

Private addresses (e.g. `192.168.x.x`) can still use `*.nip.io` names for local testing, but **Let’s Encrypt HTTP-01** validation from the public internet will not succeed for a host that is not reachable on those ports from outside.

### Issue a certificate with Certbot (nginx plugin)

Install Certbot and the Nginx plugin using your distro’s packages, then request a cert for your nip.io name (replace the IP with yours):

```bash
sudo certbot --nginx -d 203.0.113.7.nip.io
```

Certbot will adjust your Nginx site to use the issued files (under `/etc/letsencrypt/live/...`) and set up renewal timers. Use the **same** hostname in `server_name` as you passed to `-d`.

If you prefer to obtain the cert first and wire Nginx yourself:

```bash
sudo certbot certonly --nginx -d 203.0.113.7.nip.io
```

Then point `ssl_certificate` and `ssl_certificate_key` at the paths Certbot prints (typically under `/etc/letsencrypt/live/<name>/`).

### Nginx before Certbot

You still need a working HTTP server on port **80** so Let’s Encrypt can complete **HTTP-01** validation. A minimal `server { listen 80; server_name 203.0.113.7.nip.io; ... }` proxying to the app (or a simple `root`/`return`) is enough; Certbot can then add the HTTPS block or the `ssl` directives.

### Renewals

Let’s Encrypt certificates are short-lived; Certbot normally installs a **systemd timer** or **cron** job to renew. Keep Nginx and the app running so renewals succeed.

---

## 3. Nginx configuration

Place the site config where your distribution expects it (example: `/etc/nginx/conf.d/rps.conf`).

**Yes — if you use a proper domain or a nip.io name, you should update Nginx** so it matches how clients and TLS expect to reach you:

| What | Why it matters |
|------|----------------|
| **`server_name`** | Must be the **exact hostname** users type in the browser (e.g. `game.example.com` or `203.0.113.7.nip.io`). Using `_` is only a loose catch-all; for HTTPS, the name should match the certificate and what DNS points to. |
| **`ssl_certificate` / `ssl_certificate_key`** | **Self-signed** (section 1): paths under `/etc/nginx/ssl/` (or wherever you put them). **Let’s Encrypt** (section 2): typically `/etc/letsencrypt/live/<your-hostname>/fullchain.pem` and `privkey.pem` — Certbot usually writes these when you run `certbot --nginx`. |
| **DNS** | For a real domain, an **A record** (or AAAA) must point that hostname to your server’s public IP **before** HTTP-01 validation and before users can resolve the name. |

Shared proxy settings (reuse in both HTTP and HTTPS `location /`):

```nginx
proxy_http_version 1.1;
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

### Option A — Quick test: self-signed, catch-all `server_name`

Fine for LAN or experiments. Browsers will warn unless you trust the cert.

```nginx
server {
    listen 80 default_server;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

server {
    listen 443 ssl default_server;
    server_name _;

    ssl_certificate /etc/nginx/ssl/selfsigned.crt;
    ssl_certificate_key /etc/nginx/ssl/selfsigned.key;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Option B — Real hostname: domain or `<ip>.nip.io` + CA certificate

Use **one** `server_name` value everywhere it appears below; replace `game.example.com` with your real FQDN or your nip.io name.

After **Certbot** (`certbot --nginx -d game.example.com`), Nginx will usually contain something like:

```nginx
server {
    listen 80;
    server_name game.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

server {
    listen 443 ssl;
    server_name game.example.com;

    ssl_certificate /etc/letsencrypt/live/game.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/game.example.com/privkey.pem;
    # Certbot may add include snippets or redirect HTTP→HTTPS; keep those.

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Do **not** leave `server_name _;` on the HTTPS block if the certificate was issued for `game.example.com` — the server name and cert SAN must align, or browsers may show certificate name errors.

Reload Nginx after edits:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## 4. systemd service unit

### Why use systemd (instead of running `uvicorn` by hand)?

A **one-off** `uvicorn` in an SSH session stops when you disconnect, when the terminal closes, or when the process crashes. For anything beyond a quick test, you want a **supervisor** so the API is always there for Nginx to proxy to.

**systemd** gives you:

| Benefit | What it means here |
|--------|---------------------|
| **Starts on boot** | After a server reboot, the game comes back without logging in to run commands. `enable` wires the unit into `multi-user.target`. |
| **Restarts on failure** | `Restart=always` brings **uvicorn** back up if it exits unexpectedly (OOM, bug, killed). |
| **Defined environment** | `WorkingDirectory`, `User`, and `Environment` set a stable cwd and PATH so imports and `server_config.json` resolve the same way every time—not whatever directory your shell was in. |
| **No login session** | The app runs as a system service, not tied to your user’s graphical or SSH session. |
| **Operations** | Standard commands: `systemctl start/stop/restart/status`, logs via `journalctl -u rps`. |

Alternatives (Docker, `supervisord`, `pm2`, etc.) are fine; systemd is the usual default on modern Linux distros.

### Unit file

Adjust **`User`**, **`WorkingDirectory`**, and **`ExecStart`** paths to match your machine (unprivileged user, Python venv, and repo path). **`User`** should not be `root` unless you have a strong reason.

- **`After=network.target`** — start only once networking is up so `0.0.0.0:8000` binds sensibly.
- **`WorkingDirectory`** — must be the folder that contains `main.py` (FastAPI app module).
- **`ExecStart`** — full path to the **uvicorn** binary in your venv; `--host 0.0.0.0` listens on all interfaces so Nginx on the same host can reach `127.0.0.1:8000`.
- **`Restart=always` / `RestartSec=3`** — backoff slightly between restart attempts.
- **`PYTHONUNBUFFERED=1`** — log lines flush promptly to the journal.

Example file: `/etc/systemd/system/rps.service`

```ini
[Unit]
Description=RPS
After=network.target

[Service]
User=venkatababjisama
WorkingDirectory=/home/venkatababjisama/rps/vu-rsp-dc-main/deployment/src/server

ExecStart=/home/venkatababjisama/pyenv/bin/uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000

Restart=always
RestartSec=3

Environment="PATH=/home/venkatababjisama/pyenv/bin/"
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl start rps
sudo systemctl enable rps
sudo systemctl status rps
```

---

## Quick checklist

| Item | Detail |
|------|--------|
| App bind | `uvicorn` listens on `0.0.0.0:8000`; Nginx proxies to `127.0.0.1:8000`. |
| `server_config.json` | If you use a file DB path, keep it alongside the app or use an absolute path the service user can write. |
| HTTPS and camera | The browser **game** client needs a **trusted** or **accepted** HTTPS context for live camera features; self-signed certs require trusting the cert in the browser or using proper CA-issued certs. |
| nip.io + Let’s Encrypt | Use `<static-ip>.nip.io` as a hostname, then `certbot --nginx -d <that-hostname>` for CA-issued TLS; needs a **public** IP and open **80**/**443**. See section 2. |
| Nginx + real hostname | Set **`server_name`** to that hostname on **80** and **443**; use **Let’s Encrypt** `fullchain.pem` / `privkey.pem` paths on 443 (or self-signed paths only if you chose self-signed). See section 3, option B. |
