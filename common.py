"""
Utilitaires partagés par tous les scrapers du projet Sorties 77.
"""
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Referer": "https://www.google.com/",
}

MOIS = {
    "janv": "01", "janvier": "01",
    "fev": "02", "févr": "02", "fevrier": "02", "février": "02",
    "mars": "03",
    "avr": "04", "avril": "04",
    "mai": "05",
    "juin": "06",
    "juil": "07", "juillet": "07",
    "aout": "08", "août": "08",
    "sept": "09", "septembre": "09",
    "oct": "10", "octobre": "10",
    "nov": "11", "novembre": "11",
    "dec": "12", "déc": "12", "decembre": "12", "décembre": "12",
}

# Repère "18 sept.26" / "18 septembre 2026" / "18 sept 2026" dans un texte.
# Le mot du mois est capturé en entier (lettres + accents), qu'il soit
# abrégé ("sept") ou en toutes lettres ("septembre") — c'est ensuite
# parse_date_fr() qui le reconnaît via un préfixe.
DATE_RE = re.compile(
    r"(\d{1,2})\s+([A-Za-zéèêàâûîôç]+)\.?\s*'?(\d{2,4})",
    re.IGNORECASE,
)
TIME_RE = re.compile(r"(\d{1,2})[h:](\d{2})?")


@dataclass
class Event:
    date: str          # YYYY-MM-DD
    time: str          # "20h30" ou ""
    title: str
    type: str          # concert | cirque | saison | atelier | spectacle
    venue: str
    city: str
    source_url: str = ""   # lien vers la page de l'événement / billetterie
    image_url: str = ""    # image du spectacle, si disponible


def parse_date_fr(text: str, default_year: int = 2026):
    """Essaie d'extraire une date YYYY-MM-DD d'un fragment de texte français."""
    m = DATE_RE.search(text)
    if not m:
        return None
    day, mon_raw, year = m.groups()
    mon_key = mon_raw.lower().replace(".", "").rstrip("é")
    month = None
    for k, v in MOIS.items():
        if mon_raw.lower().replace(".", "").startswith(k[:4]):
            month = v
            break
    if not month:
        return None
    year = int(year)
    if year < 100:
        year += 2000
    return f"{year:04d}-{month}-{int(day):02d}"


def parse_time_fr(text: str):
    m = TIME_RE.search(text)
    if not m:
        return ""
    h, mn = m.groups()
    return f"{int(h)}h{mn or '00'}"


def fetch(url: str, timeout=15, retries=3) -> str:
    """
    Récupère une page, avec quelques nouvelles tentatives en cas de souci
    réseau transitoire (timeout, connexion refusée...) — fréquent sur les
    serveurs GitHub Actions, qui n'ont pas toujours une IP stable.
    Les erreurs HTTP "définitives" (404, 418 bloqué délibérément...) ne
    sont PAS retentées, ça ne servirait à rien.
    """
    import time

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            r.encoding = r.apparent_encoding
            return r.text
        except requests.exceptions.HTTPError as e:
            raise  # erreur HTTP explicite (418, 404...) : pas la peine de retenter
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < retries:
                wait = 5 * attempt
                print(f"[retry] tentative {attempt}/{retries} échouée ({e}), nouvel essai dans {wait}s")
                time.sleep(wait)
    raise last_error


def write_events(events, out_path: str):
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump([asdict(e) for e in events], f, ensure_ascii=False, indent=2)
    print(f"-> {len(events)} événements écrits dans {out_path}")
