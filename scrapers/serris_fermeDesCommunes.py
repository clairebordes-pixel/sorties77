"""
Scraper pour La Ferme des Communes — Serris (site officiel, pas Fnac Spectacles).
Page cible (paginée, 4 pages) :
    https://www.fermedescommunes.fr/programmation-807.html
    https://www.fermedescommunes.fr/programmation-807/page-2.html
    https://www.fermedescommunes.fr/programmation-807/page-3.html
    https://www.fermedescommunes.fr/programmation-807/page-4.html

Structure réelle observée (inspectée le 10/09/2026, via texte aplati) :

    Le 05 déc.
    à 21:00  Salle de spectacle Alfred de Musset - 8, bd Robert Thiboust
    ## Mathieu Stepson
    Retrouvez le spectacle de Mathieu Stepson le samedi 5 décembre à 21h00.
    Tarif 24€ / 19€
    Tout public
    [Réserver](https://billetterie.seetickets.fr/mathieu-stepson-ferme-des-communes-serris-05-decembre-2026-...)

L'année n'est jamais écrite dans le texte affiché ("Le 05 déc.") mais elle
EST présente dans l'URL du lien "Réserver" (ex: "...-05-decembre-2026-...")
-> c'est cette URL qu'on utilise comme source fiable pour la date complète.
"""
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common import Event, fetch, write_events

BASE = "https://www.fermedescommunes.fr"
PAGES = [
    "/programmation-807.html",
    "/programmation-807/page-2.html",
    "/programmation-807/page-3.html",
    "/programmation-807/page-4.html",
]
VENUE_DEFAULT = "La Ferme des Communes"
CITY = "Serris"

MOIS = {
    "janvier": 1, "fevrier": 2, "février": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "aout": 8, "août": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12, "décembre": 12,
}

# ex: "...-05-decembre-2026-css5-..."
URL_DATE_RE = re.compile(
    r"-(\d{1,2})-(janvier|f[ée]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[ée]cembre)-(\d{4})-",
    re.IGNORECASE,
)
TIME_RE = re.compile(r"à\s*(\d{1,2})[:h](\d{2})")

CATEGORIES_CONNUES = {"musique", "théâtre", "theatre", "humour", "festival val de rire"}


def _guess_type(category: str) -> str:
    c = (category or "").lower()
    if "musique" in c:
        return "concert"
    return "spectacle"


def _scrape_page(url: str):
    from bs4 import BeautifulSoup

    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    events = []
    for link in soup.find_all("a", string=re.compile(r"^\s*Réserver\s*$", re.IGNORECASE)):
        href = link.get("href", "")
        m = URL_DATE_RE.search(href)
        if not m:
            continue
        day, month_name, year = m.groups()
        month_num = MOIS.get(month_name.lower())
        if not month_num:
            continue
        event_date = f"{int(year):04d}-{month_num:02d}-{int(day):02d}"

        # on remonte au bloc conteneur de cette entrée pour trouver le
        # titre (h2), l'heure et la catégorie
        block = link
        h2 = None
        for _ in range(6):
            if block.parent is None:
                break
            block = block.parent
            h2 = block.find("h2")
            if h2:
                break

        title = h2.get_text(strip=True) if h2 else "Événement"

        block_text = block.get_text(" ", strip=True) if block else ""
        time_m = TIME_RE.search(block_text)
        time = f"{int(time_m.group(1))}h{time_m.group(2)}" if time_m else ""

        category = ""
        for a in (block.find_all("a") if block else []):
            txt = a.get_text(strip=True)
            if txt.lower() in CATEGORIES_CONNUES:
                category = txt
                break

        detail_url = href
        title_link = h2.find("a") if h2 else None
        if title_link and title_link.get("href"):
            detail_url = title_link["href"]
            if detail_url.startswith("/"):
                detail_url = BASE + detail_url

        events.append(
            Event(
                date=event_date,
                time=time,
                title=title,
                type=_guess_type(category),
                venue=VENUE_DEFAULT,
                city=CITY,
                source_url=detail_url,
            )
        )
    return events


def scrape():
    all_events = []
    for path in PAGES:
        url = BASE + path
        events = _scrape_page(url)
        print(f"[diagnostic] {path} : {len(events)} événement(s)")
        all_events.extend(events)

    # dédoublonnage (au cas où une page listerait deux fois la même entrée)
    seen = set()
    unique = []
    for e in all_events:
        key = (e.date, e.title, e.source_url)
        if key in seen:
            continue
        seen.add(key)
        unique.append(e)

    print(f"[diagnostic] total après dédoublonnage : {len(unique)}")
    return unique


if __name__ == "__main__":
    write_events(scrape(), "output/serris_fermeDesCommunes.json")
