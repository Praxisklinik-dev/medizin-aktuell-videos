# Shorts-Stil v3 (19.11.2026)
Echte, lizenzfreie Fotos (assets/, über Workflow „Bilder-Clips-holen“) mit Kamerafahrt und Überblendung, animierte
Infografik-Karten (hook, genes, gauge, check, study, cta – in short.html, Funktion vis()), Story-Fortschrittsbalken,
Wort-für-Wort-Untertitel, Musik mit Ducking und Übergangs-Sounds, Endkarte mit Abonnieren.
Ablauf: Stimme je Szene mit voice/gen_voice.py (ein Absatz pro Szene), dann `python3 render_v3/build.py data.json out.mp4`
(System-Python mit Playwright; Wortzeiten über cbx-Python + faster-whisper). Nur Fotos mit CC0/Public Domain/CC BY (kein BY-SA);
Urheber stehen im Bild (credit) und gehören in die Videobeschreibung.

## Neue Umgebung (z. B. geplante Aufgabe)
1. Stimme einrichten laut voice/README.md (venv „cbx“). Pfad zum cbx-Python über Umgebungsvariable `CBX_PY` angeben (Standard /home/claude/cbx/bin/python).
2. System-Python braucht soundfile, scipy, numpy: `pip install --break-system-packages soundfile scipy numpy` (Playwright/Chromium sind vorinstalliert).
3. data.json nach beispiel_lpa.json: je Szene id, text (Untertitel = gesprochener Text), audio (WAV 24 kHz), photo (assets/<key>/NN.jpg), credit, vis (hook|genes|gauge|check|study|cta mit Feldern wie im Beispiel), optional source.
4. Fotos: Eintrag in assets/requests.json, Workflow „fetch-assets“ starten (gh workflow run fetch-assets.yml), danach git pull. Nur CC0/PD/CC BY.
5. Rendern: `CBX_PY=… python3 render_v3/build.py data.json out.mp4` (~15 Min.), Einzelbilder mit ffmpeg prüfen.
