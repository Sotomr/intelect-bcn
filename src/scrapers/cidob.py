from __future__ import annotations

import logging
import re
from datetime import date
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from http_client import fetch_text
from models import EventItem

logger = logging.getLogger(__name__)


def _short_summary(title: str, max_len: int = 120) -> str:
    t = title.strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rsplit(" ", 1)[0] + "…"

_SP_MONTHS = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}


def _parse_cidob_date(text: str) -> date | None:
    t = re.sub(r"\s+", " ", text.strip())
    m = re.match(r"^(\d{1,2})\s+([A-Za-zÀ-ÿ]{3})\s+(\d{4})$", t)
    if not m:
        return None
    d, mon_s, y = int(m.group(1)), m.group(2).lower()[:3], int(m.group(3))
    month = _SP_MONTHS.get(mon_s)
    if not month:
        return None
    try:
        return date(y, month, d)
    except ValueError:
        return None


def _parse_cidob_listing(html: str, base: str) -> list[EventItem]:
    soup = BeautifulSoup(html, "lxml")
    events: list[EventItem] = []
    for art in soup.select("article.event.event-simple"):
        a = art.select_one('a.event-simple__link[href^="/actividades/"]')
        if not a:
            continue
        rel = a.get("href") or ""
        url = urljoin(base, rel)
        h3 = a.select_one("h3.event-simple__title")
        title = h3.get_text(" ", strip=True) if h3 else ""
        if not title:
            continue
        div_d = a.select_one("div.event-simple__date")
        raw = div_d.get_text(" ", strip=True) if div_d else ""
        d = _parse_cidob_date(raw) if raw else None
        starts = d.isoformat() if d else None
        events.append(
            EventItem(
                institution="CIDOB",
                title=title,
                url=url,
                starts_at=starts,
                label="",
                raw_date=raw,
                tier="nerd",
                area="Política i geopolítica",
                summary=_short_summary(title),
                source="cidob",
            )
        )
    return events


def fetch_cidob_events(list_url: str) -> list[EventItem]:
    logger.info("CIDOB: baixant %s", list_url)
    u = urlparse(list_url)
    base = f"{u.scheme}://{u.netloc}"
    html = fetch_text(list_url)
    return _parse_cidob_listing(html, base)
