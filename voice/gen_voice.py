#!/usr/bin/env python3
"""Stimme Dr. Atalay (KI-Nachbildung, autorisiert) – Version 4 „Probe B“ (19.11.2026, freigegeben als Richtung).
Prinzip: ganze Absätze (1–2 Sätze) statt Einzelsätze erzeugen → natürliche Satzmelodie; mehrere Versuche je Absatz,
Spracherkennung wählt den deutlichsten; nur zu lange Pausen kürzen (natürliche Atempausen bleiben);
Tempo per Rubberband (Stimmhöhe und Klangfarbe bleiben erhalten); Sprecher-Klangkette (Hochpass, sanfte Kompression,
Präsenz, Entrauschung, −16 LUFS).
Aufruf: gen_voice.py lines.json out_dir [ref.wav]
lines.json: [{"id": "a1", "say": "Ein oder zwei Sätze in Lautschrift", "check": "Originaltext (optional)"}]
Höchstens ~6 Einträge pro Prozess (Speicher).
"""
import json, os, sys, difflib, re, subprocess
import numpy as np, soundfile as sf, torch

SR = 24000
TEMPO = float(os.environ.get("TEMPO", "1.12"))
TRIES = int(os.environ.get("TRIES", "3"))
EXAG = float(os.environ.get("EXAG", "0.55"))
CFG = float(os.environ.get("CFG", "0.5"))
TEMP = float(os.environ.get("VOICE_TEMP", "0.8"))
PAUSE_MAX, PAUSE_KEEP = 0.35, 0.30   # Pausen über 0,35 s auf 0,30 s kürzen
CHAIN = ("highpass=f=75,afftdn=nf=-50,"
         "acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120:makeup=2,"
         "equalizer=f=3200:t=q:w=1.2:g=2,deesser=i=0.35,"
         "loudnorm=I=-16:TP=-1.5:LRA=7")


def norm(t):
    t = t.lower().replace("ß", "ss")
    return re.sub(r"[^a-zäöü0-9 ]", " ", t).split()


def score(a, b):
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def shape_pauses(x):
    f = int(0.01 * SR)
    n = len(x) // f
    e = np.array([np.sqrt(np.mean(x[i * f:(i + 1) * f] ** 2)) + 1e-9 for i in range(n)])
    sil = 20 * np.log10(e / e.max()) < -40
    out, i = [], 0
    while i < n:
        j = i
        while j < n and sil[j] == sil[i]:
            j += 1
        seg = x[i * f:j * f]
        if sil[i] and (j - i) * 0.01 > PAUSE_MAX:
            k = int(PAUSE_KEEP * SR)
            seg = np.concatenate([seg[:k // 2], seg[-k // 2:]])
        out.append(seg)
        i = j
    out.append(x[n * f:])
    y = np.concatenate(out)
    # Anfang/Ende auf 60 ms Ruhe trimmen
    nz = np.where(np.abs(y) > 10 ** (-40 / 20) * np.abs(y).max())[0]
    if len(nz):
        y = y[max(0, nz[0] - int(.06 * SR)):nz[-1] + int(.06 * SR)]
    return y.astype(np.float32)


def finish(src, dst):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af",
                    f"rubberband=tempo={TEMPO}:pitchq=quality:formant=preserved," + CHAIN, "-ar", str(SR), dst], check=True)


def main():
    lines = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
    ref = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "ref.wav")
    torch.manual_seed(int(os.environ.get("SEED", "7")))
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    from faster_whisper import WhisperModel
    tts = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    asr = WhisperModel("small", device="cpu", compute_type="int8")
    report = []
    for ln in lines:
        best = None
        for t in range(TRIES):
            x = tts.generate(ln["say"], language_id=ln.get("lang", "de"), audio_prompt_path=ref,
                             exaggeration=EXAG, cfg_weight=CFG, temperature=TEMP).squeeze().numpy()
            raw = os.path.join(out, f"{ln['id']}_raw{t}.wav"); sf.write(raw, x, SR)
            segs, _ = asr.transcribe(raw, language=ln.get("lang", "de"), beam_size=1)
            heard = " ".join(s.text for s in segs).strip()
            sc = score(ln.get("check", ln["say"]), heard)
            print(f"{ln['id']} Versuch {t + 1}: {sc:.2f} | {heard}", flush=True)
            if best is None or sc > best[0]:
                best = (sc, x, heard)
            if sc >= 0.97:
                break
        tmp = os.path.join(out, f"{ln['id']}_shaped.wav"); sf.write(tmp, shape_pauses(best[1]), SR)
        fin = os.path.join(out, f"{ln['id']}.wav"); finish(tmp, fin)
        report.append({"id": ln["id"], "score": round(best[0], 3), "heard": best[2], "dur": round(len(sf.read(fin)[0]) / SR, 2)})
    json.dump(report, open(os.path.join(out, "report.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
