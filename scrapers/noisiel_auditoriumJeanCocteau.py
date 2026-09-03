"""
Scraper pour l'Auditorium Jean-Cocteau — Noisiel.
Source : fiche Apidae Tourisme (tourisme-pvm.fr).

La logique de scraping est partagée avec d'autres salles utilisant Apidae
(voir common.scrape_apidae_fiche) — ce fichier ne fait que fournir l'URL,
le nom de la salle et la ville. Pour ajouter une nouvelle salle Apidae,
créer un nouveau fichier sur ce modèle plutôt que de modifier celui-ci.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common import scrape_apidae_fiche, write_events

URL = "https://www.tourisme-pvm.fr/apidae/fiche/4786972/auditorium-jean-cocteau"
VENUE = "Auditorium Jean-Cocteau"
CITY = "Noisiel"


def scrape():
    return scrape_apidae_fiche(URL, VENUE, CITY)


if __name__ == "__main__":
    write_events(scrape(), "output/noisiel_auditoriumJeanCocteau.json")
