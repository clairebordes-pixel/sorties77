"""
Scraper pour Les Cuizines — Chelles.
Page cible : https://www.lescuizines.fr/events/

Structure réelle observée (inspectée le 31/08/2026) :

  <div class="row">
    <div class="col-lg-3 col-md-3 col-xs-4 agenda-item">
      <div class="label-event">Scène ouverte</div>       <- catégorie
      <div class="image">
        <a href="https://www.lescuizines.fr/events/jam-britpop/">
          <img src="....jpg">
        </a>
      </div>
      <div class="agenda-groupe">...</div>                <- probablement le titre
      <div class="agenda-secondgroupe">...</div>          <- sous-titre / infos
      <div class="agenda-date-texte">Samedi 19 septembre 2026</div>
    </div>
    ...
  </div>

Le titre exact (agenda-groupe) reste à confirmer — en attendant, on utilise
le slug de l'URL de l'événement comme titre de secours si agenda-groupe est
vide.
"""
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common import Event, fetch, parse_date_fr, parse_time_fr, write_events

URL = "https://www.lescuizines.fr/events/"


def _title_from_slug(href: str) -> str:
    slug = href.rstrip("/").split("/")[-1]
    slug = re.sub(r"[-_]+", " ", slug).strip()
    return slug.title() if slug else "Événement"


def scrape():
    from bs4 import BeautifulSoup

    html = fetch(URL)
    print(f"[diagnostic] taille de la page reçue : {len(html)} caractères")
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select(".agenda-item")
    print(f"[diagnostic] nombre de .agenda-item trouvés : {len(items)}")
    events = []

    for item in items:
        date_tag = item.select_one(".agenda-date-texte")
        if not date_tag:
            continue
        date = parse_date_fr(date_tag.get_text(strip=True))
        if not date:
            continue
        time = parse_time_fr(item.get_text(" ", strip=True))

        category_tag = item.select_one(".label-event")
        category = category_tag.get_text(strip=True) if category_tag else ""

        # Titre : d'abord agenda-groupe, sinon le slug du lien
        title = ""
        groupe_tag = item.select_one(".agenda-groupe")
        if groupe_tag:
            title = groupe_tag.get_text(strip=True)
        link = item.select_one("a[href]")
        if not title and link:
            title = _title_from_slug(link["href"])
        if not title:
            title = category or "Événement"

        img_tag = item.select_one(".image img")
        image_url = img_tag.get("src", "") if img_tag else ""
        source_url = link["href"] if link else URL

        events.append(
            Event(
                date=date,
                time=time,
                title=title,
                type="concert",
                venue="Les Cuizines",
                city="Chelles",
                source_url=source_url,
                image_url=image_url,
            )
        )
    return events


if __name__ == "__main__":
    write_events(scrape(), "output/lescuizines.json")
