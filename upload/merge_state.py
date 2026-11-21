"""Speichert upload/state.json robust, auch wenn parallel andere Commits kamen.

Ablauf: Eigene Änderungen (gegenüber dem Stand beim Checkout) werden auf den
neuesten Stand von origin/main gelegt. Schlüssel, die nur andere Läufe geändert
haben, bleiben erhalten. Bis zu 6 Versuche.
"""
import json, subprocess, sys, time

PATH = "upload/state.json"

def sh(*a, check=True):
    return subprocess.run(a, check=check, capture_output=True, text=True)

def load_rev(rev):
    r = sh("git", "show", f"{rev}:{PATH}", check=False)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}

mine = json.load(open(PATH, encoding="utf-8"))
base = load_rev("HEAD")
changed = {k: v for k, v in mine.items() if base.get(k) != v}
if not changed:
    print("Status unverändert – nichts zu speichern.")
    sys.exit(0)
print("Geänderte Einträge:", ", ".join(changed))

for attempt in range(1, 7):
    sh("git", "fetch", "-q", "origin", "main")
    sh("git", "reset", "-q", "--hard", "origin/main")
    latest = load_rev("HEAD")
    latest.update(changed)
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(latest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    sh("git", "add", PATH)
    if sh("git", "diff", "--cached", "--quiet", check=False).returncode == 0:
        print("Bereits auf dem neuesten Stand.")
        sys.exit(0)
    sh("git", "commit", "-q", "-m", "YouTube-Upload: Status aktualisiert")
    if sh("git", "push", "-q", "origin", "HEAD:main", check=False).returncode == 0:
        print(f"Status gespeichert (Versuch {attempt}).")
        sys.exit(0)
    print(f"Push abgelehnt, neuer Versuch {attempt + 1} …")
    time.sleep(3 * attempt)

print("FEHLER: Status konnte nicht gespeichert werden.", file=sys.stderr)
sys.exit(1)
