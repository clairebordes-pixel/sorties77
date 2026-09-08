#!/usr/bin/env python3
"""
scrape_moustier_thorigny.py — Sorties 77 data source

Scrapes the season programme of the Centre culturel Le Moustier
(Thorigny-sur-Marne), published by the venue as a Calaméo flipbook:

    https://www.calameo.com/read/00163340505ae83966d37

WHY THIS EXISTS
---------------
Calaméo disables the "Download" button for this document (the publisher
didn't enable it), so there's no PDF to grab. But the reader doesn't render
pages as flat images: each page is fetched by the browser as an individual
SVG file (".svgz", despite the name it is served as plain SVG, not gzip —
`Content-Encoding` handles the compression) from a signed CDN URL, and that
SVG contains real <text> elements, not vector-outlined glyphs. So instead of
scraping the interactive viewer (which would need a full browser and page
flipping), this script:

  1. Loads the Calaméo reader once with Playwright, just to read the
     document's internal metadata (`getCalameoBook()`, exposed on
     `window` by Calaméo's own JS) and to capture one signed asset URL
     that the viewer requests while rendering the first page(s).
  2. Reuses that signed URL's query-string token to fetch every page's
     raw SVG directly over HTTP (fast — no further browser rendering).
  3. Parses the <text> elements out of each page's SVG and applies
     best-effort heuristics to group them into a show record (title,
     category, date, time, public, description, press quote, credits).

IMPORTANT LIMITATION — READ BEFORE TRUSTING THE OUTPUT
--------------------------------------------------------
The document uses subsetted custom fonts (typical of a PDF→SVG export).
For fonts used in stylised text (the handwritten-style day/date line, some
subtitles), the embedded font's glyph→character map doesn't line up with
real Unicode, so the extracted string is visibly garbled, e.g.:

    "Mercredi 5 novembre"  ->  "ecedi 5 novee"
    "THÉÂTRE"                (unaffected — different font on that page)

This is NOT limited to one "known-bad" font class either: on some pages
even the title font drops a character silently, with no visual sign in the
extracted string that anything is wrong:

    "GRETEL ET HANSEL"  ->  " GRETEL ET ANSEL"   (dropped the H)
    "VERNON SUBUTEX"    ->  "VERNON SUBUTE"       (dropped the X)

So: raw_text_runs (the ordered list of text strings per page) is a faithful
*record of what the SVG contained*, but it is not guaranteed to be a 100%
accurate transcription of the original document. Treat every field in
`parsed` as a first draft. Before publishing an event to Sorties 77:
  - cross-check the title/date against the rendered page (the `page_url`
    field links straight to that page in the Calaméo viewer), or
  - run it through OCR as a cross-check (Calaméo also serves a rendered
    JPEG per page under a similar signed-URL scheme — see
    `book['domains']['image']` / `book['domains']['thumbnail']` printed by
    this script with --dump-book; the exact per-page filename pattern
    wasn't captured here and would need a quick network-tab check, same
    way the .svgz pattern was found).

The category/date/time/credits split in `parsed` is heuristic (position +
regex on the raw text runs), not from any structured field Calaméo
exposes — different show types (concert vs. théâtre vs. atelier) may not
all fit the same template. `raw_text_runs` is always kept in the output
so nothing is lost if a heuristic misfires.

USAGE
-----
    pip install playwright requests
    playwright install chromium   # not needed if already provisioned

    python scrape_moustier_thorigny.py -o moustier_thorigny.json
    python scrape_moustier_thorigny.py --dump-book   # inspect raw metadata

Designed to run standalone or from a GitHub Actions step, in the same
spirit as the rest of the Sorties 77 scraper pipeline (Python script,
JSON output, no manual steps).
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from playwright.sync_api import sync_playwright

CALAMEO_URL = "https://www.calameo.com/read/00163340505ae83966d37"
SOURCE_NAME = "Centre culturel Le Moustier — Thorigny-sur-Marne"

# Category vocabulary we know appears in this programme; used only to help
# the heuristic pick out the category line with more confidence. Not
# exhaustive — anything else falls back to "first all-caps short line".
KNOWN_CATEGORIES = [
    "THÉÂTRE JEUNE PUBLIC", "THÉÂTRE", "CONCERT", "DANSE", "CIRQUE",
    "HUMOUR", "MUSIQUE", "CINÉMA", "EXPOSITION", "CONFÉRENCE", "ATELIER",
    "SPECTACLE", "JEUNE PUBLIC",
]

CREDIT_LABELS = [
    "Un spectacle d’", "Un spectacle de", "Texte de", "Texte et mise en scène",
    "Mise en scène", "Chorégraphie", "Avec", "Compagnie", "D’après",
    "Une création", "Conception",
]

TIME_RE = re.compile(r"\b\d{1,2}h\d{0,2}\b")
# \b before "ans" matters: without it this also matches inside "dans",
# "sans", etc.
PUBLIC_RE = re.compile(r"(\bans\b|\bpublic\b|à partir de)", re.IGNORECASE)


@dataclass
class TextRun:
    cls: str
    text: str


@dataclass
class PageRecord:
    page_number: int
    page_url: str
    raw_text_runs: list = field(default_factory=list)
    parsed: dict = field(default_factory=dict)
    needs_manual_review: bool = True


def get_book_metadata_and_token(calameo_url: str, headless: bool = True):
    """Load the Calaméo reader with Playwright and extract:
    - the `getCalameoBook()` JS object (document id/key/page count/etc.)
    - a signed asset query string (the `?_token_=...` suffix) captured from
      any page image the viewer requests while rendering.

    The token is a wildcard-ACL signed URL good for every page in this
    document (not just the one it was issued for) until it expires
    (observed expiry: a few hours after the page load that issued it), so
    fetch it fresh every run rather than hardcoding one.
    """
    captured_token = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        def on_request(req):
            if "_token_" in req.url and ".svgz" in req.url and "token" not in captured_token:
                # Split off everything from the query string onward.
                base, _, query = req.url.partition("?")
                captured_token["query"] = query
                captured_token["base_dir"] = base.rsplit("/", 1)[0] + "/"

        page.on("request", on_request)
        page.goto(calameo_url, wait_until="networkidle", timeout=60_000)

        # Give the viewer a moment to issue its first page image requests
        # if networkidle fired before any were made.
        page.wait_for_timeout(2000)

        book = page.evaluate("() => window.getCalameoBook ? window.getCalameoBook() : null")

        # Fallback: if no request was captured yet (e.g. lazy rendering),
        # scan the DOM directly for an element whose src/href carries the
        # token, same trick used to discover this mechanism manually.
        if "query" not in captured_token:
            found = page.evaluate(
                """() => {
                    const els = document.querySelectorAll('img, image');
                    for (const el of els) {
                        const src = el.src || el.getAttribute('href') || el.getAttribute('xlink:href') || '';
                        if (src.includes('_token_')) return src;
                    }
                    return null;
                }"""
            )
            if found:
                base, _, query = found.partition("?")
                captured_token["query"] = query
                captured_token["base_dir"] = base.rsplit("/", 1)[0] + "/"

        browser.close()

    if "query" not in captured_token:
        raise RuntimeError(
            "Could not capture a signed asset token from the Calaméo viewer. "
            "The page structure may have changed — re-check with --dump-book "
            "and a browser network inspector."
        )
    if not book:
        raise RuntimeError("window.getCalameoBook() was not available on the page.")

    return book, captured_token["base_dir"], captured_token["query"]


def fetch_page_svg_text(base_dir: str, query: str, page_number: int, session: requests.Session) -> str:
    url = f"{base_dir}p{page_number}.svgz?{query}"
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def extract_text_runs(svg_text: str) -> list[TextRun]:
    """Pull <text> elements out of the page SVG, in document order.

    Uses a regex rather than a full XML parser to sidestep namespace
    fiddling and because the SVG is well-formed enough (Calaméo-generated)
    for this to be reliable; swap in xml.etree if you'd rather be strict.
    """
    runs = []
    for m in re.finditer(
        r'<text\b[^>]*\bclass="([^"]*)"[^>]*>(.*?)</text>', svg_text, re.DOTALL
    ):
        cls, inner = m.group(1), m.group(2)
        # Strip any nested tags (e.g. <tspan>) and unescape basic entities.
        inner_text = re.sub(r"<[^>]+>", "", inner)
        inner_text = html.unescape(inner_text)
        if inner_text.strip():
            runs.append(TextRun(cls=cls, text=inner_text))
    return runs


def looks_like_category(text: str) -> bool:
    stripped = text.strip()
    if any(stripped.upper() == c or stripped.upper() in c for c in KNOWN_CATEGORIES):
        return True
    # Fallback: short, mostly-uppercase line with no digits.
    letters = [c for c in stripped if c.isalpha()]
    if not letters:
        return False
    upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    return upper_ratio > 0.9 and len(stripped) < 40 and not any(ch.isdigit() for ch in stripped)


def parse_page(page_number: int, runs: list[TextRun]) -> dict:
    """Best-effort structuring. See module docstring for the accuracy
    caveats — this is a starting point for manual review, not a
    guaranteed-correct transcription."""
    texts = [r.text.strip() for r in runs if r.text.strip()]
    parsed: dict = {
        "title": None,
        "category": None,
        "date_raw": None,
        "time": None,
        "public": None,
        "description": None,
        "point_presse_quote": None,
        "point_presse_source": None,
        "credits": {},
    }
    if not texts:
        return parsed

    idx = 0
    # texts[0] is usually the printed page number ("11") — skip it if so.
    if texts[0].strip().isdigit():
        idx = 1

    if idx < len(texts):
        parsed["title"] = texts[idx]
        idx += 1

    # Scan forward a few lines for category / date / time / public before
    # falling into the description block.
    lookahead_end = min(idx + 6, len(texts))
    category_i = date_i = time_i = public_i = None
    for i in range(idx, lookahead_end):
        t = texts[i]
        if category_i is None and looks_like_category(t):
            category_i = i
        elif TIME_RE.search(t) and time_i is None:
            time_i = i
        elif PUBLIC_RE.search(t) and public_i is None:
            public_i = i

    if category_i is not None:
        parsed["category"] = texts[category_i]
        # The line right after category is very often the date (garbled or
        # not) unless it's actually the time/public line.
        nxt = category_i + 1
        if nxt < len(texts) and nxt not in (time_i, public_i):
            parsed["date_raw"] = texts[nxt]
    if time_i is not None:
        # Keep the full line ("10h et 15h" may have two showtimes) rather
        # than just the first regex match.
        parsed["time"] = texts[time_i]
    if public_i is not None:
        parsed["public"] = texts[public_i]

    # Description: everything after the last of (category/date/time/public)
    # up to "Point presse".
    body_start = max([i for i in (category_i, time_i, public_i) if i is not None], default=idx) + 1
    if parsed["date_raw"] and (category_i is not None) and body_start <= category_i + 1:
        body_start = category_i + 2

    pp_i = next((i for i in range(body_start, len(texts)) if "point presse" in texts[i].lower()), None)
    desc_end = pp_i if pp_i is not None else len(texts)
    description_lines = texts[body_start:desc_end]
    # Drop credit lines that may be interleaved/after the description.
    parsed["description"] = " ".join(description_lines).strip() or None

    if pp_i is not None:
        remaining = texts[pp_i + 1:]
        if remaining:
            # Quote is typically the next 1-2 lines (often wrapped in « »),
            # source is a short trailing line, often prefixed with "-".
            # Keep appending to the quote until we hit a line that looks
            # like the attribution ("- Le Parisien", " - Télérama T T T ").
            quote_lines = []
            j = 0
            while j < len(remaining) and not remaining[j].strip().startswith("-"):
                quote_lines.append(remaining[j])
                j += 1
            parsed["point_presse_quote"] = " ".join(quote_lines).strip() or None
            if j < len(remaining):
                parsed["point_presse_source"] = remaining[j].lstrip("- ").strip()

    # Credits: look for known label prefixes anywhere in the text runs and
    # pair each with the following line(s) until the next label.
    label_positions = []
    for i, t in enumerate(texts):
        for label in CREDIT_LABELS:
            if t.strip().startswith(label):
                label_positions.append((i, label, t.strip()[len(label):].strip()))
                break
    for k, (i, label, same_line_value) in enumerate(label_positions):
        end = label_positions[k + 1][0] if k + 1 < len(label_positions) else min(i + 3, len(texts))
        value_parts = [same_line_value] if same_line_value else []
        value_parts += texts[i + 1:end]
        value = " ".join(v for v in value_parts if v).strip()
        if value:
            parsed["credits"][label.rstrip("’ ")] = value

    return parsed


def scrape(output_path: str | None, headless: bool = True, dump_book: bool = False):
    book, base_dir, query = get_book_metadata_and_token(CALAMEO_URL, headless=headless)

    if dump_book:
        print(json.dumps(book, indent=2, ensure_ascii=False)[:4000])

    page_count = book["document"]["pages"]
    print(f"Document: {book['name']!r} — {page_count} pages", file=sys.stderr)

    session = requests.Session()
    pages_out = []
    for n in range(1, page_count + 1):
        try:
            svg_text = fetch_page_svg_text(base_dir, query, n, session)
        except requests.RequestException as e:
            print(f"  page {n}: fetch failed ({e}), skipping", file=sys.stderr)
            continue
        runs = extract_text_runs(svg_text)
        parsed = parse_page(n, runs)
        pages_out.append(
            {
                "page_number": n,
                "page_url": f"{CALAMEO_URL}?page={n}",
                "raw_text_runs": [{"class": r.cls, "text": r.text} for r in runs],
                "parsed": parsed,
                "needs_manual_review": True,
            }
        )
        print(f"  page {n}/{page_count}: {len(runs)} text runs, title={parsed['title']!r}", file=sys.stderr)

    result = {
        "source": SOURCE_NAME,
        "source_url": CALAMEO_URL,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "document_title": book["name"],
        "page_count": page_count,
        "pages": pages_out,
        "caveat": (
            "Text extracted from Calaméo's per-page SVG. Some fonts used in "
            "this document are subsetted and drop/garble characters on "
            "extraction (seen in both stylised text and, occasionally, "
            "titles) — verify against the source page before publishing. "
            "See this script's module docstring for examples."
        ),
    }

    output = json.dumps(result, indent=2, ensure_ascii=False)
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Wrote {output_path}", file=sys.stderr)
    else:
        print(output)

    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--output", help="Path to write JSON output (default: stdout)")
    parser.add_argument("--no-headless", action="store_true", help="Run the browser with a visible window (debugging)")
    parser.add_argument("--dump-book", action="store_true", help="Print the raw getCalameoBook() metadata and exit info to stderr")
    args = parser.parse_args()

    scrape(args.output, headless=not args.no_headless, dump_book=args.dump_book)


if __name__ == "__main__":
    main()
