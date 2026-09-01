"""
Scraper pour File7 — Magny-le-Hongre.
Page cible : https://file7.com/fr/programme/programme.html

Même logique générique que lescuizines.py : à ajuster une fois que tu as
inspecté le HTML réel de la page (clic droit -> Inspecter).
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common import Event, fetch, parse_date_fr, parse_time_fr, write_events

URL = "https://file7.com/fr/programme/programme.html"


def scrape():
    from bs4 import BeautifulSoup

    html = fetch(URL)
    soup = BeautifulSoup(html, "html.parser")
    events = []

    candidates = soup.select("article, [class*='event'], [class*='programme']")
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
                type="autre",
                venue="File7",
                city="Magny-le-Hongre",
                source_url=URL,
            )
        )
    return events


if __name__ == "__main__":
    write_events(scrape(), "output/file7.json")
