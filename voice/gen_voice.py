#!/usr/bin/env python3
"""Stimme Dr. Atalay (KI-Nachbildung, autorisiert) – Version 3 (18.11.2026).
Verbesserungen gegenüber v2: zügigeres Tempo, stille und kurze Pausen, Qualitätsprüfung per Spracherkennung.
Aufruf: gen_voice.py lines.json out_dir [ref.wav]
lines.json: [{"id": "s1_1", "say": "Text", "check": "erwarteter Wortlaut (optional)"}]
"""
import json, os, sys, difflib, re, subprocess
import numpy as np, soundfile as sf, torch

SR = 24000
TEMPO = float(os.environ.get("TEMPO", "1.20"))      # zeitliche Straffung ohne Tonhöhenänderung
MAX_PAUSE = float(os.environ.get("MAX_PAUSE", "0.16"))  # max. Pause innerhalb eines Satzes (s)
TRIES = int(os.environ.get("TRIES", "3"))


def norm(t):
    t = t.lower().replace("ß", "ss")
    return re.sub(r"[^a-zäöü0-9 ]", " ", t).split()


def score(a, b):
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def clean(x):
    """Pausen stumm schalten und kürzen, Anfang/Ende trimmen."""
    x = x.astype(np.float32)
    f = int(0.01 * SR)
    n = len(x) // f
    e = np.array([np.sqrt(np.mean(x[i * f:(i + 1) * f] ** 2)) + 1e-9 for i in range(n)])
    db = 20 * np.log10(e / (np.max(e) + 1e-9))
    voiced = db > -38                                         # relativ zum lautesten Teil
    # kurze Lücken (<40 ms) innerhalb von Lauten nicht als Pause zählen
    v = voiced.copy()
    for i in range(1, n - 4):
        if not v[i] and v[i - 1] and v[i + 1:i + 5].any():
            v[i] = True
    idx = np.where(v)[0]
    if len(idx) == 0:
        return x
    out, i, start = [], idx[0], idx[0]
    segs = []
    run_s = idx[0]
    for a, b in zip(idx[:-1], idx[1:]):
        if b - a > 1:
            segs.append((run_s, a + 1)); run_s = b
    segs.append((run_s, idx[-1] + 1))
    fade = int(0.008 * SR)
    for k, (s, e_) in enumerate(segs):
        seg = x[max(0, s * f - fade):min(len(x), e_ * f + fade)].copy()
        seg[:fade] *= np.linspace(0, 1, fade)[:len(seg[:fade])]
        seg[-fade:] *= np.linspace(1, 0, fade)[:len(seg[-fade:])]
        out.append(seg)
        if k < len(segs) - 1:
            gap = (segs[k + 1][0] - e_) * f / SR
            out.append(np.zeros(int(min(gap, MAX_PAUSE) * SR), np.float32))
    return np.concatenate(out)


def tempo(path_in, path_out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path_in, "-af",
                    f"atempo={TEMPO},highpass=f=60,lowpass=f=11000,loudnorm=I=-16:TP=-1.5:LRA=7", "-ar", str(SR), path_out], check=True)


def main():
    lines = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
    ref = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(__file__), "ref.wav")
    torch.manual_seed(int(os.environ.get("SEED", "41")))
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    from faster_whisper import WhisperModel
    tts = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    asr = WhisperModel("small", device="cpu", compute_type="int8")
    report = []
    for ln in lines:
        best = None
        for t in range(TRIES):
            wav = tts.generate(ln["say"], language_id=ln.get("lang", "de"), audio_prompt_path=ref,
                               exaggeration=float(os.environ.get("EXAG", "0.55")),
                               cfg_weight=float(os.environ.get("CFG", "0.35")), temperature=0.75)
            x = wav.squeeze().numpy()
            raw = os.path.join(out, f"{ln['id']}_raw{t}.wav"); sf.write(raw, x, SR)
            segs, _ = asr.transcribe(raw, language=ln.get("lang", "de"), beam_size=1)
            heard = " ".join(s.text for s in segs)
            sc = score(ln.get("check", ln["say"]), heard)
            print(f"{ln['id']} Versuch {t + 1}: {sc:.2f} | {heard.strip()}", flush=True)
            if best is None or sc > best[0]:
                best = (sc, x, heard)
            if sc >= 0.92:
                break
        c = clean(best[1]); tmp = os.path.join(out, f"{ln['id']}_clean.wav"); sf.write(tmp, c, SR)
        final = os.path.join(out, f"{ln['id']}.wav"); tempo(tmp, final)
        report.append({"id": ln["id"], "score": round(best[0], 3), "heard": best[2].strip(), "dur": round(len(sf.read(final)[0]) / SR, 2)})
    json.dump(report, open(os.path.join(out, "report.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
