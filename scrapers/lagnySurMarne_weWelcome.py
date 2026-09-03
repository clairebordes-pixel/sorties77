"""
Scraper pour We Welcome — Lagny-sur-Marne.
Page cible : https://we-welcome.fr/programmation/

Structure réelle observée (inspectée le 31/08/2026) :

  <div class="month-title"><h2>Septembre</h2></div>
  <div class="wewelcome-event-item default">
    <a href="https://we-welcome.fr/reservation/leffet-papillon-taha-mansour-mentaliste/">
      <div class="item-thumbnail" style="background-image: url(https://we-welcome.fr/wp-content/uploads/.../affiche.png);"></div>
      <div class="item-content">
        <div class="item-day">11</div>
        <div class="item-day-month">
          <div class="day">vendredi</div>
          <div class="month">septembre</div>
        </div>
        <div class="item-hours"><span>21:00</span></div>
      </div>
    </a>
  </div>

Il n'y a pas de titre affiché dans la carte elle-même : on le reconstruit
à partir du slug de l'URL de réservation. Certains jours ont deux horaires
(deux <span> dans .item-hours) -> un événement par horaire.

L'année n'est jamais indiquée : on part de l'année en cours à la date
d'exécution du script, et on l'incrémente si un mois "recule" d'une
section à la suivante (ex: Décembre -> Janvier).
"""
import re
import sys
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common import Event, fetch, write_events

URL = "https://we-welcome.fr/programmation/"

MOIS = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "août": 8, "aout": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
}

BG_IMAGE_RE = re.compile(r"url\((.*?)\)")

ATELIER_HINTS = ("atelier", "stage", "cours")
CONCERT_HINTS = ("concert",)


def _title_from_slug(href: str) -> str:
    slug = href.rstrip("/").split("/")[-1]
    slug = re.sub(r"-\d+$", "", slug)  # enlève un suffixe numérique de doublon WP
    slug = re.sub(r"[-_]+", " ", slug).strip()
    return slug.title() if slug else "Événement"


def _guess_type(title: str) -> str:
    t = title.lower()
    if any(h in t for h in ATELIER_HINTS):
        return "atelier"
    if any(h in t for h in CONCERT_HINTS):
        return "concert"
    return "spectacle"


def scrape():
    from bs4 import BeautifulSoup

    html = fetch(URL)
    print(f"[diagnostic] taille de la page reçue : {len(html)} caractères")
    soup = BeautifulSoup(html, "html.parser")

    events = []
    current_year = date.today().year
    prev_month_num = None

    for node in soup.select(".month-title, .wewelcome-event-item"):
        if "month-title" in node.get("class", []):
            h2 = node.find("h2")
            if not h2:
                continue
            month_name = h2.get_text(strip=True).lower()
            month_num = MOIS.get(month_name)
            if not month_num:
                continue
            if prev_month_num is not None and month_num < prev_month_num:
                current_year += 1
            prev_month_num = month_num
            continue

        if prev_month_num is None:
            continue  # pas encore de mois connu, on ignore par sécurité

        link = node.find("a")
        if not link:
            continue
        href = link.get("href", URL)
        title = _title_from_slug(href)

        day_tag = node.select_one(".item-day")
        if not day_tag:
            continue
        day = day_tag.get_text(strip=True)

        thumb = node.select_one(".item-thumbnail")
        image_url = ""
        if thumb and thumb.get("style"):
            m = BG_IMAGE_RE.search(thumb["style"])
            if m:
                image_url = m.group(1).strip("'\"")

        hour_spans = node.select(".item-hours span")
        times = [s.get_text(strip=True) for s in hour_spans] or [""]

        for time_str in times:
            time = time_str.replace(":", "h") if time_str else ""
            events.append(
                Event(
                    date=f"{current_year:04d}-{prev_month_num:02d}-{int(day):02d}",
                    time=time,
                    title=title,
                    type=_guess_type(title),
                    venue="We Welcome",
                    city="Lagny-sur-Marne",
                    source_url=href,
                    image_url=image_url,
                )
            )

    print(f"[diagnostic] nombre d'événements trouvés : {len(events)}")
    return events


if __name__ == "__main__":
    write_events(scrape(), "output/we_welcome.json")
