"""
Scraper pour La Ferme du Buisson — Noisiel.
Page cible : https://www.lafermedubuisson.com/programme?subsections=spectacles

Ne garde que la section "spectacles" (le site mélange cinéma et spectacles) :
on ignore tout bloc dont le texte contient des indices de séance de cinéma
("VOST", "salle 1", etc.) pour limiter le bruit — à affiner une fois testé
en conditions réelles.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common import Event, fetch, parse_date_fr, parse_time_fr, write_events

URL = "https://www.lafermedubuisson.com/programme?subsections=spectacles"
CINEMA_HINTS = ("vost", "vf", "salle 1", "salle 2", "séance")


def scrape():
    from bs4 import BeautifulSoup

    html = fetch(URL)
    soup = BeautifulSoup(html, "html.parser")
    events = []

    candidates = soup.select("article, [class*='card'], [class*='event']")
    seen_titles = set()
    for block in candidates:
        title_tag = block.find(["h2", "h3", "h4"])
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        if not title or title in seen_titles:
            continue

        text = block.get_text(" ", strip=True)
        if any(hint in text.lower() for hint in CINEMA_HINTS):
            continue

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
                type="cirque",
                venue="Ferme du Buisson",
                city="Noisiel",
                source_url=URL,
            )
        )
    return events


if __name__ == "__main__":
    write_events(scrape(), "output/ferme_du_buisson.json")
