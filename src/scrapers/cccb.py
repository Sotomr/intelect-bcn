from __future__ import annotations

import logging
import re
from datetime import date

from bs4 import BeautifulSoup

from intellect_filters import classify_area
from http_client import fetch_text
from models import EventItem

logger = logging.getLogger(__name__)


def _short_summary(title: str, label: str, max_len: int = 120) -> str:
    extra = (label or "").strip()
    if extra:
        base = f"{title.strip()}. {extra}"
    else:
        base = title.strip()
    if len(base) <= max_len:
        return base
    return base[: max_len - 1].rsplit(" ", 1)[0] + "…"

_CATALAN_MONTHS = {
    "gener": 1,
    "febrer": 2,
    "març": 3,
    "marc": 3,
    "abril": 4,
    "maig": 5,
    "juny": 6,
    "juliol": 7,
    "agost": 8,
    "setembre": 9,
    "octubre": 10,
    "novembre": 11,
    "desembre": 12,
}


def _parse_month_heading(text: str) -> tuple[int, int] | None:
    t = re.sub(r"\s+", " ", text.strip().lower())
    parts = t.split()
    if len(parts) < 2:
        return None
    try:
        year = int(parts[-1])
    except ValueError:
        return None
    month_w = parts[0]
    mo = _CATALAN_MONTHS.get(month_w)
    if not mo:
        return None
    return year, mo


def _parse_cccb_calendar(html: str) -> list[EventItem]:
    soup = BeautifulSoup(html, "lxml")
    events: list[EventItem] = []
    current_ym: tuple[int, int] | None = None

    for node in soup.find_all(["h2", "div"]):
        if node.name == "h2":
            classes = node.get("class") or []
            if "mb-spacer-300" in classes and "text-capitalize" in classes:
                parsed = _parse_month_heading(node.get_text())
                if parsed:
                    current_ym = (parsed[0], parsed[1])
            continue

        classes = node.get("class") or []
        if "agenda-card-row" not in classes:
            continue
        if not current_ym:
            continue

        year, month = current_ym
        day_el = node.select_one(".agenda-card-date-num")
        if not day_el:
            continue
        day_s = day_el.get_text(strip=True).lstrip("0") or "0"
        try:
            day_i = int(day_s)
        except ValueError:
            continue
        try:
            d = date(year, month, day_i)
        except ValueError:
            continue

        for a in node.select("a[href*='cccb.org'][href*='/ca/w/']"):
            href = (a.get("href") or "").strip()
            title = (a.get("title") or "").strip()
            if not title:
                tit = a.select_one(".agenda-card-title")
                title = tit.get_text(strip=True) if tit else ""
            if not title:
                continue
            pre = a.select_one(".agenda-card-pretitle")
            label = ""
            if pre:
                label = re.sub(r"\s+", " ", pre.get_text(" ", strip=True))
            raw = f"{day_i:02d}/{month:02d}/{year}"
            starts = d.isoformat()
            summ = _short_summary(title, label)
            events.append(
                EventItem(
                    institution="CCCB",
                    title=title,
                    url=href.split("#")[0],
                    starts_at=starts,
                    label=label[:120],
                    raw_date=raw,
                    tier="premium",
                    area=classify_area(title, "CCCB", label),
                    summary=summ,
                    source="cccb",
                )
            )

    seen: set[str] = set()
    out: list[EventItem] = []
    for e in events:
        k = e.stable_key()
        if k in seen:
            continue
        seen.add(k)
        out.append(e)
    return out


def fetch_cccb_events(calendar_url: str) -> list[EventItem]:
    logger.info("CCCB: baixant %s", calendar_url)
    html = fetch_text(
        calendar_url,
        extra_headers={
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    return _parse_cccb_calendar(html)
