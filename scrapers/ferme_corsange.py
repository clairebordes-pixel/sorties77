"""
Scraper pour La Ferme Corsange — Bailly-Romainvilliers.

La page officielle (lafermecorsange.fr/agenda/) charge son programme en
JavaScript après coup (widget JetEngine + appel AJAX), ce qui la rend très
difficile à scraper avec une simple requête HTTP.

On passe donc par leur billetterie externe VosTickets, qui liste tout le
programme en texte brut, jusqu'à plusieurs mois à l'avance :
    https://www.vostickets.net/billet?id=LA_FERME_CORSANGE

Format observé dans le texte de la page (une fois aplati) :
    "SHERLOCK HOLMES ET LE SIGNE DES QUATRELe DIMANCHE 27 SEPTEMBRE 2026 à 15H00 ..."
c'est-à-dire : TITRE (en majuscules) + "Le" + JOUR + DATE + MOIS + ANNÉE + "à" + HEUREHMINUTE.
Le tout premier titre ("CARTE ABONNE") correspond à une carte d'abonnement,
pas à un vrai spectacle, et est donc ignoré.
"""
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common import Event, fetch, write_events

URL = "https://www.vostickets.net/billet?id=LA_FERME_CORSANGE"

MOIS = {
    "JANVIER": "01", "FEVRIER": "02", "FÉVRIER": "02", "MARS": "03",
    "AVRIL": "04", "MAI": "05", "JUIN": "06", "JUILLET": "07",
    "AOUT": "08", "AOÛT": "08", "SEPTEMBRE": "09", "OCTOBRE": "10",
    "NOVEMBRE": "11", "DECEMBRE": "12", "DÉCEMBRE": "12",
}

ENTRY_RE = re.compile(
    r"([A-ZÀ-Ÿ0-9][A-ZÀ-Ÿ0-9\s'\-]{1,60}?)Le\s*[A-ZÀ-Ÿ]+\s+(\d{1,2})\s+([A-ZÀ-Ÿ]+)\s+(\d{4})\s+à\s+(\d{1,2})H(\d{2})",
    re.IGNORECASE,
)

SKIP_HINTS = ("abonne", "carte")
ATELIER_HINTS = ("atelier",)
CIRQUE_HINTS = ("cirque",)


def _guess_type(title: str) -> str:
    t = title.lower()
    if any(h in t for h in ATELIER_HINTS):
        return "atelier"
    if any(h in t for h in CIRQUE_HINTS):
        return "cirque"
    return "spectacle"


def scrape():
    from bs4 import BeautifulSoup

    html = fetch(URL)
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    print(f"[diagnostic] taille du texte extrait : {len(text)} caractères")

    events = []
    for m in ENTRY_RE.finditer(text):
        title_raw, day, month, year, hh, mm = m.groups()
        title = re.sub(r"\s+", " ", title_raw).strip().title()
        if any(h in title.lower() for h in SKIP_HINTS):
            continue
        month_code = MOIS.get(month.upper())
        if not month_code:
            continue
        date = f"{year}-{month_code}-{int(day):02d}"
        time = f"{int(hh)}h{mm}"

        events.append(
            Event(
                date=date,
                time=time,
                title=title,
                type=_guess_type(title),
                venue="La Ferme Corsange",
                city="Bailly-Romainvilliers",
                source_url=URL,
            )
        )
    print(f"[diagnostic] nombre d'événements trouvés : {len(events)}")
    return events


if __name__ == "__main__":
    write_events(scrape(), "output/ferme_corsange.json")
