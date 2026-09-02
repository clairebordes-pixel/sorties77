"""
Scraper pour La Ferme du Buisson — Noisiel.
Page cible : https://www.lafermedubuisson.com/fr/programme?subsections=saison_26-27

Structure réelle observée (inspectée le 31/08/2026) :

  <div class="item content preview agenda ">
    <a href="/fr/bakana" class="item-content agenda" title="Bakana">
      <img class="img-box media" src="https://www.lafermedubuisson.com/media/cache/.../affiche.jpg" alt="...">
      <p class="genre">Cirque</p>                 <!-- parfois <a class="genre genre-link"> -->
      <div class="text">
        <p class="date">11.09.26 - 27.09.26</p>     <!-- ou "15.09.26 à 18h45", ou "25.09 - 26.09.26" -->
        <p class="title ">Bakana</p>
        <p class="subtitle">Das Arnak</p>
      </div>
    </a>
  </div>

Le site mélange spectacles ET séances de cinéma sur cette page : on ignore
tout ce qui est catégorisé "Cinéma"/"Opéra au cinéma" (ce n'est pas un
spectacle à proprement parler).

La date peut être une plage ("11.09.26 - 27.09.26") où la première date n'a
parfois pas d'année (ex "25.09 - 26.09.26" ou "10.10 - 24.01.27") : on
déduit l'année manquante à partir de la seconde date de la plage.
"""
import re
import sys
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common import Event, fetch, write_events

URL = "https://www.lafermedubuisson.com/fr/programme?subsections=saison_26-27"
BASE = "https://www.lafermedubuisson.com"

SKIP_GENRES = ("cinéma", "cinema", "opéra au cinéma", "opera au cinema")
GENRE_TYPE = {"cirque": "cirque", "atelier": "atelier", "musique": "concert"}

# ex: "11.09.26", "25.09", "18h45"
DATE_PART_RE = re.compile(
    r"(\d{1,2})\.(\d{1,2})(?:\.(\d{2}))?(?:\s*à\s*(\d{1,2})h(\d{2}))?",
    re.IGNORECASE,
)


def _guess_type(genre: str) -> str:
    return GENRE_TYPE.get(genre.lower(), "spectacle")


def scrape():
    from bs4 import BeautifulSoup

    html = fetch(URL)
    print(f"[diagnostic] taille de la page reçue : {len(html)} caractères")
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("div.item.content.preview.agenda")
    print(f"[diagnostic] nombre de cartes trouvées : {len(items)}")

    events = []
    for item in items:
        link = item.select_one("a.item-content")
        if not link:
            continue

        genre_tag = item.select_one("p.genre, a.genre")
        genre = genre_tag.get_text(strip=True) if genre_tag else ""
        if genre.lower() in SKIP_GENRES:
            continue

        title_tag = item.select_one("p.title")
        title = title_tag.get_text(strip=True) if title_tag else (link.get("title") or "Événement")

        date_tag = item.select_one("p.date")
        if not date_tag:
            continue
        date_text = date_tag.get_text(strip=True)

        parts = [p.strip() for p in date_text.split(" - ")]
        parsed = [DATE_PART_RE.search(p) for p in parts]
        parsed = [m.groups() for m in parsed if m]
        if not parsed:
            continue

        # année de référence : la dernière date qui en précise une
        base_year = None
        for g in reversed(parsed):
            if g[2]:
                base_year = int(g[2]) + 2000
                break
        if base_year is None:
            base_year = date.today().year

        day1, month1, yr1, h1, mi1 = parsed[0]
        year1 = int(yr1) + 2000 if yr1 else base_year
        if not yr1 and len(parsed) > 1:
            _, month2, *_ = parsed[-1]
            if int(month1) > int(month2):
                year1 = base_year - 1

        event_date = f"{year1:04d}-{int(month1):02d}-{int(day1):02d}"
        time = f"{int(h1)}h{mi1}" if h1 else ""

        display_title = title
        if len(parsed) > 1:
            day2, month2, *_ = parsed[-1]
            display_title = f"{title} (jusqu'au {int(day2):02d}/{int(month2):02d})"

        href = link.get("href", URL)
        if href and not href.startswith("http"):
            href = BASE + href

        img_tag = item.select_one("img.img-box")
        image_url = img_tag.get("src", "") if img_tag else ""

        events.append(
            Event(
                date=event_date,
                time=time,
                title=display_title,
                type=_guess_type(genre),
                venue="Ferme du Buisson",
                city="Noisiel",
                source_url=href,
                image_url=image_url,
            )
        )

    return events


if __name__ == "__main__":
    write_events(scrape(), "output/ferme_du_buisson.json")
