"""Scraper per l'ICE-CSIC (Institut de Ciències de l'Espai).

Parseja /news/scientific-events — les dades de data, hora i ponent
estan directament al llistat (no hi ha pàgines individuals útils,
els links són YouTube streams).
"""

from __future__ import annotations

import logging
import re
from datetime import date

from bs4 import BeautifulSoup

from http_client import fetch_text
from models import EventItem

logger = logging.getLogger(__name__)

_URL = "https://www.ice.csic.es/news/scientific-events"

_MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

_RE_ENTRY = re.compile(
    r"(?P<tag>#\w+|Colloquium|Thesis Defence)?\s*(?:by\s+)?(?P<speaker>.+?)\s+"
    r"(?P<day>\d{1,2})\s+(?P<month>January|February|March|April|May|June|"
    r"July|August|September|October|November|December)\s+at\s+"
    r"(?P<hour>\d{1,2}):(?P<min>\d{2})",
    re.IGNORECASE,
)


def fetch_ice_csic_events(url: str = _URL) -> list[EventItem]:
    logger.info("ICE-CSIC: baixant %s", url)
    try:
        html = fetch_text(url)
    except Exception as exc:
        logger.warning("ICE-CSIC: no s'ha pogut baixar: %s", exc)
        return []

    soup = BeautifulSoup(html, "lxml")
    events: list[EventItem] = []
    today = date.today()
    year = today.year
    seen: set[str] = set()

    for item in soup.select(".el-item"):
        text = item.get_text(" ", strip=True)
        m = _RE_ENTRY.search(text)
        if not m:
            continue

        tag = (m.group("tag") or "").strip()
        speaker = m.group("speaker").strip()
        day = int(m.group("day"))
        month_name = m.group("month")
        hour = int(m.group("hour"))
        minute = int(m.group("min"))

        month = _MONTH_MAP.get(month_name.lower())
        if not month:
            continue

        try:
            event_date = date(year, month, day)
        except ValueError:
            continue

        if event_date < today:
            continue

        # Title: combine tag + speaker for a meaningful title
        if tag.startswith("#"):
            kind_label = tag.replace("#", "").replace("Seminar", "").strip()
            title = f"{tag} by {speaker}"
            kind = "seminari"
        elif "colloquium" in tag.lower():
            title = f"Colloquium: {speaker}"
            kind = "debat"
        elif "thesis" in tag.lower():
            title = f"Thesis Defence: {speaker}"
            kind = "sessio"
        else:
            title = speaker
            kind = "seminari"

        key = f"{event_date.isoformat()}|{speaker}"
        if key in seen:
            continue
        seen.add(key)

        time_str = f"{hour:02d}:{minute:02d}"

        link_el = item.select_one("a[href]")
        url_ev = link_el.get("href", "") if link_el else ""
        if not url_ev or url_ev.startswith("javascript"):
            url_ev = _URL

        events.append(
            EventItem(
                institution="ICE-CSIC",
                title=title,
                url=url_ev,
                starts_at=event_date.isoformat(),
                label=tag or "Seminar",
                raw_date=event_date.strftime("%d/%m/%Y"),
                tier="nerd",
                area="Ciència i cosmos",
                summary=title,
                source="ice_csic",
                event_kind=kind,
                confidence="high",
                source_quality="premium",
                starts_at_time=time_str,
                venue="ICE-CSIC, Campus UAB, Bellaterra",
                city="Bellaterra",
                speakers=speaker,
                detail_fetched=True,
            )
        )

    logger.info("ICE-CSIC: %s esdeveniments futurs", len(events))
    return events
