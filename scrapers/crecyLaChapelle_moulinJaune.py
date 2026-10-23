"""
Scraper pour Le Moulin Jaune — Crécy-la-Chapelle.
Les événements sont sur la billetterie Billetweb "multi-événements" :
https://www.billetweb.fr/multi_event.php?multi=33459&color=e3bd00

Structure (HTML rendu côté serveur) :
  <div class="multi_event_container ...">
    <img src="/files/event/150/<id>.jpg">
    <span class="multi_event_name_span">Titre</span>
    <div class="multi_event_date"><span class="text">Lun. 19 oct. 2026 au sam. 24 oct. 2026</span></div>
    <a class="naviguate" href="https://www.billetweb.fr/shop.php?event=...">Réserver</a>
  </div>

Le jardin n'ouvre que ponctuellement : la liste change au fil des saisons,
le scraper se met à jour tout seul quand de nouveaux événements sont publiés.
Les "bons cadeaux" ne sont pas des sorties : ignorés.
Pour une période (ex. "du 19 au 24 oct."), on affiche la date de début, ou
aujourd'hui si la période a déjà commencé, tant qu'elle n'est pas terminée.
"""
import re
import sys
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common import Event, fetch, parse_date_fr, write_events

URL = "https://www.billetweb.fr/multi_event.php?multi=33459&color=e3bd00"
BASE = "https://www.billetweb.fr"
VENUE = "Le Moulin Jaune"
CITY = "Crécy-la-Chapelle"

DATE_PART_RE = re.compile(r"\d{1,2}\s+[A-Za-zéèêûîôç]+\.?\s*\d{4}")
TIME_RE = re.compile(r"à\s+(\d{1,2})h(\d{2})")


def _guess_type(title: str) -> str:
    t = title.lower()
    if "concert" in t:
        return "concert"
    if "spectacle" in t:
        return "spectacle"
    return "atelier"


def parse_html(html: str, today: date = None):
    from bs4 import BeautifulSoup

    today = today or date.today()
    soup = BeautifulSoup(html, "html.parser")
    events = []
    for card in soup.select(".multi_event_container.filterable"):
        name = card.select_one(".multi_event_name_span")
        if not name:
            continue
        title = name.get_text(strip=True)
        if "bon cadeau" in title.lower():
            continue

        date_tag = card.select_one(".multi_event_date .text")
        date_text = date_tag.get_text(" ", strip=True) if date_tag else ""
        found = [parse_date_fr(m.group(0)) for m in DATE_PART_RE.finditer(date_text)]
        found = [d for d in found if d]
        if not found:
            continue
        start, end = found[0], found[-1]
        if end < today.isoformat():
            continue  # période terminée
        event_date = max(start, today.isoformat()) if end > start else start
        tm = TIME_RE.search(date_text)
        time_str = f"{int(tm.group(1))}h{tm.group(2)}" if tm else ""

        link_tag = card.select_one("a.naviguate")
        link = link_tag.get("href", URL) if link_tag else URL
        img = card.select_one(".multi_event_picture img")
        image_url = ""
        if img and img.get("src"):
            src = img["src"].split("?")[0]
            image_url = src if src.startswith("http") else BASE + src

        events.append(Event(
            date=event_date, time=time_str, title=title, type=_guess_type(title),
            venue=VENUE, city=CITY, source_url=link, image_url=image_url,
        ))
    return events


def scrape():
    html = fetch(URL)
    print(f"[diagnostic] taille de la page reçue : {len(html)} caractères")
    events = parse_html(html)
    print(f"[diagnostic] événements retenus : {len(events)}")
    return events


if __name__ == "__main__":
    write_events(scrape(), "output/crecyLaChapelle_moulinJaune.json")
