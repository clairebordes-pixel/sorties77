"""
Lance tous les scrapers disponibles et fusionne le résultat dans
output/events.json — le fichier que l'appli sorties77.html va charger.

Usage :
    python run_all.py
"""
import json
import traceback
from dataclasses import asdict
from pathlib import Path

from common import Event
from scrapers import (
    chelles_lesCuizines,
    magnyLeHongre_file7,
    noisiel_fermeDuBuisson,
    noisiel_auditoriumJeanCocteau,
    stThibaultDesVignes_centreCulturelMarcBrinon,
    baillyRomainvilliers_fermeCorsange,
    lagnySurMarne_weWelcome,
    noisiel_poleCulturelMichelLegrand,
)
# montevrain_leMillesime n'est plus scrapé automatiquement : le site
# bloque systématiquement les requêtes venant des serveurs GitHub
# (erreur 418). Son programme est maintenu à la main dans
# data/manual_events.json.

SCRAPERS = [
    ("Chelles — Les Cuizines", chelles_lesCuizines),
    ("Magny-le-Hongre — File7", magnyLeHongre_file7),
    ("Noisiel — Ferme du Buisson", noisiel_fermeDuBuisson),
    ("Noisiel — Auditorium Jean-Cocteau", noisiel_auditoriumJeanCocteau),
    ("Saint-Thibault-des-Vignes — Centre culturel / Marc Brinon", stThibaultDesVignes_centreCulturelMarcBrinon),
    ("Bailly Romainvilliers — La Ferme Corsange (via VosTickets)", baillyRomainvilliers_fermeCorsange),
    ("Lagny-sur-Marne — We Welcome", lagnySurMarne_weWelcome),
    ("Noisiel — Pôle culturel Michel-Legrand (billetterie)", noisiel_poleCulturelMichelLegrand),
]


def load_manual_events():
    """
    Charge les événements saisis à la main (data/manual_events.json).
    Utile pour les salles dont le site n'est pas automatisable
    (ex : Charles Vanel à Lagny, dont la billetterie est une appli
    JavaScript sans données exploitables côté serveur).
    Ce fichier n'est jamais généré par les scrapers -> à mettre à jour
    manuellement quand une salle publie une nouvelle plaquette.
    """
    path = Path("data/manual_events.json")
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return [Event(**item) for item in raw]


def main():
    all_events = []
    for label, module in SCRAPERS:
        print(f"--- {label} ---")
        try:
            events = module.scrape()
            print(f"    {len(events)} événement(s) trouvé(s)")
            all_events.extend(events)
        except Exception:
            print(f"    [!] échec du scraper : voir la trace ci-dessous")
            traceback.print_exc()

    print("--- Événements manuels (data/manual_events.json) ---")
    manual = load_manual_events()
    print(f"    {len(manual)} événement(s) chargé(s)")
    all_events.extend(manual)

    # dédoublonne sur (date, titre, lieu)
    seen = set()
    unique = []
    for e in all_events:
        key = (e.date, e.title, e.venue)
        if key in seen:
            continue
        seen.add(key)
        unique.append(e)

    unique.sort(key=lambda e: (e.date, e.venue))

    out_path = Path("output/events.json")
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump([asdict(e) for e in unique], f, ensure_ascii=False, indent=2)

    print(f"\n=> Total : {len(unique)} événements écrits dans {out_path}")


if __name__ == "__main__":
    main()
