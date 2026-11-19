# Stimme Dr. Atalay (KI-Nachbildung, autorisiert) – Version 5, 19.11.2026

Einrichtung (CPU reicht, ca. 10 Min.):
```
uv venv -p 3.11 cbx && . cbx/bin/activate
uv pip install chatterbox-tts faster-whisper noisereduce soundfile num2words "setuptools<81"
```
(PyTorch-Index download.pytorch.org ist im Sandbox-Proxy gesperrt → normales PyPI verwenden.)

Erzeugen: `python voice/gen_voice.py lines.json out_dir voice/ref.wav`
- lines.json: `[{"id":"s1","say":"Gesprochener Text","check":"Text wie er erkannt werden soll"}]`
- GENAU EIN Eintrag (1–2 Sätze) pro Prozess aufrufen – mehr führt bei 8 GB RAM zum Absturz (OOM). Für lange Texte eine Schleife über einzelne JSON-Dateien.
- Jeder Eintrag = ein kleiner Absatz (1–2 Sätze); das ergibt eine natürlichere Satzmelodie als Einzelsätze.
- Ergebnis: out_dir/<id>.wav (24 kHz, Pausen > 0,35 s auf 0,30 s gekürzt, Tempo ×1,12 per Rubberband, Sprecher-Klangkette, −16 LUFS); zwischen Absätzen 0,38 s Stille einfügen und report.json (Erkennungs-Score je Zeile; < 0,85 prüfen).
- Aussprache: schwierige Wörter lautschriftlich in "say" (z. B. „Kolesterin“, „Ell-Pe-A“), Original in "check".
- Hinweis in Video/Text: „Stimme: KI-Nachbildung von Dr. G. Atalay, autorisiert.“
- Referenz ref.wav: Aufnahme Dr. Atalay 15.11.2026, Ausschnitt 18,4–35,7 s, Hochpass + leichte Entrauschung.

## Version 5 (19.11.2026, nach Rückmeldung „künstlich, abgehackt“)
- KEINE Schnitte in den Pausen, KEINE Zeitdehnung mehr (das hat abgehackt geklungen). Nur Anfang/Ende getrimmt, sanfte Klangkette.
- Tempo und Ausdruck über das Modell: EXAG 0,7, CFG 0,7 (Test mit 8 Kombinationen: zügig ~140 Wörter/Min, Erkennung 98 %).
- Text nur noch als "text" angeben – prep_de.py schreibt Zahlen aus, löst Abkürzungen auf und setzt die Aussprachehilfen (LEX erweitern!).
- Cholesterin NICHT umschreiben (Original wird am besten gesprochen). Schwierige Arzneinamen (z. B. Pelacarsen) im Sprechtext möglichst umschreiben („ein neues Medikament“), Name nur in der Einblendung.
- Zwischen Szenen 0,42 s Stille.
