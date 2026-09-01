"""
Scraper générique pour une fiche "événement" publiée via la plateforme
Apidae Tourisme (tourisme-pvm.fr, marneetgondoire-tourisme.fr, etc.)

Ces fiches ne listent en général qu'UNE seule date (ou une série de dates
répétées) par page, contrairement au Millésime qui liste toute une saison.
Il faut donc une entrée par événement/URL dans FICHES ci-dessous.

Pour trouver de nouvelles fiches : chercher sur le site de l'office de
tourisme concerné, ou via Google "site:tourisme-pvm.fr agenda".
"""
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common import Event, fetch, parse_date_fr, parse_time_fr, write_events

# Une entrée par lieu/fiche à surveiller.
FICHES = [
    {
        "url": "https://www.tourisme-pvm.fr/apidae/fiche/4786972/auditorium-jean-cocteau",
        "venue": "Auditorium Jean-Cocteau",
        "city": "Noisiel",
    },
    {
        "url": "https://www.marneetgondoire-tourisme.fr/fr/fiche/6665564/programmation-culturelle-espace-marc-brinon/",
        "venue": "Espace Marc Brinon",
        "city": "Saint-Thibault-des-Vignes",
    },
]


def scrape():
    from bs4 import BeautifulSoup

    events = []
    for fiche in FICHES:
        try:
            html = fetch(fiche["url"])
        except Exception as e:
            print(f"[!] Impossible de charger {fiche['url']} : {e}")
            continue

        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text("\n", strip=True)

        # Titre : première grosse balise de titre trouvée sur la page
        title_tag = soup.find(["h1", "h2"])
        title = title_tag.get_text(strip=True) if title_tag else fiche["venue"]

        # On cherche chaque occurrence "jour mois année" dans le texte de la page
        for line in text.split("\n"):
            date = parse_date_fr(line)
            if not date:
                continue
            time = parse_time_fr(line)
            events.append(
                Event(
                    date=date,
                    time=time,
                    title=title,
                    type="saison",
                    venue=fiche["venue"],
                    city=fiche["city"],
                    source_url=fiche["url"],
                )
            )
    return events


if __name__ == "__main__":
    write_events(scrape(), "output/apidae.json")
