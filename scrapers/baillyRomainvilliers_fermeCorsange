"""
Scraper pour La Ferme Corsange — Bailly-Romainvilliers.

Le site officiel (lafermecorsange.fr/agenda/) charge son programme en
JavaScript (widget JetEngine + appel AJAX) — trop complexe à scraper
simplement. On passe donc par leur billetterie externe VosTickets :
    https://www.vostickets.net/billet?id=LA_FERME_CORSANGE

Structure réelle observée (inspectée le 31/08/2026) — chaque spectacle
est une carte de ce type :

  <div class="... ticket-mur-vignette-entiere"
       data-spectacle="32806"
       data-datePrem="20260927"   <- AAAAMMJJ, vide pour les non-spectacles
       data-dateDern="20260927"
       data-libStructure="LA FERME CORSANGE" ...>
    <img alt="affiche" src="https://vosbillets-images.s3.../....webp">
    <div name="titre">SHERLOCK HOLMES<br />ET LE SIGNE DES QUATRE</div>
    <div name="date">Le
        DIMANCHE 27 SEPTEMBRE 2026 à 15H00</div>
  </div>

Les "abonnements/duos" (cartes sans date, ex. "Duo INDIVIDUEL BAILLY")
ont un data-datePrem vide -> on les ignore : seules les cartes avec une
date exploitable sont de vrais spectacles programmés.
"""
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common import Event, fetch, write_events

URL = "https://www.vostickets.net/billet?id=LA_FERME_CORSANGE"

TIME_RE = re.compile(r"à\s*(\d{1,2})H(\d{2})", re.IGNORECASE)

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
    print(f"[diagnostic] taille de la page reçue : {len(html)} caractères")
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.ticket-mur-vignette-entiere")
    print(f"[diagnostic] nombre de cartes trouvées : {len(cards)}")

    events = []
    for card in cards:
        date_prem = card.get("data-dateprem", "").strip()
        if not date_prem or len(date_prem) != 8:
            continue  # pas de date = abonnement/duo, pas un spectacle daté

        date = f"{date_prem[0:4]}-{date_prem[4:6]}-{date_prem[6:8]}"

        title_tag = card.select_one("div[name='titre']")
        title = title_tag.get_text(" ", strip=True) if title_tag else "Spectacle"
        title = title.title() if title.isupper() else title

        date_tag = card.select_one("div[name='date']")
        time = ""
        if date_tag:
            m = TIME_RE.search(date_tag.get_text(" ", strip=True))
            if m:
                time = f"{int(m.group(1))}h{m.group(2)}"

        img_tag = card.select_one(".ticket-murImage img")
        image_url = img_tag.get("src", "") if img_tag else ""

        events.append(
            Event(
                date=date,
                time=time,
                title=title,
                type=_guess_type(title),
                venue="La Ferme Corsange",
                city="Bailly-Romainvilliers",
                source_url=URL,
                image_url=image_url,
            )
        )
    return events


if __name__ == "__main__":
    write_events(scrape(), "output/ferme_corsange.json")
