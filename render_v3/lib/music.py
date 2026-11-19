"""Ruhiges, modernes Ambient-Bett (Pads + weicher Puls + Glitzer), deterministisch."""
import numpy as np, wave, sys
SR = 44100
from scipy.signal import lfilter
def lp(x, a):  # Einpol-Tiefpass
    return lfilter([a], [1, a - 1], x)
def music(path, dur, seed=1, root=50):
    r = np.random.default_rng(seed); n = int(SR * dur); t = np.arange(n) / SR
    prog = [[0, 3, 7, 10, 14], [-4, 0, 3, 7, 10], [-7, -3, 0, 4, 7], [-2, 2, 5, 9, 12]]  # i9 – VI – III – VII
    bar = 60 / 76 * 4; out = np.zeros(n)
    for k in range(int(dur / bar) + 2):
        ch = prog[k % 4]; s0 = int(k * bar * SR); L = int(bar * 1.6 * SR)
        tt = np.arange(L) / SR; env = np.minimum(1, tt / 1.6) * np.exp(-np.maximum(0, tt - bar) * 1.4)
        for iv in ch:
            f = 440 * 2 ** ((root + iv - 69) / 12)
            for det in (-0.12, 0.12):
                ph = r.uniform(0, 6.28)
                w = np.sin(2*np.pi*f*(1+det/100)*tt + ph) + .25*np.sin(2*np.pi*2*f*tt + ph) + .08*np.sin(2*np.pi*3*f*tt)
                seg = w * env * .06
                e = min(n, s0 + L)
                if e > s0: out[s0:e] += seg[:e - s0]
        # Bass
        fb = 440 * 2 ** ((root - 12 + ch[0] - 69) / 12); Lb = int(bar * SR); tb = np.arange(Lb) / SR
        sb = np.sin(2*np.pi*fb*tb) * np.minimum(1, tb / .4) * np.exp(-tb * .5) * .12
        e = min(n, s0 + Lb)
        if e > s0: out[s0:e] += sb[:e - s0]
    # weicher Puls (Viertel)
    beat = 60 / 76
    for k in range(int(dur / beat)):
        s0 = int(k * beat * SR); L = int(.25 * SR); tt = np.arange(L) / SR
        th = np.sin(2*np.pi*(55 + 40*np.exp(-tt*30))*tt) * np.exp(-tt*14) * (.10 if k % 2 == 0 else .05)
        e = min(n, s0 + L)
        if e > s0: out[s0:e] += th[:e - s0]
    # Glitzer
    for k in range(int(dur / (beat/2))):
        if r.random() < .22:
            f = 440 * 2 ** ((root + 24 + r.choice([0, 3, 7, 10, 14]) - 69) / 12); s0 = int(k * beat/2 * SR); L = int(1.2 * SR); tt = np.arange(L) / SR
            g = np.sin(2*np.pi*f*tt) * np.exp(-tt*3) * .025; e = min(n, s0 + L)
            if e > s0: out[s0:e] += g[:e - s0]
    out = lp(out, 0.18)
    fade = np.minimum(1, t / 1.5) * np.minimum(1, (dur - t) / 2.5); out *= fade
    out = out / np.abs(out).max() * .7
    st = np.stack([out, np.roll(out, 300)], 1)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype(np.int16).tobytes())
if __name__ == '__main__': music(sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 50)
