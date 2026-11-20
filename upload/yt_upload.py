"""Automatischer YouTube-Upload für Medizin Aktuell (läuft in GitHub Actions).

Liest upload/queue.json und
  1. lädt jedes Video, das noch nicht hochgeladen ist, hoch – mit Termin (publishAt),
     YouTube veröffentlicht es dann selbst zur geplanten Zeit;
  2. schreibt den ersten Kommentar, sobald das Video öffentlich ist.
Ergebnis (YouTube-IDs) steht in upload/state.json.

Zugangsdaten kommen ausschließlich aus GitHub-Secrets:
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
"""
import datetime as dt
import json
import os
import sys
import tempfile
import urllib.request

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

HERE = os.path.dirname(os.path.abspath(__file__))
QUEUE = os.path.join(HERE, "queue.json")
STATE = os.path.join(HERE, "state.json")
MAX_UPLOADS_PER_RUN = int(os.environ.get("MAX_UPLOADS_PER_RUN", "6"))


def now():
    return dt.datetime.now(dt.timezone.utc)


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save_state(state):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


def youtube():
    need = ["YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"]
    if not all(os.environ.get(k) for k in need):
        print("Secrets fehlen noch – nichts zu tun.")
        sys.exit(0)
    creds = Credentials(
        None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.force-ssl"],
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload(yt, e):
    publish_at = dt.datetime.fromisoformat(e["publish_at"].replace("Z", "+00:00"))
    status = {
        "selfDeclaredMadeForKids": False,
        "containsSyntheticMedia": True,  # KI-Stimme
        "embeddable": True,
    }
    # In der Vergangenheit -> sofort öffentlich; sonst privat mit Termin
    if publish_at <= now() + dt.timedelta(minutes=20):
        status["privacyStatus"] = "public"
    else:
        status["privacyStatus"] = "private"
        status["publishAt"] = e["publish_at"]
    body = {
        "snippet": {
            "title": e["title"],
            "description": e["description"],
            "tags": e.get("tags", []),
            "categoryId": e.get("category_id", "27"),
            "defaultLanguage": "de",
            "defaultAudioLanguage": "de",
        },
        "status": status,
    }
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "video.mp4")
        src = e.get("video_file")
        if src:
            path = os.path.join(HERE, "..", src)
        else:
            urllib.request.urlretrieve(e["video_url"], path)
        media = MediaFileUpload(path, mimetype="video/mp4", chunksize=-1, resumable=True)
        req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
        resp = None
        while resp is None:
            _, resp = req.next_chunk()
    return resp["id"], status["privacyStatus"]


def unlist(yt, video_id):
    """Altes Video auf "nicht gelistet" stellen (nicht löschen) – für ersetzte Fassungen."""
    r = yt.videos().list(part="status", id=video_id).execute()
    if not r.get("items"):
        return False
    st = r["items"][0]["status"]
    # Geplante (private) Fassung bleibt privat und verliert nur den Termin; öffentliche wird "nicht gelistet"
    if st.get("privacyStatus") != "private":
        st["privacyStatus"] = "unlisted"
    st.pop("publishAt", None)
    yt.videos().update(part="status", body={"id": video_id, "status": st}).execute()
    return True


def comment(yt, video_id, text):
    yt.commentThreads().insert(
        part="snippet",
        body={"snippet": {"videoId": video_id,
                          "topLevelComment": {"snippet": {"textOriginal": text}}}},
    ).execute()


def main():
    queue = load(QUEUE, [])
    state = load(STATE, {})
    yt = youtube()
    uploaded = 0
    for e in sorted(queue, key=lambda x: x["publish_at"]):
        s = state.setdefault(e["key"], {})
        if e.get("skip"):
            continue
        # Angehalten: geplantes Video bleibt privat (Termin entfernt), z. B. bis Neuauflage fertig ist
        if e.get("hold"):
            if s.get("video_id") and not s.get("held"):
                try:
                    unlist(yt, s["video_id"])
                    s["held"] = True
                    print(f"Angehalten (bleibt privat): {e['title']}")
                except HttpError as err:
                    print(f"Anhalten fehlgeschlagen {e['title']}: {err.resp.status}")
                save_state(state)
            continue
        # 1. Hochladen
        if "video_id" not in s and uploaded < MAX_UPLOADS_PER_RUN:
            try:
                vid, priv = upload(yt, e)
                s.update(video_id=vid, uploaded_at=now().isoformat(timespec="seconds"),
                         title=e["title"], publish_at=e["publish_at"])
                uploaded += 1
                print(f"Hochgeladen: {e['title']} -> https://youtu.be/{vid} ({priv})")
            except HttpError as err:
                s["last_error"] = str(err)[:300]
                print(f"FEHLER Upload {e['title']}: {err}")
                if err.resp.status in (403, 429):  # Kontingent erschöpft
                    break
            save_state(state)
        # 1b. Ersetzte alte Fassung auf "nicht gelistet" stellen (sobald neue öffentlich ist)
        if s.get("video_id") and e.get("replaces") and not s.get("replaced_done"):
            pub = dt.datetime.fromisoformat(e["publish_at"].replace("Z", "+00:00"))
            if pub <= now():
                try:
                    if unlist(yt, e["replaces"]):
                        print(f"Alte Fassung nicht gelistet: https://youtu.be/{e['replaces']}")
                    s["replaced_done"] = True
                except HttpError as err:
                    print(f"Alte Fassung noch nicht umgestellt: {err.resp.status}")
                save_state(state)
        # 2. Erster Kommentar, sobald veröffentlicht
        if s.get("video_id") and not s.get("comment_done") and e.get("first_comment"):
            pub = dt.datetime.fromisoformat(e["publish_at"].replace("Z", "+00:00"))
            if pub <= now():
                try:
                    comment(yt, s["video_id"], e["first_comment"])
                    s["comment_done"] = True
                    print(f"Kommentar gesetzt: {e['title']}")
                except HttpError as err:
                    print(f"Kommentar noch nicht möglich ({e['title']}): {err.resp.status}")
                save_state(state)
    save_state(state)


if __name__ == "__main__":
    main()
