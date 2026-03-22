"""Scraper per l'ICCUB (Institut de Ciències del Cosmos, Universitat de Barcelona).

Fa dues passades:
1. Llistat d'events (/events) → títol, data, tipus, URL
2. Cada pàgina individual → ponent, hora, lloc, abstract
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from http_client import fetch_text
from models import EventItem, classify_event_kind

logger = logging.getLogger(__name__)

_BASE = "https://icc.ub.edu"
_EVENTS_URL = f"{_BASE}/events"

_KIND_MAP = {
    "seminar": "seminari",
    "conference": "conferencia",
    "course": "taller",
    "iccub colloquium": "debat",
    "colloquium": "debat",
    "thesis defence": "sessio",
    "workshop": "taller",
    "winter meeting": "conferencia",
}


def _enrich_single(e: EventItem) -> EventItem:
    """Obre la pàgina individual i extreu speaker, hora, lloc, abstract."""
    try:
        html = fetch_text(e.url, timeout=(10.0, 15.0), max_attempts=2)
    except Exception as exc:
        logger.debug("ICCUB enrich: no s'ha pogut obrir %s: %s", e.url[:60], exc)
        e.detail_fetched = True
        return e

    soup = BeautifulSoup(html, "lxml")
    for row in soup.select(".field--label-inline, .field"):
        label_el = row.select_one(".field__label")
        value_el = row.select_one(".field__item, .field__items")
        if not label_el or not value_el:
            continue
        label = label_el.get_text(strip=True).lower()
        value = value_el.get_text(strip=True)
        if "by" == label.strip().rstrip(":") and not e.speakers:
            e.speakers = value[:200]
        elif "date" in label and not e.starts_at_time:
            import re
            m = re.search(r"(\d{1,2}):(\d{2})", value)
            if m:
                e.starts_at_time = f"{int(m.group(1)):02d}:{m.group(2)}"
        elif ("place" in label or "room" in label) and not e.venue:
            e.venue = value[:100]

    body = soup.select_one(".field--name-body")
    if body and not e.detail_text:
        t = body.get_text(" ", strip=True)
        if t.lower().startswith("abstract:"):
            t = t[9:].strip()
        if len(t) > 30:
            e.detail_text = t[:1500]

    e.detail_fetched = True
    return e


def _parse_iccub_listing(html: str) -> list[EventItem]:
    soup = BeautifulSoup(html, "lxml")
    events: list[EventItem] = []
    seen_urls: set[str] = set()

    for card in soup.select(".node--type-event.card"):
        time_el = card.select_one("time.datetime[datetime]")
        if not time_el:
            continue
        dt_str = time_el.get("datetime", "")
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            event_date = dt.date()
        except (ValueError, TypeError):
            continue

        if event_date < date.today():
            continue

        title_group = card.select_one(".field-group-title")
        if not title_group:
            continue

        spans = title_group.select("span")
        event_type = spans[0].get_text(strip=True) if spans else ""

        link_el = title_group.select_one("a.stretched-link[href]")
        if not link_el:
            continue
        title = link_el.get_text(strip=True)
        href = urljoin(_BASE, link_el.get("href", ""))

        if not title or href in seen_urls:
            continue
        seen_urls.add(href)

        kind = _KIND_MAP.get(event_type.lower(), classify_event_kind(title))

        events.append(
            EventItem(
                institution="ICCUB (UB)",
                title=title,
                url=href,
                starts_at=event_date.isoformat(),
                label=event_type,
                raw_date=event_date.strftime("%d/%m/%Y"),
                tier="nerd",
                area="Ciència i cosmos",
                summary=f"{event_type}: {title}" if event_type else title,
                source="iccub",
                event_kind=kind,
                confidence="high",
                source_quality="premium",
            )
        )

    return events


def fetch_iccub_events(url: str = _EVENTS_URL) -> list[EventItem]:
    logger.info("ICCUB: baixant %s", url)
    html = fetch_text(url)
    evs = _parse_iccub_listing(html)
    logger.info("ICCUB: %s esdeveniments futurs, enriquint...", len(evs))

    if evs:
        workers = min(4, len(evs))
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(_enrich_single, e): e for e in evs}
            for fut in as_completed(futs):
                try:
                    fut.result()
                except Exception:
                    pass
        enriched = sum(1 for e in evs if e.detail_text)
        logger.info("ICCUB: %s/%s enriquits amb abstract", enriched, len(evs))

    return evs
