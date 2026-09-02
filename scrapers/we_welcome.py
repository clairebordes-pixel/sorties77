"""
Scraper pour We Welcome — Lagny-sur-Marne.
Page cible : https://we-welcome.fr/programmation/

Structure réelle observée : la page est organisée par mois, chaque mois
étant un titre <h2> ("Septembre", "Octobre", ...), suivi d'une série de
liens <a> dont le TEXTE encode la date complète, ex :

    <a href="https://we-welcome.fr/reservation/leffet-papillon-taha-mansour-mentaliste/">
        11vendrediseptembre21:00
    </a>

soit : jour (11) + jour de semaine (vendredi) + mois (septembre) + heure (21:00).
Certains jours ont deux horaires collés (ex "10:3014:30") -> on crée un
événement par horaire. Le titre du spectacle est reconstruit à partir du
slug de l'URL (l'API HTML ne donne pas de titre affiché séparément à cet
endroit).

L'année n'apparaît jamais dans le texte : on part de l'année en cours à la
date d'exécution du script, et on l'incrémente si un mois "recule"
(ex: Décembre -> Janvier) d'un titre de section au suivant.
"""
import re
import sys
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common import Event, fetch, write_events

URL = "https://we-welcome.fr/programmation/"

MOIS = {
    "janvier": 1, "fevrier": 2, "février": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "aout": 8, "août": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12, "décembre": 12,
}
MOIS_NAMES = set(MOIS.keys())

# ex: "11vendrediseptembre21:00" ou "21mercredioctobre10:3014:30"
LINK_RE = re.compile(
    r"^(\d{1,2})\s*(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\s*"
    r"(janvier|f[ée]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[ée]cembre)"
    r"((?:\d{1,2}:\d{2})+)$",
    re.IGNORECASE,
)

ATELIER_HINTS = ("atelier", "stage", "cours")
CONCERT_HINTS = ("concert",)


def _title_from_slug(href: str) -> str:
    slug = href.rstrip("/").split("/")[-1]
    slug = re.sub(r"-\d+$", "", slug)  # enlève un suffixe numérique (doublon WP: "-2", "-4"...)
    slug = re.sub(r"[-_]+", " ", slug).strip()
    return slug.title() if slug else "Événement"


def _guess_type(title: str) -> str:
    t = title.lower()
    if any(h in t for h in ATELIER_HINTS):
        return "atelier"
    if any(h in t for h in CONCERT_HINTS):
        return "concert"
    return "spectacle"


def scrape():
    from bs4 import BeautifulSoup

    html = fetch(URL)
    soup = BeautifulSoup(html, "html.parser")
    print(f"[diagnostic] taille de la page reçue : {len(html)} caractères")

    events = []
    current_year = date.today().year
    prev_month_num = None

    for tag in soup.find_all(["h2", "a"]):
        text = tag.get_text(strip=True)

        if tag.name == "h2" and text.lower() in MOIS_NAMES:
            month_num = MOIS[text.lower()]
            if prev_month_num is not None and month_num < prev_month_num:
                current_year += 1
            prev_month_num = month_num
            continue

        if tag.name != "a":
            continue
        m = LINK_RE.match(text)
        if not m or prev_month_num is None:
            continue

        day, _dow, month_name, times_blob = m.groups()
        month_num = MOIS[month_name.lower()]
        href = tag.get("href", URL)
        title = _title_from_slug(href)

        for time_str in re.findall(r"\d{1,2}:\d{2}", times_blob):
            hh, mm = time_str.split(":")
            events.append(
                Event(
                    date=f"{current_year:04d}-{month_num:02d}-{int(day):02d}",
                    time=f"{int(hh)}h{mm}",
                    title=title,
                    type=_guess_type(title),
                    venue="We Welcome",
                    city="Lagny-sur-Marne",
                    source_url=href,
                )
            )

    print(f"[diagnostic] nombre d'événements trouvés : {len(events)}")
    return events


if __name__ == "__main__":
    write_events(scrape(), "output/we_welcome.json")
