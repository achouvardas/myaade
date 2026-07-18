# Technical stack

| Layer | Technology | Role |
| --- | --- | --- |
| Application | Python 3, Flask 3.1, Jinja | Server-rendered application and routes |
| Data | SQLite, Flask-SQLAlchemy | Local business, invoice, audit, and settings data |
| Web service | Gunicorn | Production WSGI server, normally bound to localhost |
| Edge | Cloudflare Tunnel / `cloudflared` | Public hostname without an exposed application port |
| AADE | HTTPS REST + XML | Test and Production myDATA transmission |
| Encryption | `cryptography` / Fernet | Encrypted application secrets and TOTP seeds |
| Authentication | Werkzeug hashes, CSRF tokens, rate limiting, Turnstile, `pyotp` | Password login, protected state-changing requests, configurable throttling, optional anti-bot check, optional authenticator 2FA |
| PDF | ReportLab | Inline invoice PDFs and QR rendering |
| Client enrichment | VIES and ΓΕΜΗ public endpoints | VAT validation and optional business data enrichment |
| Email | Resend API | Manually triggered invoice PDF delivery |
| Demo narration/export | Kokoro ONNX via `sherpa-onnx`, Browser `getDisplayMedia` / `MediaRecorder`, FFmpeg | Local open-source narration, screen recording, and H.264/AAC MP4 conversion |
| UI | Tailwind CDN + browser JavaScript | Responsive UI and local accessibility preferences |

Dependencies are pinned in [`../requirements.txt`](../requirements.txt). The project has no Node.js build step.
