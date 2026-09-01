"""
Scraper pour Le Millésime — Montévrain.
Page cible : https://www.montevrain.fr/millesime/

Structure observée : chaque événement est un bloc avec une image (dont le nom
de fichier reprend souvent le titre du spectacle), suivi d'une ligne en gras
du type "Vendredi 18 sept.26 | 20h30", suivie d'un lien "Billetterie".

Comme le site peut changer de structure HTML avec le temps, ce scraper
travaille sur le texte brut extrait de la page plutôt que sur des sélecteurs
CSS fragiles — à ajuster si la page est redesignée.
"""
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common import Event, fetch, parse_date_fr, parse_time_fr, write_events

URL = "https://www.montevrain.fr/millesime/"

# "Vendredi 18 sept.26 | 20h30"
LINE_RE = re.compile(
    r"([A-Za-zéû]+)\s+(\d{1,2}\s*[a-zéû]+\.?\s*'?\d{2,4})\s*\|\s*(\d{1,2}h\d{0,2})",
    re.IGNORECASE,
)


def scrape():
    from bs4 import BeautifulSoup

    html = fetch(URL)
    soup = BeautifulSoup(html, "html.parser")

    events = []
    # Chaque bloc spectacle est un <strong>/<b> contenant la ligne date | heure,
    # précédé d'une image dont l'attribut alt/src donne un indice du titre.
    for bold in soup.find_all(["strong", "b"]):
        text = bold.get_text(" ", strip=True)
        m = LINE_RE.search(text)
        if not m:
            continue
        _, date_part, time_part = m.groups()
        date = parse_date_fr(date_part)
        time = parse_time_fr(time_part)
        if not date:
            continue

        # Le titre : on cherche l'image la plus proche en remontant dans le DOM
        title = "Spectacle (titre à vérifier)"
        img = bold.find_previous("img")
        if img:
            src = img.get("src", "") or img.get("alt", "")
            stem = Path(src).stem
            stem = re.sub(r"[-_]+", " ", stem).strip()
            if stem:
                title = stem.title()

        events.append(
            Event(
                date=date,
                time=time,
                title=title,
                type="spectacle",
                venue="Le Millésime",
                city="Montévrain",
                source_url=URL,
            )
        )
    return events


if __name__ == "__main__":
    write_events(scrape(), "output/millesime.json")
