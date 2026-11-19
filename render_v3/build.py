#!/usr/bin/env python3
"""Shorts im Stil v3 (19.11.2026): echte Fotos mit Kamerafahrt, animierte Infografiken, Wort-für-Wort-Untertitel,
Musik mit Ducking und Übergangs-Sounds. Aufruf: build.py data.json out.mp4"""
import json, os, sys, subprocess, re, wave
import numpy as np, soundfile as sf
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 24000; FPS = 30; LEAD = 0.4; GAP = 0.38; ENDCARD = 3.6
D = json.load(open(sys.argv[1])); OUT = sys.argv[2]; WORK = OUT + ".work"; os.makedirs(WORK, exist_ok=True)
base = os.path.dirname(os.path.abspath(sys.argv[1]))
P = lambda p: p if os.path.isabs(p) else os.path.join(base, p)

# 1) Stimme zusammensetzen, Szenenzeiten
voice = [np.zeros(int(LEAD * SR))]; t = LEAD; scenes = []
for i, s in enumerate(D["scenes"]):
    x, sr = sf.read(P(s["audio"])); assert sr == SR
    if x.ndim > 1: x = x.mean(1)
    t0 = 0 if i == 0 else t; voice.append(x); s["a0"] = t; t += len(x) / SR; s["a1"] = t
    gap = GAP if i < len(D["scenes"]) - 1 else ENDCARD
    voice.append(np.zeros(int(gap * SR))); t += gap
    s["t0"] = t0; s["t1"] = t
v = np.concatenate(voice).astype(np.float32); TOTAL = len(v) / SR
sf.write(f"{WORK}/voice.wav", v, SR)

# 2) Wortzeiten (Spracherkennung liefert Zeiten, Wortlaut kommt aus dem Skript)
subprocess.run([os.environ.get("CBX_PY", "/home/claude/cbx/bin/python"), os.path.join(HERE, "words.py"), f"{WORK}/hw.json"] + [P(s["audio"]) for s in D["scenes"]], check=True, capture_output=True)
HW = json.load(open(f"{WORK}/hw.json"))
words = []
for i, s in enumerate(D["scenes"]):
    hw = HW[i]
    txt = s["text"].split()
    if not hw:
        continue
    if len(hw) == len(txt):
        tim = [tuple(w) for w in hw]
    else:   # proportional über Zeichenpositionen verteilen
        a, b = hw[0][0], hw[-1][1]; L = sum(len(w) + 1 for w in txt); c = 0; tim = []
        for w in txt:
            s0 = a + (b - a) * c / L; c += len(w) + 1; tim.append((s0, a + (b - a) * c / L))
    for w, (ws, we) in zip(txt, tim):
        words.append({"w": w, "s": round(s["a0"] + ws, 3), "e": round(s["a0"] + we, 3), "sc": i})

# 3) Musik + Übergangs-Sounds, Ducking
sys.path.insert(0, os.path.join(HERE, "lib"))
from music import music
music(f"{WORK}/music.wav", TOTAL + 1, seed=D.get("seed", 3), root=D.get("root", 50))
sr2 = 44100; n = int(TOTAL * sr2); sfx = np.zeros(n)
rng = np.random.default_rng(5)
for s in D["scenes"][1:]:
    L = int(.45 * sr2); tt = np.arange(L) / sr2; noise = rng.standard_normal(L)
    from scipy.signal import butter, lfilter
    bb, aa = butter(2, [400 / (sr2 / 2), 5000 / (sr2 / 2)], "band"); w = lfilter(bb, aa, noise)
    env = np.sin(np.pi * np.clip(tt / .45, 0, 1)) ** 2
    s0 = int(max(0, s["t0"] - .22) * sr2); e = min(n, s0 + L); sfx[s0:e] += (w * env * .05)[:e - s0]
sf.write(f"{WORK}/sfx.wav", sfx.astype(np.float32), sr2)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{WORK}/voice.wav", "-i", f"{WORK}/music.wav", "-i", f"{WORK}/sfx.wav", "-filter_complex",
                "[0:a]aresample=44100,asplit=2[v][vk];[1:a]volume=0.55[m];[m][vk]sidechaincompress=threshold=0.03:ratio=6:attack=30:release=400[md];"
                "[v][md][2:a]amix=inputs=3:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=9[out]",
                "-map", "[out]", "-ar", "44100", f"{WORK}/mix.wav"], check=True)

# 4) Bilder rendern
data = {"scenes": [{k: (("file://" + P(v_)) if k == "photo" else v_) for k, v_ in s.items()} for s in D["scenes"]], "words": words}
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-", "-i", f"{WORK}/mix.wav",
                       "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                       "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
with sync_playwright() as p:
    b = p.chromium.launch(args=["--allow-file-access-from-files"]); pg = b.new_page(viewport={"width": 1080, "height": 1920})
    pg.goto("file://" + os.path.join(HERE, "short.html")); pg.evaluate("d=>setup(d)", data)
    nf = int(TOTAL * FPS)
    for f in range(nf):
        pg.evaluate(f"render({f / FPS})")
        if f == 0: pg.wait_for_timeout(400)
        ff.stdin.write(pg.screenshot(type="jpeg", quality=92))
        if only := os.environ.get("STILLS"):
            pass
    b.close()
ff.stdin.close(); ff.wait()
json.dump({"total": TOTAL, "scenes": [(s["id"], s["t0"], s["t1"]) for s in D["scenes"]]}, open(f"{WORK}/timeline.json", "w"))
print("fertig", OUT, round(TOTAL, 1), "s")
