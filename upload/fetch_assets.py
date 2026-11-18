#!/usr/bin/env python3
"""Lizenzfreie Bilder/Clips für Videos holen (läuft in GitHub Actions, dort ist das Internet frei).

assets/requests.json: [{"key": "lpa", "query": "blood test tube", "kind": "photo"|"video", "n": 4}]
Quellen (in dieser Reihenfolge, je nach vorhandenem Schlüssel):
  Pexels  (Secret PEXELS_KEY)   – Pexels-Lizenz, frei nutzbar, keine Namensnennung nötig
  Pixabay (Secret PIXABAY_KEY)  – Pixabay-Inhaltslizenz, frei nutzbar
  Wikimedia Commons (ohne Schlüssel) – nur Public Domain / CC0 / CC BY / CC BY-SA, Urheber wird gespeichert
Ergebnis: assets/<key>/<datei> und assets/<key>/credits.json. Bereits geholte Keys werden übersprungen.
"""
import json, os, re, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQ = os.path.join(ROOT, "assets", "requests.json")
UA = {"User-Agent": "medizin-aktuell-videos/1.0 (https://medizin-aktuell.eu)"}


def get(url, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def save(url, path):
    with open(path, "wb") as f:
        f.write(get(url))


def pexels(q, kind, n, key):
    out = []
    if kind == "video":
        d = json.loads(get(f"https://api.pexels.com/videos/search?query={urllib.parse.quote(q)}&per_page={n}&orientation=portrait", {"Authorization": key}))
        for v in d.get("videos", []):
            files = sorted([f for f in v["video_files"] if f.get("height") and f["height"] <= 1920], key=lambda f: -f["height"])
            if files:
                out.append({"url": files[0]["link"], "ext": "mp4", "author": v["user"]["name"], "source": v["url"], "license": "Pexels License"})
    else:
        d = json.loads(get(f"https://api.pexels.com/v1/search?query={urllib.parse.quote(q)}&per_page={n}", {"Authorization": key}))
        for p in d.get("photos", []):
            out.append({"url": p["src"]["large2x"], "ext": "jpg", "author": p["photographer"], "source": p["url"], "license": "Pexels License"})
    return out


def pixabay(q, kind, n, key):
    out = []
    if kind == "video":
        d = json.loads(get(f"https://pixabay.com/api/videos/?key={key}&q={urllib.parse.quote(q)}&per_page={max(3, n)}&safesearch=true"))
        for h in d.get("hits", [])[:n]:
            v = h["videos"].get("large") or h["videos"].get("medium")
            if v and v.get("url"):
                out.append({"url": v["url"], "ext": "mp4", "author": h["user"], "source": h["pageURL"], "license": "Pixabay Content License"})
    else:
        d = json.loads(get(f"https://pixabay.com/api/?key={key}&q={urllib.parse.quote(q)}&per_page={max(3, n)}&safesearch=true&image_type=photo"))
        for h in d.get("hits", [])[:n]:
            out.append({"url": h["largeImageURL"], "ext": "jpg", "author": h["user"], "source": h["pageURL"], "license": "Pixabay Content License"})
    return out


OK_LIC = re.compile(r"^(public domain|pd|cc0|cc by(-sa)? [0-9.]+)$", re.I)


def commons(q, kind, n):
    if kind == "video":
        return []
    p = {"action": "query", "format": "json", "generator": "search", "gsrsearch": f"{q} filetype:bitmap", "gsrnamespace": 6,
         "gsrlimit": 20, "prop": "imageinfo", "iiprop": "url|extmetadata|size", "iiurlwidth": 1600}
    d = json.loads(get("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(p)))
    out = []
    for pg in sorted(d.get("query", {}).get("pages", {}).values(), key=lambda x: x.get("index", 0)):
        ii = (pg.get("imageinfo") or [{}])[0]; md = ii.get("extmetadata", {})
        lic = md.get("LicenseShortName", {}).get("value", "")
        if not OK_LIC.match(lic.strip()) or ii.get("width", 0) < 1000:
            continue
        author = re.sub("<[^>]+>", "", md.get("Artist", {}).get("value", "unbekannt")).strip()
        out.append({"url": ii.get("thumburl") or ii["url"], "ext": "jpg", "author": author, "source": ii.get("descriptionurl"), "license": lic})
        if len(out) >= n:
            break
    return out


def main():
    reqs = json.load(open(REQ)) if os.path.exists(REQ) else []
    pk, xk = os.environ.get("PEXELS_KEY"), os.environ.get("PIXABAY_KEY")
    for r in reqs:
        d = os.path.join(ROOT, "assets", r["key"])
        if os.path.exists(os.path.join(d, "credits.json")):
            continue
        os.makedirs(d, exist_ok=True)
        n, kind, q = r.get("n", 4), r.get("kind", "photo"), r["query"]
        items = []
        for name, fn in (("pexels", lambda: pexels(q, kind, n, pk) if pk else []),
                         ("pixabay", lambda: pixabay(q, kind, n, xk) if xk else []),
                         ("commons", lambda: commons(q, kind, n))):
            try:
                items = fn()
            except Exception as e:
                print("Fehler", name, r["key"], e)
            if items:
                for it in items: it["provider"] = name
                break
        credits = []
        for i, it in enumerate(items[:n]):
            fn = f"{i + 1:02d}.{it['ext']}"
            try:
                save(it["url"], os.path.join(d, fn)); credits.append({**it, "file": fn}); print("ok", r["key"], fn, it["provider"])
            except Exception as e:
                print("Download-Fehler", it["url"], e)
        json.dump({"query": q, "kind": kind, "items": credits}, open(os.path.join(d, "credits.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
