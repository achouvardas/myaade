# Installation, configuration, and operations

## Prerequisites

- Python 3.11+ and `venv`
- Git
- For production: systemd and a non-root deployment user (recommended)
- Optional public access: `cloudflared`, a Cloudflare account, and a hostname routed to a named tunnel

## Install locally

```bash
git clone https://github.com/achouvardas/Elefthero.git elefthero
cd elefthero
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
cp .env.example .env
chmod 600 .env
```

Set a strong Flask session key in `.env`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

```bash
set -a
. ./.env
set +a
.venv/bin/python app.py
```

Open `http://127.0.0.1:5000`, create the first administrator, and complete the authenticated setup.

## Configuration reference

| Value | Where to set it | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | `.env` or service environment | Required Flask session-signing key |
| `DATABASE_URL` | `.env` or service environment | Optional SQLAlchemy URL; defaults to local SQLite |
| `MYDATA_MODE` | `.env` or service environment | Startup default; Settings is authoritative after setup |
| `PORT`, `FLASK_DEBUG` | `.env` or service environment | Development-server behavior |
| Business profile | Authenticated UI | Issuer VAT and PDF identity/details |
| AADE credentials | Settings | Encrypted Test and Production pairs |
| Turnstile | Settings | Optional sign-in protection; both site key and secret are needed |
| Resend | Settings | Optional manual invoice email delivery |
| TOTP | User `2FA` page | Generated and encrypted by the app |

Do not put AADE, Resend, Turnstile, or TOTP secrets in `.env` or Git. The application encrypts them locally after authenticated setup.

## Gunicorn and systemd

Run Gunicorn directly for a local/reverse-proxied deployment:

```bash
set -a
. ./.env
set +a
.venv/bin/gunicorn --workers 2 --bind 127.0.0.1:5050 app:app
```

The supplied systemd unit files use `/root/myaade_erp` as example paths. Copy and edit paths, user, and Cloudflare config before enabling them:

```bash
sudo cp deploy/systemd/myaade.service /etc/systemd/system/elefthero.service
sudo cp deploy/systemd/myaade-cloudflared.service /etc/systemd/system/elefthero-cloudflared.service
sudoedit /etc/systemd/system/elefthero.service
sudoedit /etc/systemd/system/elefthero-cloudflared.service
sudo systemctl daemon-reload
sudo systemctl enable --now elefthero.service elefthero-cloudflared.service
```

Useful commands:

```bash
sudo systemctl restart elefthero.service
sudo journalctl -u elefthero.service -f
curl http://127.0.0.1:5050/health
```

## Cloudflare Tunnel

Keep tunnel credentials and configuration outside Git. A minimal configuration is:

```yaml
tunnel: YOUR-TUNNEL-UUID
credentials-file: /path/to/YOUR-TUNNEL-UUID.json

ingress:
  - hostname: invoices.example.gr
    service: http://127.0.0.1:5050
  - service: http_status:404
```

Create the DNS route using Cloudflare’s dashboard or CLI.

## Backups and updates

- Back up the SQLite database and entire `instance/` directory together. The instance directory contains the Fernet key, generated PDFs, and logo files.
- Losing the Fernet key means encrypted AADE/Resend/Turnstile/TOTP values cannot be recovered.
- Test all AADE updates in AADE Test before Production.

```bash
git pull
.venv/bin/pip install -r requirements.txt
sudo systemctl restart elefthero.service
```

## Development checks

```bash
.venv/bin/python -m py_compile app.py
git diff --check
```
