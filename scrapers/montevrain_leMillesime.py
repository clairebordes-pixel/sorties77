"""
Scraper pour Le Millésime — Montévrain.
Page cible : https://www.montevrain.fr/millesime/

Structure réelle observée (site refait, inspecté le 02/09/2026) :

  <div style="align-self:flex-start" class="col-xs-12 col-lg-4">
    <div class="rte rte-preserve-wrap">
      <figure class="ce-gallery">
        <a href="https://www.montevrain.fr/app/uploads/2026/06/Smile.png" class="fancybox">
          <picture><img data-src="....-819x1024.png" ...></picture>
        </a>
      </figure>
    </div>
    <div class="rte">
      <p style="text-align:center"><strong>Vendredi 18 sept.26 | 20h30</strong></p>
    </div>
    <div class="link-wordpress"><a class="btn is-wordpress" href="https://www.billetweb.fr/millesime-smile">Billetterie</a></div>
  </div>

Chaque encart événement est un seul bloc contenant l'image, la date/heure
et le lien de billetterie. Le titre n'est pas affiché en texte : on le
reconstruit à partir du nom de fichier de l'affiche (ex. "Smile.png" ->
"Smile"), car c'est plus fiable que le texte alt générique
("Agrandir l'image, fenêtre modale").
"""
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common import Event, fetch, parse_date_fr, parse_time_fr, write_events

URL = "https://www.montevrain.fr/millesime/"


def _title_from_image_url(href: str) -> str:
    stem = Path(href.split("?")[0]).stem
    stem = re.sub(r"[-_]+", " ", stem).strip()
    return stem.title() if stem else "Spectacle"


def scrape():
    from bs4 import BeautifulSoup

    html = fetch(URL)
    print(f"[diagnostic] taille de la page reçue : {len(html)} caractères")
    soup = BeautifulSoup(html, "html.parser")

    events = []
    # Chaque encart est un conteneur avec une image (figure > a.fancybox)
    # ET un paragraphe en gras contenant une date -> on filtre sur cette
    # double condition pour ne garder que les vrais encarts spectacle.
    candidates = soup.select("div.col-lg-4, div[class*='col-lg-4']")
    seen = set()
    for block in candidates:
        strong = block.find("strong")
        link_img = block.select_one("a.fancybox[href]")
        if not strong or not link_img:
            continue

        date_time_text = strong.get_text(" ", strip=True)
        date = parse_date_fr(date_time_text)
        if not date:
            continue
        time = parse_time_fr(date_time_text)

        image_url = link_img["href"]
        title = _title_from_image_url(image_url)

        key = (date, title)
        if key in seen:
            continue
        seen.add(key)

        billet_link = block.select_one(".link-wordpress a[href]")
        source_url = billet_link["href"] if billet_link else URL

        events.append(
            Event(
                date=date,
                time=time,
                title=title,
                type="spectacle",
                venue="Le Millésime",
                city="Montévrain",
                source_url=source_url,
                image_url=image_url,
            )
        )
    return events


if __name__ == "__main__":
    write_events(scrape(), "output/millesime.json")
