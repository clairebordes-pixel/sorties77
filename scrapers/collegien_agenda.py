"""
Scraper pour l'agenda culture/sports/loisirs de la mairie de Collégien.
Page cible : https://collegien.fr/culture-sports-et-loisirs/agenda-culture-sports-et-loisirs
(paginée : ?page=2, ?page=3, ...)

La page mélange de VRAIES sorties (spectacles, concerts, expos...) et des
ateliers/services municipaux internes (Fabrique Citoyenne, ateliers séniors,
numériques...). On ne garde que les catégories qui ressemblent à des sorties
culturelles — voir CATEGORIES_A_GARDER ci-dessous, à ajuster si besoin.

Structure du texte observée par entrée (une fois la page aplatie en texte) :

    04 septembre
    17h30
    Événement, Festivités
    Festi'Rentrée
    Le rendez-vous de la rentrée à Collégien !
    Promenade Sylvie Mérigard

soit : date, heure, catégories (séparées par virgules), titre, description,
lieu — dans cet ordre, ligne par ligne.
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

DATE_LINE_RE = re.compile(r"^(\d{1,2})\s+(janvier|f[ée]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[ée]cembre)$", re.IGNORECASE)
TIME_LINE_RE = re.compile(r"^(\d{1,2})h(\d{0,2})$")
PAGE_COUNT_RE = re.compile(r"Page\s+\d+\s+sur\s+(\d+)", re.IGNORECASE)

# catégories qu'on garde : tout ce qui ressemble à une vraie sortie plutôt
# qu'à un service municipal interne. À ajuster si de nouvelles catégories
# pertinentes apparaissent sur le site.
CATEGORIES_A_GARDER = {
    "spectacle", "spectacle tout public", "musique", "concert",
    "festivités", "événement", "exposition", "film", "conférence",
    "lecture", "halloween", "visite",
}


def _year_for_month(month_num: int, today: date = None) -> int:
    today = today or date.today()
    # on part du principe que la page affiche les 12 prochains mois
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
    lines = [l.strip() for l in soup.get_text("\n").split("\n") if l.strip()]

    events = []
    i = 0
    n = len(lines)
    while i < n:
        date_m = DATE_LINE_RE.match(lines[i])
        if not date_m or i + 1 >= n:
            i += 1
            continue
        time_m = TIME_LINE_RE.match(lines[i + 1])
        if not time_m:
            i += 1
            continue

        day = int(date_m.group(1))
        month_num = MOIS[date_m.group(2).lower()]
        year = _year_for_month(month_num)
        event_date = f"{year:04d}-{month_num:02d}-{int(day):02d}"
        hh, mm = time_m.groups()
        time_str = f"{int(hh)}h{mm or '00'}"

        categories = [c.strip() for c in lines[i + 2].split(",")] if i + 2 < n else []
        title = lines[i + 3] if i + 3 < n else ""

        # on cherche où commence la PROCHAINE entrée (date+heure consécutives)
        # pour délimiter la fin de celle-ci ; le lieu est la dernière ligne
        # non vide juste avant.
        j = i + 4
        next_start = n
        while j + 1 < n:
            if DATE_LINE_RE.match(lines[j]) and TIME_LINE_RE.match(lines[j + 1]):
                next_start = j
                break
            j += 1
        location = lines[next_start - 1] if next_start - 1 > i + 3 else ""

        keep = any(c.lower() in CATEGORIES_A_GARDER for c in categories)
        if keep and title:
            events.append(
                Event(
                    date=event_date,
                    time=time_str,
                    title=title,
                    type=_guess_type(categories),
                    venue=location or VENUE_DEFAULT,
                    city=CITY,
                    source_url=BASE_URL,
                )
            )
        i = next_start if next_start > i else i + 1

    return events


def scrape():
    html = fetch(BASE_URL)
    print(f"[diagnostic] taille de la page 1 : {len(html)} caractères")

    m = PAGE_COUNT_RE.search(html)
    total_pages = int(m.group(1)) if m else 1
    total_pages = min(total_pages, 20)  # garde-fou
    print(f"[diagnostic] nombre de pages détectées : {total_pages}")

    events = _parse_page(html)
    for p in range(2, total_pages + 1):
        html = fetch(f"{BASE_URL}?page={p}")
        events.extend(_parse_page(html))

    print(f"[diagnostic] nombre d'événements retenus (après filtre catégories) : {len(events)}")
    return events


if __name__ == "__main__":
    write_events(scrape(), "output/collegien_agenda.json")
