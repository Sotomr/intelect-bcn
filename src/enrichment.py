"""
Enriquiment: obre la pàgina oficial de cada candidat vàlid i n'extreu
hora, lloc, ponents i descripció llarga.

S'executa al job diari, només sobre candidats que han passat la validació.
"""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup

from http_client import fetch_text
from models import EventItem

logger = logging.getLogger(__name__)

_RE_TIME = re.compile(r"\b(\d{1,2})[:h](\d{2})\b")
_RE_TIME_DOTTED = re.compile(r"\b(\d{1,2})\.(\d{2})\s*(?:h\b|hores\b)")
_RE_VENUE_HINTS = re.compile(
    r"(sala|auditori|aula|room|espai|hall|teatre|atri)\b",
    re.IGNORECASE,
)

_SKIP_SOURCES = frozenset({"gencat"})


def _clean_text(raw: str, max_len: int = 2000) -> str:
    t = re.sub(r"\s+", " ", raw).strip()
    return t[:max_len] if len(t) > max_len else t


def _extract_time(text: str) -> str:
    for rx in (_RE_TIME, _RE_TIME_DOTTED):
        m = rx.search(text)
        if m:
            h, mi = int(m.group(1)), int(m.group(2))
            if 0 <= h <= 23 and 0 <= mi <= 59:
                return f"{h:02d}:{mi:02d}"
    return ""


# ---- Extractors per font ----

def _enrich_cccb(soup: BeautifulSoup, e: EventItem) -> None:
    body = soup.select_one("body")
    if not body:
        return
    text = body.get_text(" ", strip=True)

    idx = text.find("Comprar entrades")
    if idx < 0:
        idx = text.find("comprar entrades")
    if idx < 0:
        idx = 0
    chunk = text[idx:idx + 3000]

    if not e.starts_at_time:
        horari_idx = chunk.find("Data i horari")
        if horari_idx > 0:
            e.starts_at_time = _extract_time(chunk[horari_idx:horari_idx + 200])
        else:
            e.starts_at_time = _extract_time(chunk)

    if not e.detail_text:
        # Text between "Comprar entrades" / "Presentació" and "Participants" / "Informació pràctica"
        desc_start = chunk.find("Presentació")
        if desc_start < 0:
            desc_start = 20
        desc_end = len(chunk)
        for marker in ("Participants", "Informació pràctica", "Data i horari", "Organitza"):
            mi = chunk.find(marker, desc_start + 10)
            if mi > 0:
                desc_end = min(desc_end, mi)
        desc = chunk[desc_start:desc_end].strip()
        if desc.startswith("Presentació"):
            desc = desc[len("Presentació"):].strip()
        if len(desc) > 40:
            e.detail_text = _clean_text(desc, 1500)

    if not e.speakers:
        pi = chunk.find("Participants")
        if pi > 0:
            org_i = chunk.find("Organitza", pi)
            info_i = chunk.find("Informació pràctica", pi)
            end = min(x for x in (org_i, info_i, len(chunk)) if x > 0)
            speakers_text = chunk[pi + len("Participants"):end].strip()
            names = [n.strip() for n in re.split(r"\s{2,}", speakers_text) if len(n.strip()) > 2]
            if names:
                e.speakers = "; ".join(names[:6])

    if not e.venue:
        for pattern in (r"Lloc\s+(.+?)(?:\s{2}|$)", r"Sala\s+(.+?)(?:\s{2}|$)"):
            m = re.search(pattern, chunk)
            if m:
                e.venue = m.group(1).strip()[:100]
                break


def _enrich_iccub(soup: BeautifulSoup, e: EventItem) -> None:
    for row in soup.select(".field--label-inline, .field"):
        label_el = row.select_one(".field__label")
        value_el = row.select_one(".field__item, .field__items")
        if not label_el or not value_el:
            continue
        label = label_el.get_text(strip=True).lower()
        value = value_el.get_text(strip=True)
        if "by" in label and not e.speakers:
            e.speakers = value[:200]
        elif "date" in label and not e.starts_at_time:
            e.starts_at_time = _extract_time(value)
        elif "place" in label or "room" in label:
            if not e.venue:
                e.venue = value[:100]

    body = soup.select_one(".field--name-body")
    if body and not e.detail_text:
        t = body.get_text(" ", strip=True)
        if t.lower().startswith("abstract:"):
            t = t[9:].strip()
        if len(t) > 30:
            e.detail_text = _clean_text(t, 1500)


def _enrich_cidob(soup: BeautifulSoup, e: EventItem) -> None:
    body = soup.select_one("body")
    if not body:
        return
    text = body.get_text(" ", strip=True)

    if not e.starts_at_time:
        e.starts_at_time = _extract_time(text[:2000])

    desc = soup.select_one(".field--name-body, .event-detail__body, .text-formatted")
    if desc and not e.detail_text:
        t = desc.get_text(" ", strip=True)
        if len(t) > 40:
            e.detail_text = _clean_text(t, 1500)

    if not e.speakers:
        for pattern in (r"[Pp]onente?s?:?\s*(.+?)(?:\.|$)", r"[Pp]articipante?s?:?\s*(.+?)(?:\.|$)"):
            m = re.search(pattern, text[:3000])
            if m:
                e.speakers = m.group(1).strip()[:200]
                break


def _enrich_guia(soup: BeautifulSoup, e: EventItem) -> None:
    """Extractor per a pàgines de guia.barcelona.cat/ca/agenda/{id}."""
    body = soup.select_one("body")
    if not body:
        return
    text = body.get_text(" ", strip=True)

    if not e.starts_at_time:
        e.starts_at_time = _extract_time(text[:3000])

    if not e.institution:
        for sel in (".event-detail__place", ".field--name-field-place", ".col-location"):
            el = soup.select_one(sel)
            if el:
                place = el.get_text(strip=True)
                if place and len(place) > 2:
                    e.institution = place[:120]
                    break

    if not e.venue:
        for sel in (".event-detail__address", ".field--name-field-address"):
            el = soup.select_one(sel)
            if el:
                addr = el.get_text(strip=True)
                if addr and len(addr) > 4:
                    e.venue = addr[:120]
                    break

    if not e.detail_text:
        desc = soup.select_one(".event-detail__description, .field--name-body, .event-body")
        if desc:
            t = desc.get_text(" ", strip=True)
            if len(t) > 30:
                e.detail_text = _clean_text(t, 1500)
        else:
            paras = body.select("p")
            chunks = [p.get_text(strip=True) for p in paras if len(p.get_text(strip=True)) > 30]
            if chunks:
                e.detail_text = _clean_text(" ".join(chunks[:8]), 1500)


def _enrich_generic(soup: BeautifulSoup, e: EventItem) -> None:
    """Extractor genèric per a fonts RSS i altres."""
    body = soup.select_one("article, main, .content, .entry-content, body")
    if not body:
        return
    text = body.get_text(" ", strip=True)

    if not e.starts_at_time:
        e.starts_at_time = _extract_time(text[:2000])

    if not e.detail_text:
        paras = body.select("p")
        chunks = [p.get_text(strip=True) for p in paras if len(p.get_text(strip=True)) > 30]
        if chunks:
            e.detail_text = _clean_text(" ".join(chunks[:10]), 1500)

    if not e.venue and _RE_VENUE_HINTS.search(text[:2000]):
        m = _RE_VENUE_HINTS.search(text[:2000])
        if m:
            start = max(0, m.start() - 10)
            snippet = text[start:m.end() + 80]
            e.venue = _clean_text(snippet, 100)


_SOURCE_EXTRACTORS = {
    "cccb": _enrich_cccb,
    "cidob": _enrich_cidob,
    "iccub": _enrich_iccub,
    "guia_bcn": _enrich_guia,
}


def enrich_event(e: EventItem) -> EventItem:
    """Obre la pàgina oficial i extreu detalls. Modifica l'EventItem in-place."""
    if e.detail_fetched:
        return e

    src = e.source.split(":")[0] if ":" in e.source else e.source
    if src in _SKIP_SOURCES:
        e.detail_fetched = True
        return e

    try:
        html = fetch_text(e.url, timeout=(10.0, 20.0), max_attempts=2)
    except Exception as exc:
        logger.debug("Enrichment: no s'ha pogut obrir %s: %s", e.url[:80], exc)
        e.detail_fetched = True
        return e

    soup = BeautifulSoup(html, "lxml")
    extractor = _SOURCE_EXTRACTORS.get(src, _enrich_generic)
    try:
        extractor(soup, e)
    except Exception as exc:
        logger.debug("Enrichment: error parsejant %s: %s", e.url[:80], exc)

    e.detail_fetched = True
    return e


def enrich_batch(
    events: list[EventItem],
    *,
    max_workers: int = 4,
    only_high_quality: bool = True,
) -> list[EventItem]:
    """
    Enriqueix en paral·lel. Si only_high_quality=True, només enriqueix
    candidats amb source_quality != "exploratory" (no gastar requests en soroll).
    """
    to_enrich = []
    skip = []
    for e in events:
        if e.detail_fetched:
            skip.append(e)
        elif only_high_quality and e.source_quality == "exploratory":
            skip.append(e)
        else:
            to_enrich.append(e)

    if not to_enrich:
        return events

    logger.info("Enriquiment: %s candidats a enriquir", len(to_enrich))
    workers = min(max_workers, len(to_enrich))

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(enrich_event, e): i for i, e in enumerate(to_enrich)}
        for fut in as_completed(futs):
            try:
                fut.result()
            except Exception as exc:
                logger.debug("Enrichment thread error: %s", exc)

    enriched = sum(1 for e in to_enrich if e.detail_text)
    logger.info("Enriquiment: %s/%s amb detail_text", enriched, len(to_enrich))
    return events
