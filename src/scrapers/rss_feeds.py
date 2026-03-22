from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser
import requests

from intellect_filters import classify_area, text_matches_intellect_blob
from models import EventItem

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RssFeed:
    source_id: str
    feed_url: str
    institution: str
    tier: str
    """Si True, només es conserven entrades que passin el filtre d’«alta densitat intel·lectual»."""
    apply_intellect_filter: bool


_HTTP_HEADERS = {
    "User-Agent": "intelect-bcn/1.0 (+https://github.com/Sotomr/intelect-bcn)",
    "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
}

# Fonts amb RSS públic i estable (ampliïs aquí quan trobeu nous feeds vàlids).
# Nota: molts sites bloquegen feedparser sense User-Agent; es baixa amb requests.
RSS_FEEDS: tuple[RssFeed, ...] = (
    RssFeed("iec", "https://www.iec.cat/feed/", "Institut d’Estudis Catalans", "nerd", False),
    RssFeed("scm", "https://scm.iec.cat/feed/", "Societat Catalana de Matemàtiques", "nerd", False),
    RssFeed("macba", "https://www.macba.cat/feed/", "MACBA", "premium", True),
    RssFeed("ateneu", "https://ateneubcn.cat/feed/", "Ateneu Barcelonès", "premium", True),
    RssFeed("hangar", "https://www.hangar.org/feed/", "Hangar", "premium", False),
    RssFeed("mies", "https://www.miesbcn.com/ca/feed/", "Fundació Mies van der Rohe", "premium", True),
    RssFeed(
        "enginyers_bcn",
        "https://enginyersbcn.cat/feed/",
        "Col·legi d’Enginyers de Barcelona",
        "nerd",
        True,
    ),
)


def _date_from_entry(e: object) -> str | None:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(e, attr, None)
        if t:
            try:
                dt = datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)
                return dt.date().isoformat()
            except (OverflowError, OSError, ValueError):
                continue
    return None


def fetch_rss_feeds(*, max_per_feed: int = 25) -> list[EventItem]:
    out: list[EventItem] = []
    for spec in RSS_FEEDS:
        try:
            r = requests.get(
                spec.feed_url,
                timeout=(15, 90),
                headers=_HTTP_HEADERS,
            )
            r.raise_for_status()
            d = feedparser.parse(r.content)
        except Exception as e:
            logger.warning("RSS %s: error baixant o parsejant (%s)", spec.source_id, e)
            continue
        if getattr(d, "bozo", False) and not d.entries:
            logger.warning("RSS %s: feed buit o malformat", spec.source_id)
            continue
        n = 0
        for e in d.entries:
            if n >= max_per_feed:
                break
            title = (getattr(e, "title", None) or "").strip()
            link = (getattr(e, "link", None) or "").strip()
            if not title or not link:
                continue
            summary = (getattr(e, "summary", None) or getattr(e, "description", None) or "")
            if spec.apply_intellect_filter and not text_matches_intellect_blob(
                title, summary[:2000]
            ):
                continue
            day = _date_from_entry(e)
            if not day:
                continue
            n += 1
            out.append(
                EventItem(
                    institution=spec.institution,
                    title=title,
                    url=link,
                    starts_at=day,
                    label="RSS",
                    raw_date=day,
                    tier=spec.tier,
                    area=classify_area(title, spec.institution, "RSS"),
                    summary=title[:200] + ("…" if len(title) > 200 else ""),
                    source=f"rss:{spec.source_id}",
                )
            )
        logger.info("RSS %s: %s entrades (després de filtres)", spec.source_id, n)
    logger.info("RSS total: %s entrades", len(out))
    return out
