"""
Scraper pour File7 — Magny-le-Hongre.
Page cible : https://file7.com/fr/programme/programme.html

Structure réelle observée (inspectée le 31/08/2026) :

  <div class="zone_grille">
    <div class="bloc_show">
      <a href="https://www.file7.com/fr/programme/programme/19-09-2026-09h00-ecoute-de-prog-au-marche.html">
        <span class="show_image">...</span>
        <span class="infos">
          <span class="artistes">ÉCOUTE DE PROG' AU MARCHÉ !</span>
          <span class="date">Samedi 19 septembre</span>   <- pas d'année ici !
        </span>
      </a>
    </div>
    ...
  </div>

L'URL de chaque événement contient la date ET l'heure complètes
(jj-mm-aaaa-hhhmm), donc on s'appuie sur elle plutôt que sur le texte
".date" qui n'a pas l'année.
"""
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common import Event, fetch, write_events

URL = "https://file7.com/fr/programme/programme.html"

# ex: .../19-09-2026-09h00-ecoute-de-prog-au-marche.html
URL_DATE_RE = re.compile(r"/(\d{2})-(\d{2})-(\d{4})-(\d{1,2})h(\d{2})-")

# File7 est avant tout une salle de musiques actuelles : par défaut on
# classe en "concert", sauf mots-clés indiquant autre chose.
ATELIER_HINTS = ("atelier", "rencontre", "conférence", "masterclass")
SPECTACLE_HINTS = ("kidz", "just dance", "zélie", "scène ouverte")


def guess_type(title: str) -> str:
    t = title.lower()
    if any(h in t for h in ATELIER_HINTS):
        return "atelier"
    if any(h in t for h in SPECTACLE_HINTS):
        return "spectacle"
    return "concert"


def scrape():
    from bs4 import BeautifulSoup

    html = fetch(URL)
    print(f"[diagnostic] taille de la page reçue : {len(html)} caractères")
    soup = BeautifulSoup(html, "html.parser")
    blocs = soup.select(".bloc_show")
    print(f"[diagnostic] nombre de .bloc_show trouvés : {len(blocs)}")
    events = []

    for block in blocs:
        link = block.select_one("a[href]")
        if not link:
            continue
        href = link["href"]
        m = URL_DATE_RE.search(href)
        if not m:
            continue
        day, month, year, hour, minute = m.groups()
        date = f"{year}-{month}-{day}"
        time = f"{int(hour)}h{minute}"

        title_tag = block.select_one(".artistes")
        title = title_tag.get_text(strip=True) if title_tag else "Événement"
        title = title.title() if title.isupper() else title

        img_tag = block.select_one(".show_image img")
        image_url = img_tag.get("src", "") if img_tag else ""

        events.append(
            Event(
                date=date,
                time=time,
                title=title,
                type=guess_type(title),
                venue="File7",
                city="Magny-le-Hongre",
                source_url=href,
                image_url=image_url,
            )
        )
    return events


if __name__ == "__main__":
    write_events(scrape(), "output/file7.json")
