"""Scraper per l'ICCUB (Institut de Ciències del Cosmos, Universitat de Barcelona)."""

from __future__ import annotations

import logging
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


def _parse_iccub_events(html: str) -> list[EventItem]:
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
            )
        )

    return events


def fetch_iccub_events(url: str = _EVENTS_URL) -> list[EventItem]:
    logger.info("ICCUB: baixant %s", url)
    html = fetch_text(url)
    evs = _parse_iccub_events(html)
    logger.info("ICCUB: %s esdeveniments futurs", len(evs))
    return evs
