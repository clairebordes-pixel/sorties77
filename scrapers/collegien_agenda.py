"""
Scraper pour l'agenda culture/sports/loisirs de la mairie de Collégien.
Page cible : https://collegien.fr/culture-sports-et-loisirs/agenda-culture-sports-et-loisirs
(paginée : ?page=2, ?page=3, ...)

Structure réelle observée (inspectée le 03/09/2026) :

  <div class="w-layout-grid agenda-grid">
    <div class="agenda-card-img" style="background-image: url('...jpg')" onclick="window.location.href = '...';"></div>
    <div class="agenda-card-dates">
      <div class="text-block-2">10 septembre<br><span>14h00</span></div>
    </div>
    <div class="agenda-card-details">
      <div class="news-card-category">Atelier séniors, Fabrique Citoyenne</div>
      <h3 class="news-card-title">Atelier taïso et nutrition</h3>
      <p class="news-card-description"></p>
      <div class="loc-text">Fabrique citoyenne</div>
    </div>
    <!-- ...se répète par groupes de 3 divs (img, dates, details) pour
         chaque carte, tous en enfants directs du même conteneur -->
  </div>

La page mélange de VRAIES sorties (spectacles, concerts, expos...) et des
ateliers/services municipaux internes (Fabrique Citoyenne, ateliers séniors,
numériques...). On ne garde que les catégories qui ressemblent à des sorties
culturelles — voir CATEGORIES_A_GARDER ci-dessous, à ajuster si besoin.
"""
import re
import sys
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common import Event, fetch, write_events

BASE_URL = "https://collegien.fr/culture-sports-et-loisirs/agenda-culture-sports-et-loisirs"
VENUE_DEFAULT = "Ville de Collégien"
CITY = "Collégien"

MOIS = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "août": 8, "aout": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
}

DATE_RE = re.compile(
    r"(\d{1,2})\s+(janvier|f[ée]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[ée]cembre)",
    re.IGNORECASE,
)
TIME_RE = re.compile(r"(\d{1,2})h(\d{0,2})")
PAGE_COUNT_RE = re.compile(r"Page\s+\d+\s+sur\s+(\d+)", re.IGNORECASE)
URL_RE = re.compile(r"window\.location\.href\s*=\s*'([^']+)'")
BG_IMAGE_RE = re.compile(r"url\((['\"]?)(.*?)\1\)")

CATEGORIES_A_GARDER = {
    "spectacle", "spectacle tout public", "musique", "concert",
    "festivités", "événement", "exposition", "film", "conférence",
    "lecture", "halloween", "visite",
}


def _year_for_month(month_num: int, today: date = None) -> int:
    today = today or date.today()
    if month_num >= today.month:
        return today.year
    return today.year + 1


def _guess_type(categories):
    cats = {c.lower() for c in categories}
    if "concert" in cats or "musique" in cats:
        return "concert"
    return "spectacle"


def _parse_page(html: str):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    grid = soup.select_one(".agenda-grid")
    if not grid:
        return []

    children = grid.find_all("div", recursive=False)
    events = []

    for i in range(0, len(children) - 2, 3):
        img_div, dates_div, details_div = children[i], children[i + 1], children[i + 2]

        date_block = dates_div.select_one(".text-block-2")
        if not date_block:
            continue
        date_text = date_block.get_text(" ", strip=True)
        date_m = DATE_RE.search(date_text)
        time_m = TIME_RE.search(date_text)
        if not date_m:
            continue
        day = int(date_m.group(1))
        month_num = MOIS[date_m.group(2).lower()]
        year = _year_for_month(month_num)
        event_date = f"{year:04d}-{month_num:02d}-{int(day):02d}"
        time_str = f"{int(time_m.group(1))}h{time_m.group(2) or '00'}" if time_m else ""

        cat_tag = details_div.select_one(".news-card-category")
        categories = [c.strip() for c in cat_tag.get_text(strip=True).split(",")] if cat_tag else []

        title_tag = details_div.select_one(".news-card-title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        loc_tag = details_div.select_one(".loc-text")
        location = loc_tag.get_text(strip=True) if loc_tag else ""

        # lien : dans l'attribut onclick de n'importe lequel des 3 divs
        link = ""
        for div in (img_div, dates_div, details_div):
            onclick = div.get("onclick", "")
            m = URL_RE.search(onclick)
            if m:
                link = m.group(1)
                break

        # image de fond
        image_url = ""
        style = img_div.get("style", "")
        m = BG_IMAGE_RE.search(style)
        if m:
            image_url = m.group(2)

        if not (title and any(c.lower() in CATEGORIES_A_GARDER for c in categories)):
            continue

        events.append(
            Event(
                date=event_date,
                time=time_str,
                title=title,
                type=_guess_type(categories),
                venue=location or VENUE_DEFAULT,
                city=CITY,
                source_url=link or BASE_URL,
                image_url=image_url,
            )
        )

    return events


def scrape():
    html = fetch(BASE_URL)
    print(f"[diagnostic] taille de la page 1 : {len(html)} caractères")

    m = PAGE_COUNT_RE.search(html)
    total_pages = int(m.group(1)) if m else 1
    total_pages = min(total_pages, 20)
    print(f"[diagnostic] nombre de pages détectées : {total_pages}")

    from collections import Counter
    from bs4 import BeautifulSoup
    cat_counter = Counter()

    def _count_categories(page_html):
        soup = BeautifulSoup(page_html, "html.parser")
        cards = soup.select(".news-card-category")
        for tag in cards:
            for c in tag.get_text(strip=True).split(","):
                cat_counter[c.strip()] += 1
        return len(cards)

    events = _parse_page(html)
    n = _count_categories(html)
    print(f"[diagnostic] page 1 : {n} cartes trouvées")

    for p in range(2, total_pages + 1):
        html = fetch(f"{BASE_URL}?page={p}")
        n = _count_categories(html)
        print(f"[diagnostic] page {p} : {len(html)} caractères, {n} cartes trouvées")
        events.extend(_parse_page(html))

    print(f"[diagnostic] toutes catégories rencontrées (toutes pages) : {dict(cat_counter)}")
    print(f"[diagnostic] nombre d'événements retenus (après filtre catégories) : {len(events)}")
    return events


if __name__ == "__main__":
    write_events(scrape(), "output/collegien_agenda.json")
