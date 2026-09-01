"""
Scraper pour Les Cuizines — Chelles.
Page cible : https://www.lescuizines.fr/events/

Ce site utilise très probablement un plugin d'événements WordPress
(The Events Calendar ou équivalent), qui structure généralement chaque
événement dans un article avec un titre (h2/h3) et une date associée.
Les sélecteurs ci-dessous sont un point de départ raisonnable ; ouvre les
outils de développement du navigateur (clic droit -> Inspecter) sur la page
si rien ne remonte, pour ajuster les noms de classes.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common import Event, fetch, parse_date_fr, parse_time_fr, write_events

URL = "https://www.lescuizines.fr/events/"


def scrape():
    from bs4 import BeautifulSoup

    html = fetch(URL)
    soup = BeautifulSoup(html, "html.parser")
    events = []

    # Hypothèse : chaque événement est dans un conteneur <article> ou une
    # div avec une classe contenant "event" (très courant chez The Events
    # Calendar : "tribe-events-calendar-list__event")
    candidates = soup.select(
        "article, [class*='event'], [class*='tribe-events']"
    )

    seen_titles = set()
    for block in candidates:
        title_tag = block.find(["h2", "h3", "h4"])
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        if not title or title in seen_titles:
            continue

        text = block.get_text(" ", strip=True)
        date = parse_date_fr(text)
        if not date:
            continue
        time = parse_time_fr(text)

        seen_titles.add(title)
        events.append(
            Event(
                date=date,
                time=time,
                title=title,
                type="concert",
                venue="Les Cuizines",
                city="Chelles",
                source_url=URL,
            )
        )
    return events


if __name__ == "__main__":
    write_events(scrape(), "output/lescuizines.json")
