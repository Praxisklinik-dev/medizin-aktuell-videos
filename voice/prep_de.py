"""Deutschen Sprechtext für die Stimmkopie aufbereiten: Zahlen ausschreiben, Abkürzungen auflösen, Aussprache-Lexikon."""
import re
from num2words import num2words

LEX = {  # Schreibung -> Aussprache (Lautschrift, die das Modell richtig spricht)
    "Lp(a)HORIZON": "El-Pe-A-Horizon", "Lp(a)": "El-Pe-A", "vs.": "gegenüber", "Lipoprotein(a)": "Lipoprotein A", "LDL": "El-De-El", "HDL": "Ha-De-El",
    "KI": "Ka-I", "HIV": "Ha-I-Vau", "Abnehmspritze": "Abnehm-Spritze", "EU": "E-U", "EMA": "E-M-A", "FDA": "F-D-A", "WHO": "W-H-O", "RKI": "R-K-I", "CRISPR": "Krisper",
    "Pelacarsen": "Pelazarsen", "Olpasiran": "Olpasiran", "Retatrutid": "Reta-trutid", "Semaglutid": "Sema-glutid",
    "mg/dL": "Milligramm pro Deziliter", "mmol/L": "Millimol pro Liter", "nmol/L": "Nanomol pro Liter",
    "medizin-aktuell.eu": "medizin aktuell punkt e u", "z. B.": "zum Beispiel", "bzw.": "beziehungsweise", "ca.": "zirka",
    "Dr.": "Doktor", "Prof.": "Professor", "u. a.": "unter anderem", "d. h.": "das heißt", "NEJM": "New England Journal of Medicine",
    "Ezetimib": "Ezeti-mib", "Rosuvastatin": "Rosuva-statin",
    # Folge 2 Zukunft der Medizin (21.11.2026)
    "USA": "U-S-A", "US-": "U-S-", "ALS": "A-L-S", "Angioödem": "Angio-ödem", "Bradykinin": "Brady-kinin",
    "Locked-in-Syndrom": "Lockt-inn-Sündrom", "Seoul": "Se-ul", "Seattle": "Siättl", "Smartphone": "Smartfon",
    "Lymphdrüsenkrebs": "Lümf-drüsenkrebs", "Mammographien": "Mammografien",
    # Neuauflage Nr. 2 Laser-Geschichte (21.11.2026)
    "Maiman": "Mei-män", "Maser": "Meiser",
    # Neuauflage Nr. 3 EKG mit KI (21.11.2026)
    # Neuauflage Nr. 4 Medizin 2041 (21.11.2026)
    "Schweineniere": "Schweine-Niere", "Genschere": "Gen-Schere",
    # Neuauflage Nr. 5 Heimgeräte (21.11.2026)
    "Praxislaser": "Praxis-Laser", "Energiedichte": "Energie-Dichte", "Hautkontakt-Sensor": "Haut-Kontakt-Sensor", "IPL": "I-Pe-El",
    # Neuauflage Nr. 6 Spinat und Eisen (22.11.2026)
    "Oxalsäure": "Oxal-säure", "Polyphenole": "Poly-phenole", "Vitamin C": "Vitamin Zeh", "Kommafehler": "Komma-Fehler",
    # Neuauflage Nr. 7 KI-Medikamente (22.11.2026)
    "AlphaFold": "Alpha-Fold", "Placebo": "Plazebo", "Lungenfibrose": "Lungen-Fibrose",
    # Neuauflage Nr. 8 Antibiotika und Erkältung (22.11.2026)
    "Cochrane": "Kockrän",
    # Neuauflage Nr. 10 KI in der Pathologie (23.11.2026)
    "Gigabyte": "Giga-beit", "Krebsbefunde": "Krebs-Befunde", "Biopsien": "Bi-opsien", "Grundlagenmodelle": "Grundlagen-Modelle", "Schnittbilder": "Schnitt-Bilder",
    # Neuauflage Nr. 13 Fingerknacken (23.11.2026)
    "Gelenkflüssigkeit": "Gelenk-Flüssigkeit", "Gelenkflächen": "Gelenk-Flächen", "Langzeitstudien": "Langzeit-Studien", "Hohlraum": "Hohl-Raum",
    "EKG": "E-Ka-Ge", "Smartwatches": "Smart-wotsches", "Smartwatch": "Smart-wotsch", "die 112": "die eins eins zwei", "Vorhofflimmern": "Vorhof-flimmern",
    # Neuauflage Nr. 15 Pigmentflecken lasern (24.11.2026)
    "Dermatoskop": "Dermato-skop", "Lichtschutzfaktor": "Licht-schutz-faktor", "Pigmentflecken": "Pigment-Flecken", "Altersfleck": "Alters-Fleck", "weglasern": "weg-lasern", "Vitamin-C-": "Vitamin-Zeh-",
    # Neuauflage Nr. 16 Kortison in Hautcremes (24.11.2026)
    "Hautcremes": "Haut-Cremes", "Hautcreme": "Haut-Creme", "kortisonfreie": "kortison-freie", "Dehnungsstreifen": "Dehnungs-Streifen", "Online-Shops": "Onlein-Schops", "verschreibungspflichtigen": "verschreibungs-pflichtigen", "Stichprobe": "Stich-Probe",
    # Neuauflage Nr. 17 Daumenbruch (24.11.2026)
    "Bennett": "Bännett", "Daumensattelgelenk": "Daumen-Sattel-Gelenk", "Bruchstücken": "Bruch-Stücken", "Bruchstücke": "Bruch-Stücke", "Gelenkfläche": "Gelenk-Fläche", "Gelenkbrüchen": "Gelenk-Brüchen", "Gelenkbrüche": "Gelenk-Brüche", "Röntgenbild": "Röntgen-Bild", "ein CT": "ein Zeh-Teh", "Winterstein-Bruch": "Winterstein-Bruch",
    # Neuauflage Nr. 19 Zell-Verjüngung am Auge (25.11.2026)
    "Yamanaka-Faktoren": "Jamanaka-Faktoren", "Epigenom": "Epi-Genom", "Sehnerven": "Seh-Nerven", "Sehnerv": "Seh-Nerv", "Sehnerv-Infarkt": "Seh-Nerv-Infarkt", "Gesichtsfeld": "Gesichts-Feld", "Kontrollgruppe": "Kontroll-Gruppe", "Augenpraxis": "Augen-Praxis",
    # Neuauflage Nr. 20 selektive Photothermolyse (25.11.2026)
    "Photothermolyse": "Foto-Thermo-Lyse", "Wellenlänge": "Wellen-Länge", "Blutgefäß": "Blut-Gefäß", "Blutfarbstoff": "Blut-Farbstoff", "Tattoofarbe": "Tättu-Farbe", "Tattoos": "Tättus", "Lichtpuls": "Licht-Puls", "Gefäßlaser": "Gefäß-Laser", "Laser-Haarentfernung": "Laser-Haar-Entfernung", "Pigmentstörungen": "Pigment-Störungen", "Laserbehandlung": "Laser-Behandlung", "Tätowierfarbe": "Tätowier-Farbe", "Haarentfernung": "Haar-Entfernung",
    # Neuauflage Nr. 21 Grapefruit und Tabletten (25.11.2026)
    "Pomelo": "Pomelo", "Bitterorange": "Bitter-Orange", "Cholesterinsenker": "Cholesterin-Senker", "Wirkstoffe": "Wirk-Stoffe", "Wirkstoff": "Wirk-Stoff", "Mindestmenge": "Mindest-Menge", "Muskelschäden": "Muskel-Schäden", "Nierenversagen": "Nieren-Versagen", "Wechselwirkung": "Wechsel-Wirkung",
    # Neuauflage Nr. 23 Hyaluronsäure zum Trinken (26.11.2026)
    "Hyaluronsäure": "Hüalu-ron-säure", "Hautfeuchtigkeit": "Haut-Feuchtigkeit", "Hauttypen": "Haut-Typen", "Basispflege": "Basis-Pflege", "Sonnenschutz": "Sonnen-Schutz", "Unterarm": "Unter-Arm",
    # Neuauflage Nr. 25 OP-Roboter (26.11.2026)
    "OP-Robotern": "O-Pe-Robotern", "OP-Videos": "O-Pe-Videos", "Roboter-OP": "Roboter-O-Pe", "Gallenblasen": "Gallen-Blasen", "Gallenblase": "Gallen-Blase", "Forschungsroboter": "Forschungs-Roboter", "Baltimore": "Baltimor", "in 3D": "in drei-D", "Einzelschritte": "Einzel-Schritte",
    # Neuauflage Nr. 26 ChatGPT und Symptome (27.11.2026)
    "ChatGPT": "Tschätt-Dschi-Pi-Ti", "OpenAI": "Open-Ei-Ei", "Chatbots": "Tschätt-Bots", "Chatbot": "Tschätt-Bot", "Oxford-Studie": "Oxford-Studie", "Arztbrief": "Arzt-Brief", "Arztgespräch": "Arzt-Gespräch", "Arzttermin": "Arzt-Termin", "Lähmungen": "Lähmungen",
    # Neuauflage Nr. 27 Baby KJ / Gen-Schere (27.11.2026)
    "Baby KJ": "Bäibi Ka-Jot", "KJ": "Ka-Jot", "Philadelphia": "Filadelfia", "Neugeborenen-Screening": "Neugeborenen-Skrining", "Zielsequenz": "Ziel-Sequenz", "Leitlinienentwurf": "Leitlinien-Entwurf", "Stoffwechselstörung": "Stoffwechsel-Störung", "Langzeitdaten": "Langzeit-Daten",
    # Neuauflage Nr. 28 KI am Laser (27.11.2026)
    "CE-Kennzeichnung": "Ze-E-Kennzeichnung", "Hautfotos": "Haut-Fotos", "Medizinprodukten": "Medizin-Produkten", "Medizinprodukt": "Medizin-Produkt", "Hochrisiko": "Hoch-Risiko", "Gesundheitsdaten": "Gesundheits-Daten", "Strahlenschutz": "Strahlen-Schutz", "Laser-Einstellung": "Laser-Einstellung",
}


def year(m):
    return num2words(int(m.group(0)), lang="de", to="year")


def num(m):
    s = m.group(0).replace(".", "").replace(",", ".")
    try:
        if "." in s:
            a, b = s.split(".")
            return num2words(int(a), lang="de") + " Komma " + " ".join(num2words(int(c), lang="de") for c in b)
        return num2words(int(s), lang="de")
    except Exception:
        return m.group(0)


def prep(t):
    for k in sorted(LEX, key=len, reverse=True):
        t = t.replace(k, LEX[k])
    t = re.sub(r"(\d)\s*%", r"\1 Prozent", t)
    t = re.sub(r"(\d)\s*×", r"\1 mal", t)
    t = re.sub(r"(?<![\d.,])1[1-9]\d\d(?![\d.,]\d)", year, t)  # Jahreszahlen 1100–1999: neunzehnhundert…
    t = re.sub(r"\b(\d{1,3}(?:\.\d{3})+|\d+(?:,\d+)?)\b", num, t)
    t = t.replace(" – ", ", ").replace("–", " bis ").replace("„", "").replace("“", "")
    return re.sub(r"\s+", " ", t).strip()


if __name__ == "__main__":
    import sys
    print(prep(" ".join(sys.argv[1:])))
