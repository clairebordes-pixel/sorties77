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
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
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

# Repère "18 sept.26" / "18 septembre 2026" / "18 sept 2026" dans un texte
DATE_RE = re.compile(
    r"(\d{1,2})\s*(janv\.?|f[ée]vr?\.?|mars|avr\.?|mai|juin|juil\.?|ao[uû]t|"
    r"sept\.?|oct\.?|nov\.?|d[ée]c\.?)\.?\s*'?(\d{2,4})",
    re.IGNORECASE,
)
TIME_RE = re.compile(r"(\d{1,2})[h:](\d{2})?")


@dataclass
class Event:
    date: str          # YYYY-MM-DD
    time: str          # "20h30" ou ""
    title: str
    type: str          # concert | cirque | saison | autre
    venue: str
    city: str
    source_url: str = ""


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


def fetch(url: str, timeout=15) -> str:
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.apparent_encoding
    return r.text


def write_events(events, out_path: str):
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump([asdict(e) for e in events], f, ensure_ascii=False, indent=2)
    print(f"-> {len(events)} événements écrits dans {out_path}")
