"""Deutschen Sprechtext für die Stimmkopie aufbereiten: Zahlen ausschreiben, Abkürzungen auflösen, Aussprache-Lexikon."""
import re
from num2words import num2words

LEX = {  # Schreibung -> Aussprache (Lautschrift, die das Modell richtig spricht)
    "Lp(a)HORIZON": "El-Pe-A-Horizon", "Lp(a)": "El-Pe-A", "vs.": "gegenüber", "Lipoprotein(a)": "Lipoprotein A", "LDL": "El-De-El", "HDL": "Ha-De-El",
    "KI": "Ka-I", "EU": "E-U", "EMA": "E-M-A", "FDA": "F-D-A", "WHO": "W-H-O", "RKI": "R-K-I", "CRISPR": "Krisper",
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
    "EKG": "E-Ka-Ge", "Smartwatches": "Smart-wotsches", "Smartwatch": "Smart-wotsch", "die 112": "die eins eins zwei", "Vorhofflimmern": "Vorhof-flimmern",
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
