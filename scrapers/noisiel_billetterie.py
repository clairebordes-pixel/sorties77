"""
Scraper pour la billetterie de la Saison Culturelle de Noisiel (Pôle culturel
Michel-Legrand).
Page cible : https://www.ville-noisiel.fr/loisirs/culture/saison-culturelle/acheter-une-place-de-spectacle/

Cette page est en HTML classique (pas de JS), mais je n'ai pas pu voir son
vrai code source (seulement une version texte/markdown). Le scraper
travaille donc sur le TEXTE APLATI de la page plutôt que sur des sélecteurs
CSS, pour rester robuste même si la structure HTML réelle diffère un peu
de ce qu'on imagine. Format observé dans le texte :

    "El Spectacolo ! (samedi 3 octobre à 20h) ... Pour réserver, cliquez ici"
    "Le jardin de Dahi (« Dimanche en famille », dimanche 11 octobre à 16h
     et 17h30) Séance de 16h : pour réserver, cliquez ici Séance de 17h30 :
     pour réserver, cliquez ici"

Chaque lien de réservation pointe vers my.weezevent.com/<slug> — on associe
chaque lien au titre et à l'heure qui le précèdent immédiatement dans le texte.

L'année n'est jamais indiquée dans le texte (juste "samedi 3 octobre") : on
se base sur le fait que la page couvre la saison 2026-2027 (septembre à
décembre -> 2026, janvier à juillet -> 2027). À METTRE À JOUR l'an prochain
si le site republie une page "saison 2027-2028" avec le même format.
"""
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common import Event, fetch, write_events

URL = "https://www.ville-noisiel.fr/loisirs/culture/saison-culturelle/acheter-une-place-de-spectacle/"
VENUE = "Pôle culturel Michel-Legrand"
CITY = "Noisiel"

# saison 2026-2027 : septembre->décembre = 2026, janvier->juillet = 2027
SEASON_YEAR_SEPT_DEC = 2026
SEASON_YEAR_JAN_JUL = 2027

MOIS = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "août": 8, "aout": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
}

# "samedi 3 octobre à 20h" / "dimanche 11 octobre à 16h et 17h30"
DATE_RE = re.compile(
    r"(\d{1,2})\s+(janvier|f[ée]vrier|mars|avril|mai|juin|juillet|ao[uû]t|"
    r"septembre|octobre|novembre|d[ée]cembre)\s+à\s+"
    r"(\d{1,2})h(\d{0,2})(?:\s+et\s+(\d{1,2})h(\d{0,2}))?",
    re.IGNORECASE,
)

# titre en gras suivi d'une parenthèse contenant la date -> on capture tout
# le segment "Titre (....)" pour en extraire le titre propre ensuite.
ENTRY_RE = re.compile(r"([A-ZÀ-Ÿ0-9][^()]{2,80}?)\s*\(([^()]*?à[^()]*?)\)")

WEEZEVENT_LINK_RE = re.compile(r"(https?://my\.weezevent\.com/[a-z0-9\-]+)")


def _year_for_month(month_num: int) -> int:
    return SEASON_YEAR_SEPT_DEC if month_num >= 8 else SEASON_YEAR_JAN_JUL


def _clean_title(raw: str) -> str:
    title = raw.strip(" *–—-")
    title = re.sub(r"\s+", " ", title)
    return title


def scrape():
    from bs4 import BeautifulSoup

    html = fetch(URL)
    print(f"[diagnostic] taille de la page reçue : {len(html)} caractères")
    soup = BeautifulSoup(html, "html.parser")

    # on ne garde que la zone de contenu principale si on la trouve, sinon
    # toute la page (le menu/footer ne contiennent pas de lien weezevent
    # donc ça ne fausse pas le résultat)
    main = soup.find("main") or soup

    # on associe chaque lien weezevent à son <a> pour connaître l'ordre
    # d'apparition réel dans le DOM (plus fiable qu'un texte aplati global)
    links = main.find_all("a", href=re.compile(r"weezevent\.com"))
    print(f"[diagnostic] nombre de liens weezevent trouvés : {len(links)}")

    events = []
    for link in links:
        href = link.get("href", "")
        # on remonte au bloc parent (paragraphe/liste) qui contient tout le
        # texte de cette entrée (titre, date, "séance de XXh"...)
        block = link
        for _ in range(4):
            if block.parent is None:
                break
            block = block.parent
            text = block.get_text(" ", strip=True)
            if DATE_RE.search(text) and len(text) < 400:
                break

        text = block.get_text(" ", strip=True)

        m_entry = ENTRY_RE.search(text)
        title = _clean_title(m_entry.group(1)) if m_entry else "Spectacle"

        # heure spécifique à CE lien si "séance de XXh" est indiqué juste
        # avant lui dans le texte du lien lui-même ou son contexte proche
        link_context = link.get_text(" ", strip=True)
        seance_m = re.search(r"[Ss][ée]ance de (\d{1,2})h(\d{0,2})", text)

        date_m = DATE_RE.search(text)
        if not date_m:
            continue
        day, month_name, h1, m1, h2, m2 = date_m.groups()
        month_num = MOIS[month_name.lower()]
        year = _year_for_month(month_num)
        date_str = f"{year:04d}-{month_num:02d}-{int(day):02d}"

        # s'il y a deux horaires ET deux liens weezevent (deux séances),
        # on essaie de deviner laquelle correspond à ce lien via son index
        # dans la liste des liens de ce même bloc
        block_links = [a.get("href", "") for a in block.find_all("a", href=re.compile(r"weezevent\.com"))]
        if h2 and len(block_links) >= 2:
            idx = block_links.index(href) if href in block_links else 0
            time = f"{int(h1)}h{m1 or '00'}" if idx == 0 else f"{int(h2)}h{m2 or '00'}"
        else:
            time = f"{int(h1)}h{m1 or '00'}"

        events.append(
            Event(
                date=date_str,
                time=time,
                title=title,
                type="spectacle",
                venue=VENUE,
                city=CITY,
                source_url=href,
                image_url="",
            )
        )

    # dédoublonnage simple si jamais un même lien a été traité deux fois
    seen = set()
    unique = []
    for e in events:
        key = (e.date, e.time, e.source_url)
        if key in seen:
            continue
        seen.add(key)
        unique.append(e)

    print(f"[diagnostic] nombre d'événements extraits : {len(unique)}")
    return unique


if __name__ == "__main__":
    write_events(scrape(), "output/noisiel_billetterie.json")
