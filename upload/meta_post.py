#!/usr/bin/env python3
"""Facebook-Seite + Instagram automatisch bespielen (Meta Graph API).

Liest social/queue.json. Jeder Eintrag:
  key          eindeutiger Schlüssel
  publish_at   ISO-Zeit UTC; vorher wird nichts gepostet
  fb_message   Text für die Facebook-Seite (Link wird als Vorschau angehängt)
  link         Beitrags-URL
  image_url    öffentliches Bild (JPEG/PNG) für Instagram-Bildpost (optional)
  video_url    öffentliches MP4 (9:16) für Instagram-Reel (optional, hat Vorrang vor image_url)
  ig_caption   Instagram-Text (Links sind dort nicht klickbar -> "Link in Bio")
Status in social/state.json. Secrets: META_PAGE_ID, META_PAGE_TOKEN.
Ohne Secrets beendet sich das Skript ohne Fehler.
"""
import json, os, sys, time, datetime as dt, urllib.request, urllib.parse, urllib.error

API = "https://graph.facebook.com/v21.0"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "social", "queue.json")
STATE = os.path.join(ROOT, "social", "state.json")
MAX_PER_RUN = 3


def call(method, path, **params):
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(url + "?" + data.decode())
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code} {path}: {body[:400]}")


def main():
    page, tok = os.environ.get("META_PAGE_ID"), os.environ.get("META_PAGE_TOKEN")
    if not page or not tok:
        print("META_PAGE_ID/META_PAGE_TOKEN fehlen – nichts zu tun.")
        return
    queue = json.load(open(QUEUE)) if os.path.exists(QUEUE) else []
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    ig = state.get("_ig_user_id")
    if not ig:
        info = call("GET", page, fields="instagram_business_account,name", access_token=tok)
        ig = (info.get("instagram_business_account") or {}).get("id")
        state["_ig_user_id"] = ig or ""
        print("Seite:", info.get("name"), "| Instagram-ID:", ig or "keins verbunden")
    now = dt.datetime.now(dt.timezone.utc)
    done = 0
    for e in queue:
        if e.get("skip"):
            continue
        if done >= MAX_PER_RUN:
            break
        k = e["key"]; st = state.setdefault(k, {})
        if dt.datetime.fromisoformat(e["publish_at"].replace("Z", "+00:00")) > now:
            continue
        try:
            if not st.get("fb_id") and e.get("fb_message"):
                r = call("POST", f"{page}/feed", message=e["fb_message"], link=e.get("link", ""), access_token=tok)
                st["fb_id"] = r.get("id"); st["fb_at"] = now.isoformat(); print("FB ok", k, st["fb_id"]); done += 1
            if ig and not st.get("ig_id") and (e.get("video_url") or e.get("image_url")):
                if e.get("video_url"):
                    c = call("POST", f"{ig}/media", media_type="REELS", video_url=e["video_url"], caption=e.get("ig_caption", ""), share_to_feed="true", access_token=tok)
                else:
                    c = call("POST", f"{ig}/media", image_url=e["image_url"], caption=e.get("ig_caption", ""), access_token=tok)
                cid = c["id"]
                for _ in range(40):  # Verarbeitung abwarten (Reels brauchen Zeit)
                    s = call("GET", cid, fields="status_code", access_token=tok).get("status_code")
                    if s in ("FINISHED", None):
                        break
                    if s == "ERROR":
                        raise RuntimeError("Instagram-Verarbeitung fehlgeschlagen")
                    time.sleep(15)
                p = call("POST", f"{ig}/media_publish", creation_id=cid, access_token=tok)
                st["ig_id"] = p.get("id"); st["ig_at"] = now.isoformat(); print("IG ok", k, st["ig_id"]); done += 1
            st.pop("last_error", None)
        except Exception as ex:
            st["last_error"] = str(ex)[:500]; print("Fehler", k, ex)
            if "(#4)" in str(ex) or "(#32)" in str(ex) or "limit" in str(ex).lower():
                break  # Ratenlimit: beim nächsten Lauf weiter
    json.dump(state, open(STATE, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
