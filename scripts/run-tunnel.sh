#!/usr/bin/env bash
set -euo pipefail
# A temporary public URL — no DNS setup required.
cloudflared tunnel --url http://127.0.0.1:5000
