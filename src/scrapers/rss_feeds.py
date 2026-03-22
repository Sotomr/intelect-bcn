from __future__ import annotations

import html as html_lib
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests

from intellect_filters import classify_area, text_matches_intellect_blob
from models import EventItem
from rss_event_filter import rss_entry_is_valid_event

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RssFeed:
    source_id: str
    feed_url: str
    institution: str
    tier: str
    """Si True, només es conserven entrades que passin el filtre d’«alta densitat intel·lectual»."""
    apply_intellect_filter: bool


# User-Agent «navegador» per reduir 403 en alguns mitjans; Accept explícit per Atom/RSS.
_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; intelect-bcn/1.0; +https://github.com/Sotomr/intelect-bcn) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.5"
    ),
    "Accept-Language": "ca-ES,ca;q=0.9,es;q=0.8,en;q=0.7",
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
    # Mitjans i cultura (verificats HTTP 200 amb les capçaleres del projecte).
    RssFeed("directa", "https://directa.cat/feed", "Directa", "nerd", True),
    RssFeed("el_critic", "https://www.elcritic.cat/feed/", "El Crític", "nerd", True),
    RssFeed("ara_cultura", "https://www.ara.cat/rss/cultura/", "Ara Cultura", "nerd", True),
    RssFeed("beteve", "https://beteve.cat/feed/", "Betevé", "nerd", True),
    RssFeed("rezero", "https://rezero.cat/feed/", "Rezero", "nerd", True),
)

_ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DMY_DATE = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b")
_RE_HTML_TAG = re.compile(r"<[^>]+>")


def _strip_html(raw: str) -> str:
    if not raw:
        return ""
    t = _RE_HTML_TAG.sub(" ", raw)
    t = html_lib.unescape(t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _entry_plain_summary(entry: object, title: str) -> str:
    """Text pla per al digest (sense HTML); prioritza resum del feed."""
    raw = (getattr(entry, "summary", None) or getattr(entry, "description", None) or "") or ""
    if not raw.strip() and getattr(entry, "content", None):
        c = entry.content
        if isinstance(c, list) and c:
            raw = (c[0].get("value") if isinstance(c[0], dict) else str(c[0])) or ""
    plain = _strip_html(str(raw))
    if len(plain) < 35:
        return title[:400]
    return plain[:420] + ("…" if len(plain) > 420 else "")


def _rss_today() -> date:
    try:
        from zoneinfo import ZoneInfo

        tz_name = (os.getenv("TIMEZONE") or "Europe/Madrid").strip() or "Europe/Madrid"
        return datetime.now(ZoneInfo(tz_name)).date()
    except Exception:
        return datetime.now(timezone.utc).date()


def _extract_dates_from_text(text: str) -> list[date]:
    """Dates explícites al títol o resum (l’acte sol ser futur; la pub. del feed sovint és passada)."""
    out: list[date] = []
    for m in _ISO_DATE.finditer(text):
        try:
            out.append(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        except ValueError:
            continue
    for m in _DMY_DATE.finditer(text):
        try:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            out.append(date(y, mo, d))
        except ValueError:
            continue
    return out


def _dates_from_feed_entry(e: object) -> list[date]:
    out: list[date] = []
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(e, attr, None)
        if t:
            try:
                dt = datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)
                out.append(dt.date())
            except (OverflowError, OSError, ValueError):
                continue
    for attr in ("published", "updated"):
        raw = getattr(e, attr, None)
        if raw and str(raw).strip():
            try:
                dt = parsedate_to_datetime(str(raw))
                out.append(dt.date())
            except (TypeError, ValueError, OSError):
                continue
    return out


def _pick_event_date(e: object, title: str, summary: str) -> str | None:
    today = _rss_today()
    blob = f"{title}\n{summary}"
    from_text = _extract_dates_from_text(blob)
    horizon = today + timedelta(days=500)
    upcoming = [d for d in set(from_text) if today <= d <= horizon]
    if upcoming:
        return min(upcoming).isoformat()
    feed_ds = _dates_from_feed_entry(e)
    if feed_ds:
        return max(feed_ds).isoformat()
    return None


def _rss_http_timeout() -> tuple[float, float]:
    raw = (os.getenv("RSS_HTTP_READ_TIMEOUT") or "").strip()
    if raw.isdigit():
        read_s = float(raw)
    else:
        read_s = 55.0
    read_s = max(20.0, min(120.0, read_s))
    return (15.0, read_s)


def _fetch_one_feed(spec: RssFeed, *, max_per_feed: int, timeout: tuple[float, float]) -> list[EventItem]:
    out: list[EventItem] = []
    try:
        r = requests.get(spec.feed_url, timeout=timeout, headers=_HTTP_HEADERS)
        r.raise_for_status()
        d = feedparser.parse(r.content)
    except Exception as e:
        logger.warning("RSS %s: error baixant o parsejant (%s)", spec.source_id, e)
        return out

    if getattr(d, "bozo", False) and not d.entries:
        logger.warning("RSS %s: feed buit o malformat", spec.source_id)
        return out

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
        summary_plain = _strip_html(summary)
        day = _pick_event_date(e, title, summary_plain)
        if not day:
            continue
        n += 1
        plain_for_item = _entry_plain_summary(e, title)
        full_plain = _strip_html(summary)[:2500]
        if not rss_entry_is_valid_event(
            source_id=spec.source_id,
            title=title,
            summary=full_plain,
            link=link,
        ):
            continue
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
                summary=plain_for_item,
                source=f"rss:{spec.source_id}",
            )
        )
    logger.info("RSS %s: %s entrades (després de filtres)", spec.source_id, n)
    return out


def fetch_rss_feeds(*, max_per_feed: int = 25) -> list[EventItem]:
    timeout = _rss_http_timeout()
    out: list[EventItem] = []
    feeds = list(RSS_FEEDS)
    workers = min(8, len(feeds))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {
            ex.submit(_fetch_one_feed, spec, max_per_feed=max_per_feed, timeout=timeout): spec
            for spec in feeds
        }
        for fut in as_completed(futs):
            try:
                out.extend(fut.result())
            except Exception as e:
                spec = futs[fut]
                logger.warning("RSS %s: error inesperat (%s)", spec.source_id, e)
    logger.info("RSS total: %s entrades", len(out))
    return out
