"""Liest Kanal- und Videozahlen (YouTube Data API, nur lesend) und schreibt upload/stats.json."""
import os, json, datetime as dt
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
c = Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN"], client_id=os.environ["YT_CLIENT_ID"],
                client_secret=os.environ["YT_CLIENT_SECRET"], token_uri="https://oauth2.googleapis.com/token")
yt = build("youtube", "v3", credentials=c, cache_discovery=False)
ch = yt.channels().list(part="snippet,statistics,contentDetails", mine=True).execute()["items"][0]
up = ch["contentDetails"]["relatedPlaylists"]["uploads"]
ids, tok = [], None
while True:
    r = yt.playlistItems().list(part="contentDetails", playlistId=up, maxResults=50, pageToken=tok).execute()
    ids += [i["contentDetails"]["videoId"] for i in r["items"]]; tok = r.get("nextPageToken")
    if not tok: break
vids = []
for i in range(0, len(ids), 50):
    for v in yt.videos().list(part="snippet,statistics,status", id=",".join(ids[i:i+50])).execute()["items"]:
        s = v["statistics"]; vids.append(dict(id=v["id"], title=v["snippet"]["title"], published=v["snippet"]["publishedAt"],
            privacy=v["status"]["privacyStatus"], views=int(s.get("viewCount", 0)), likes=int(s.get("likeCount", 0)), comments=int(s.get("commentCount", 0))))
out = dict(stand=dt.datetime.utcnow().isoformat(timespec="minutes") + "Z", kanal=ch["snippet"]["title"],
           abonnenten=int(ch["statistics"].get("subscriberCount", 0)), aufrufe_gesamt=int(ch["statistics"].get("viewCount", 0)),
           videos_gesamt=int(ch["statistics"].get("videoCount", 0)), videos=sorted(vids, key=lambda x: -x["views"]))
json.dump(out, open(os.path.join(os.path.dirname(__file__), "stats.json"), "w"), ensure_ascii=False, indent=1)
print(out["kanal"], out["abonnenten"], out["aufrufe_gesamt"], out["videos_gesamt"])
