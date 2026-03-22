"""Scraper per l'ICFO (Institut de Ciències Fotòniques).

Parseja la pàgina /icfo-events/ que té les dades d'hora, lloc i speaker
directament al llistat, i obre les pàgines individuals per l'abstract.
"""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from http_client import fetch_text
from models import EventItem, classify_event_kind

logger = logging.getLogger(__name__)

_BASE = "https://www.icfo.eu"
_EVENTS_URL = f"{_BASE}/icfo-events/"

_MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

_RE_DATE = re.compile(
    r"(?P<month>January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+(?P<day>\d{1,2}),?\s+(?P<year>\d{4})",
    re.IGNORECASE,
)
_RE_HOUR = re.compile(r"From\s+(\d{1,2}):(\d{2})h", re.IGNORECASE)
_RE_PLACE = re.compile(r"Place:\s*(.+?)(?:\.\s|$)", re.IGNORECASE)

_KIND_MAP = {
    "seminars": "seminari",
    "colloquium": "debat",
    "events & conferences": "conferencia",
    "schools": "taller",
    "outreach": "xerrada",
    "skills training": "taller",
}


def _parse_event_date(text: str) -> date | None:
    m = _RE_DATE.search(text)
    if not m:
        return None
    try:
        return date(
            int(m.group("year")),
            _MONTH_MAP[m.group("month").lower()],
            int(m.group("day")),
        )
    except (ValueError, KeyError):
        return None


def _enrich_icfo(e: EventItem) -> EventItem:
    try:
        html = fetch_text(e.url, timeout=(10.0, 15.0), max_attempts=2)
    except Exception:
        e.detail_fetched = True
        return e
    soup = BeautifulSoup(html, "lxml")
    body = soup.select_one("article, .post-content, .entry-content, main")
    if body and not e.detail_text:
        text = body.get_text(" ", strip=True)
        if len(text) > 50:
            e.detail_text = text[:1500]
    e.detail_fetched = True
    return e


def fetch_icfo_events(url: str = _EVENTS_URL) -> list[EventItem]:
    logger.info("ICFO: baixant %s", url)
    try:
        html = fetch_text(url)
    except Exception as exc:
        logger.warning("ICFO: no s'ha pogut baixar: %s", exc)
        return []

    soup = BeautifulSoup(html, "lxml")
    events: list[EventItem] = []
    seen: set[str] = set()
    today = date.today()

    for wrapper in soup.select(".event-wrapper"):
        text = wrapper.get_text(" ", strip=True)
        link_el = wrapper.select_one("a[href]")
        if not link_el:
            continue
        href = link_el.get("href", "")
        if href.startswith("javascript"):
            continue
        url_full = urljoin(_BASE, href)
        if url_full in seen:
            continue
        seen.add(url_full)

        event_date = _parse_event_date(text)
        if not event_date or event_date < today:
            continue

        # Type: comes before the date
        type_text = ""
        for container in wrapper.parents:
            cls = " ".join(container.get("class", []))
            if "events-container" in cls:
                first_child = container.find(string=True, recursive=False)
                if first_child:
                    type_text = first_child.strip()
                break

        # Title: text after the date, before "Hour:"
        title_match = re.search(
            r"\d{4}\s+(.+?)(?:\s+Hour:|\s+All day|\s+Place:)",
            text,
        )
        title = title_match.group(1).strip() if title_match else text[:100]

        hour = ""
        m_hour = _RE_HOUR.search(text)
        if m_hour:
            hour = f"{int(m_hour.group(1)):02d}:{m_hour.group(2)}"

        place = ""
        m_place = _RE_PLACE.search(text)
        if m_place:
            place = m_place.group(1).strip()

        speaker = ""
        for pattern in (r"(?:SEMINAR|Seminar|COLLOQUIUM)(?:\s*[:|])\s*(.+?)(?:\s+Hour|\s+All day|$)",):
            sm = re.search(pattern, text)
            if sm:
                speaker = sm.group(1).strip()
                break
        if not speaker and "by " in text:
            sm = re.search(r"by\s+(.+?)(?:\s+\d{1,2}\s+\w+\s+at|\s*$)", text)
            if sm:
                speaker = sm.group(1).strip()

        kind_key = type_text.lower().strip()
        kind = _KIND_MAP.get(kind_key, classify_event_kind(title))

        events.append(
            EventItem(
                institution="ICFO",
                title=title,
                url=url_full,
                starts_at=event_date.isoformat(),
                label=type_text or "Seminar",
                raw_date=event_date.strftime("%d/%m/%Y"),
                tier="nerd",
                area="Ciència i cosmos",
                summary=f"{type_text}: {title}" if type_text else title,
                source="icfo",
                event_kind=kind,
                confidence="high",
                source_quality="premium",
                starts_at_time=hour,
                venue=place,
                speakers=speaker,
            )
        )

    if not events:
        logger.info("ICFO: 0 events (probablement bot-lockout JS challenge; requereix Playwright)")
        return events

    logger.info("ICFO: %s esdeveniments futurs, enriquint...", len(events))

    if events:
        workers = min(4, len(events))
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(_enrich_icfo, e): e for e in events}
            for fut in as_completed(futs):
                try:
                    fut.result()
                except Exception:
                    pass
        enriched = sum(1 for e in events if e.detail_text)
        logger.info("ICFO: %s/%s enriquits amb abstract", enriched, len(events))

    return events
