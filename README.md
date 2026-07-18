# myAade — calm personal invoicing for Greece

> A bilingual, local-first invoice workspace that makes myDATA submission feel understandable rather than intimidating.

myAade is an **Apps for Your Life** entry for OpenAI Build Week. It helps Greek freelancers and small business owners draft an invoice, see VAT clearly, and submit it to AADE myDATA from one calm, accessible flow. It runs with SQLite by default and starts in a completely safe Demo mode.

## Why this matters

For a sole proprietor, invoicing is personal admin with real consequences: fragmented tools, opaque tax terminology, and the anxiety of submitting the wrong thing. myAade converts the core journey into one deliberate loop: create → review totals → transmit → retain a local record. Greek and English switching supports accountants, founders, and international collaborators.

## Features

- Polished responsive Flask/Tailwind interface
- Greek / English UI toggle
- SQLite local persistence — no account required
- Draft, review, and myDATA transmission state
- Safe `demo`, AADE `development`, and `production` environments
- XML invoice builder and documented AADE headers
- Health endpoint at `/health`

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Open `http://127.0.0.1:5000`. The default `MYDATA_MODE=demo` never calls AADE; it generates a clearly labelled `DEMO-*` MARK.

## AADE configuration

The AADE specification requires `aade-user-id` and `ocp-apim-subscription-key` in every call. Put credentials only in your local `.env` or deployment secret manager — `.env` and databases are intentionally ignored by Git.

```bash
MYDATA_MODE=development # uses https://mydataapidev.aade.gr
MYDATA_USER_ID=your-user-id
MYDATA_SUBSCRIPTION_KEY=your-subscription-key
MYDATA_VAT_NUMBER=your-vat-number
SECRET_KEY=a-long-random-secret
```

Use production only after AADE schema validation and an operational review. myAade is a hackathon prototype, not accounting or tax advice.

## Cloudflare Tunnel test domain

For a disposable public testing URL, start the app and run `bash scripts/run-tunnel.sh`. It prints a temporary `trycloudflare.com` URL.

For your Cloudflare-managed test domain, install `cloudflared`, run `cloudflared tunnel login`, then `cloudflared tunnel create myaade-test` and `cloudflared tunnel route dns myaade-test test.example.com`. Copy `cloudflared/config.example.yml` to `~/.cloudflared/config.yml`, replace the tunnel UUID, credentials path, and hostname, then run `cloudflared tunnel run myaade-test`. Keep tunnel credentials outside this repository; `.cloudflared/` is ignored.

### Start on reboot (Linux/systemd)

The repository includes service templates in `deploy/systemd/`. They run the app through Gunicorn on local port `5050` and expose it only through Cloudflare Tunnel. Adjust absolute paths if your checkout is elsewhere, then install and start them:

```bash
sudo cp deploy/systemd/myaade.service /etc/systemd/system/
sudo cp deploy/systemd/myaade-cloudflared.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now myaade.service myaade-cloudflared.service
sudo systemctl status myaade.service myaade-cloudflared.service
```

Use `journalctl -u myaade.service -f` or `journalctl -u myaade-cloudflared.service -f` to diagnose failures. Do not enable production myDATA credentials until the submission schema and full accounting workflows have been validated.

## myDATA integration

`SendInvoices` is implemented as an XML POST. The project configuration also documents the other AADE endpoints planned for the product: CancelInvoice, SendIncomeClassification, SendExpensesClassification, RequestDocs, RequestTransmittedDocs, RequestMyIncome, and RequestMyExpenses. AADE’s API documentation is the source of truth: [v2.0.2 preofficial ERP PDF](https://www.aade.gr/sites/default/files/2026-06/myDATA%20API%20Documentation%20v2.0.2_preofficial_erp.pdf).

## Built with Codex and GPT-5.6

This project was created during OpenAI Build Week with Codex. Codex accelerated the full vertical slice: shaping the local-first product concept, turning AADE REST/XML requirements into the Flask integration boundary, implementing the SQLite data model and environment safety rails, and iterating on a bilingual Tailwind user experience. The human product decisions were to keep financial data local by default, make Demo mode unmistakable, and prioritize a single anxiety-reducing submission journey over a sprawling ERP.

## Hackathon demo checklist

- [ ] Record a public YouTube demo with audio under three minutes.
- [ ] Show the Demo invoice flow, language switch, and environment safety.
- [ ] Explain the Codex/GPT-5.6 collaboration above.
- [ ] Add the public repository URL and `/feedback` Codex Session ID to Devpost.
- [ ] Provide a public demo deployment or clear local testing instructions.

## License

[MIT](LICENSE)
