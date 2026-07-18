#!/usr/bin/env python3
"""Generate Elefthero's fixed Devpost narration with local Kokoro audio."""
from pathlib import Path
import argparse
import subprocess
import tempfile
import wave

import numpy as np
import sherpa_onnx

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "instance" / "models" / "kokoro-en-v0_19"
OUTPUT = ROOT / "instance" / "demo-audio"
SCRIPT = [
    "Elefthero is the open-source way to invoice in Greece. It gives small businesses a simple, self-hosted way to understand and control their invoicing data.",
    "Greek businesses must transmit invoice data to AADE myDATA. Many existing choices are expensive, opaque, or difficult to adapt to everyday work.",
    "Elefthero means free. It is MIT licensed, self-hosted, bilingual, and designed so that sent and received AADE XML can be inspected.",
    "The app validates invoice data, builds myDATA XML, transmits to AADE Test or Production, then retains the response, MARK, UID, and QR URL.",
    "Codex and GPT-5.6 were hands-on implementation partners: turning AADE validation errors into XML fixes, building Flask workflows, and refining the product through live feedback.",
    "This is not a mockup. Elefthero has real AADE Test and Production modes, local encrypted settings, PDFs, client tools, and audit logs.",
    "The dashboard gives a small business an immediate view of transmitted turnover, VAT, drafts, recent invoices, and top customers. The navigation keeps every daily task close.",
    "Invoices are searchable by customer name and VAT number, with status, document type, amounts, AADE identifiers, filtering, and links to the full record.",
    "New invoices keep the form focused: choose one of the supported document types, select or add a customer when appropriate, add multiple lines, VAT, payment method, and required income classification.",
    "Clients are reusable and searchable. The workflow can validate Greek VAT numbers through VIES and optionally enrich records through the public GEMI service when it is available.",
    "Templates and reuse reduce repeated work. A transmitted invoice can become an editable fresh draft or a named template without copying sensitive submission identifiers.",
    "Business Profile controls the identity printed on PDFs. Settings keeps AADE Test and Production credentials separate, encrypted locally, alongside email, security, and service configuration.",
    "Administrators manage local users and roles. Optional Turnstile, configurable login rate limits, CSRF protection, and authenticator-app two factor authentication protect real business workflows.",
    "Security settings make the rate limits and optional services explicit, while the two factor page lets each user enrol a standard authenticator app with a QR code.",
    "Two factor authentication is optional, user controlled, and stored encrypted at rest. It protects access without forcing a third-party identity provider.",
    "Finally, the developer log makes the integration inspectable: sign-in events, client lookups, PDF generation, sent XML, received XML, and AADE errors remain visible for troubleshooting.",
]

def build_engine():
    needed = [MODEL / name for name in ("model.onnx", "voices.bin", "tokens.txt", "espeak-ng-data")]
    if not all(path.exists() for path in needed):
        raise SystemExit("Kokoro model files are missing. See docs/INSTALLATION.md.")
    kokoro = sherpa_onnx.OfflineTtsKokoroModelConfig(model=str(MODEL / "model.onnx"), voices=str(MODEL / "voices.bin"), tokens=str(MODEL / "tokens.txt"), data_dir=str(MODEL / "espeak-ng-data"))
    config = sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(kokoro=kokoro, num_threads=4, provider="cpu"), max_num_sentences=1, silence_scale=0.28)
    return sherpa_onnx.OfflineTts(config)

def write_wav(path, samples, sample_rate):
    pcm = (np.clip(np.asarray(samples, dtype=np.float32), -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1); output.setsampwidth(2); output.setframerate(sample_rate); output.writeframes(pcm.tobytes())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=len(SCRIPT))
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    engine = build_engine()
    for index, text in enumerate(SCRIPT[args.start:args.end], start=args.start):
        target = OUTPUT / f"step-{index:02d}.mp3"
        if target.exists() and target.stat().st_size > 1024:
            print(f"{target.name} (already generated)")
            continue
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temporary:
            wav_path = Path(temporary.name)
        try:
            generated = engine.generate(text, sid=1, speed=0.96)  # af_bella: warm American English female voice
            write_wav(wav_path, generated.samples, generated.sample_rate)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav_path), "-c:a", "libmp3lame", "-b:a", "96k", str(target)], check=True)
            print(target.name)
        finally:
            wav_path.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
