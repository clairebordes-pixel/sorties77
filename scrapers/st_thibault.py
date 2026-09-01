"""
Scraper pour Saint-Thibault-des-Vignes — saison culturelle.
Page cible : https://www.saintthibaultdesvignes.fr/culture/saison-culturelle-et-evenements/

Structure réelle observée (inspectée le 31/08/2026) :

  <article class="post ... type-dt_portfolio ...">
    <div class="post-thumbnail-wrap">
      <div class="post-thumbnail">
        <a href="https://www.saintthibaultdesvignes.fr/spectacles/spectacle-pablo-mira-2/">
          <img title="261107-PabloMira-Affiche-spectacle26-27" ...>
        </a>
      </div>
    </div>
    <div class="post-entry-content">
      <h3 class="entry-title">
        <a href="...">Spectacle – Pablo Mira</a>
      </h3>
      ...
    </div>
  </article>

Il n'y a PAS de champ de date fiable dans le DOM (le data-date de l'article
est la date de PUBLICATION de la page, pas celle du spectacle). La seule
date fiable est encodée dans le nom de fichier de l'affiche, au format
AAMMJJ (ex: "261107" = 7 novembre 2026) — présent pour les spectacles
programmés, absent pour les activités récurrentes (ateliers, forums...).
Ces dernières sont donc ignorées faute de date exploitable.
"""
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common import Event, fetch, write_events

URL = "https://www.saintthibaultdesvignes.fr/culture/saison-culturelle-et-evenements/"

# ex: "261107-PabloMira-Affiche-spectacle26-27" -> 2026-11-07
DATE_PREFIX_RE = re.compile(r"(\d{2})(\d{2})(\d{2})[-_]")


def _guess_type(title: str) -> str:
    t = title.lower()
    if "concert" in t:
        return "concert"
    if "théâtre" in t or "theatre" in t:
        return "spectacle"
    if "atelier" in t or "stage" in t or "forum" in t:
        return "atelier"
    return "spectacle"


def scrape():
    from bs4 import BeautifulSoup

    html = fetch(URL)
    print(f"[diagnostic] taille de la page reçue : {len(html)} caractères")
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.select("article[class*='dt_portfolio']")
    print(f"[diagnostic] nombre d'articles trouvés : {len(articles)}")

    events = []
    for article in articles:
        title_tag = article.select_one("h3.entry-title a, .entry-title a")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        href = title_tag.get("href", URL)

        img = article.select_one(".post-thumbnail img")
        date_source = ""
        if img:
            date_source = img.get("title") or img.get("alt") or img.get("src") or ""

        m = DATE_PREFIX_RE.search(date_source)
        if not m:
            # Pas de date exploitable (atelier récurrent, forum, etc.) -> on ignore
            continue
        yy, mm, dd = m.groups()
        date = f"20{yy}-{mm}-{dd}"

        image_url = img.get("src", "") if img else ""

        events.append(
            Event(
                date=date,
                time="",
                title=title,
                type=_guess_type(title),
                venue="Centre Culturel",
                city="Saint-Thibault-des-Vignes",
                source_url=href,
                image_url=image_url,
            )
        )
    return events


if __name__ == "__main__":
    write_events(scrape(), "output/st_thibault.json")
