"""
Selector editorial: scoring, selecció de highlights i frases de valor.
Separa el «què val la pena» del scraping i la presentació.

Scoring en 3 passes:
  1. Llindar mínim de qualitat
  2. Puntuació per qualitat + adequació al perfil
  3. Diversitat de fonts (suau, mai baixant qualitat)

Interfície `judge` preparada per LLM (Fase 2).
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Iterable

from models import EventItem


def _norm(s: str) -> str:
    s = (s or "").lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip()


# ---- Perfil del producte ----

_PROFILE_KEYWORDS = (
    "politica", "politic", "filosofia", "pensament", "etica",
    "fisica", "astro", "cosmolog", "quantic", "matemat",
    "intel.ligencia artificial", "inteligencia artificial", "computacio",
    "algoritme", "dades", "ciberseguretat", "blockchain",
    "literatura", "assaig", "narrativ", "poetica",
    "democracia", "geopol", "internacional", "europa",
    "humanitats", "ciencia", "recerca",
    "seminari", "colloquium", "lecture",
    "foton", "gravitat", "particul",
    "utopi", "distopi", "resilienc",
)

_FORMAT_SCORES: dict[str, int] = {
    "debat": 18,
    "conferencia": 17,
    "seminari": 16,
    "xerrada": 12,
    "presentacio": 10,
    "taller": 6,
    "projeccio": 5,
    "exposicio": 4,
    "sessio": 2,
    "visita": -15,
    "article": -30,
}

_TIER_SCORES: dict[str, int] = {
    "premium": 20,
    "nerd": 15,
    "base": 0,
}

_CONFIDENCE_SCORES: dict[str, int] = {
    "high": 10,
    "medium": 5,
    "low": -10,
}

_SOURCE_BONUS: dict[str, int] = {
    "cccb": 5,
    "cidob": 8,
    "iccub": 8,
    "icfo": 8,
    "ice_csic": 7,
    "palau_macaya": 6,
    "la_central": 5,
}

_QUALITY_BONUS: dict[str, int] = {
    "premium": 8,
    "good": 0,
    "exploratory": -5,
}

_PENALTY_PATTERNS = (
    ("infantil", -30), ("infanteses", -30), ("familiar", -30),
    ("mirador", -20),
    ("ceguesa", -15), ("baixa visio", -15), ("portes obertes", -8),
)

# ---- Scoring constants ----
_BASE_SCORE = 50
_PROFILE_KEYWORD_BONUS = 4
_PROFILE_KEYWORD_CAP = 16
_DETAIL_TEXT_MIN_LEN = 100
_DETAIL_TEXT_BONUS = 6
_SPEAKERS_BONUS = 4
_TIME_BONUS = 2
_VENUE_BONUS = 2
_SERVICE_FORMAT_PENALTY = -20
_HIGHLIGHT_SCORE_FLOOR = 55
_EDITORIAL_PHRASE_MAX_LEN = 280
_MIN_DETAIL_LEN_FOR_PHRASE = 40
_MIN_SUMMARY_LEN_FOR_PHRASE = 30


@dataclass
class SelectionResult:
    event: EventItem
    score: int
    is_highlight: bool
    editorial_phrase: str
    category: str


def score_event(e: EventItem) -> int:
    """Score 0-100 basat en format, tier, perfil, enriquiment i font."""
    s = _BASE_SCORE

    s += _FORMAT_SCORES.get(e.event_kind, 0)
    s += _TIER_SCORES.get(e.tier, 0)
    s += _CONFIDENCE_SCORES.get(e.confidence, 0)

    blob = _norm(f"{e.title} {e.summary} {e.detail_text}")
    profile_matches = sum(1 for kw in _PROFILE_KEYWORDS if kw in blob)
    s += min(profile_matches * _PROFILE_KEYWORD_BONUS, _PROFILE_KEYWORD_CAP)

    src = (e.source or "").split(":")[0]
    s += _SOURCE_BONUS.get(src, 0)
    if e.source.startswith("rss:"):
        src_id = e.source[4:]
        s += _SOURCE_BONUS.get(src_id, 0)

    s += _QUALITY_BONUS.get(e.source_quality, 0)

    if e.detail_fetched and e.detail_text and len(e.detail_text) > _DETAIL_TEXT_MIN_LEN:
        s += _DETAIL_TEXT_BONUS
    if e.speakers:
        s += _SPEAKERS_BONUS
    if e.starts_at_time:
        s += _TIME_BONUS
    if e.venue:
        s += _VENUE_BONUS

    if e.is_service_format:
        s += _SERVICE_FORMAT_PENALTY

    tb = _norm(e.title)
    for pattern, penalty in _PENALTY_PATTERNS:
        if pattern in tb:
            s += penalty

    return max(0, min(100, s))


_KIND_LABELS: dict[str, str] = {
    "debat": "Debat",
    "conferencia": "Conferència",
    "seminari": "Seminari",
    "xerrada": "Xerrada",
    "presentacio": "Presentació",
    "taller": "Taller",
    "projeccio": "Projecció",
}


def _best_sentence(text: str, min_len: int = 25) -> str:
    """Extract the best descriptive sentence from a block of text."""
    sentences = re.split(r"(?<=[.!?])\s+", text[:800])
    skip_prefixes = ("abstract", "resum", "keywords", "http", "www.")
    for sent in sentences[:6]:
        sent = sent.strip()
        if len(sent) < min_len:
            continue
        if any(sent.lower().startswith(p) for p in skip_prefixes):
            continue
        return sent
    return ""


def _heuristic_phrase(e: EventItem) -> str:
    """Frase editorial amb veu: «per què importa», no un snippet sec."""
    inst = (e.institution or "").strip()
    title = (e.title or "").strip()
    speakers = (e.speakers or "").strip()
    detail = (e.detail_text or "").strip()
    summ = (e.summary or "").strip()
    fmt = _KIND_LABELS.get(e.event_kind, "")

    if detail and len(detail) > _MIN_DETAIL_LEN_FOR_PHRASE:
        best = _best_sentence(detail)
        if best:
            return _clip(best, _EDITORIAL_PHRASE_MAX_LEN)

    if summ and len(summ) > _MIN_DETAIL_LEN_FOR_PHRASE and _norm(summ[:80]) != _norm(title[:80]):
        best = _best_sentence(summ)
        if best:
            return _clip(best, _EDITORIAL_PHRASE_MAX_LEN)

    if speakers and fmt and inst:
        return _clip(f"{speakers} · {fmt} a {inst}.", _EDITORIAL_PHRASE_MAX_LEN)
    if speakers and inst:
        return _clip(f"Amb {speakers} — {inst}.", _EDITORIAL_PHRASE_MAX_LEN)
    if speakers and fmt:
        return _clip(f"{speakers} · {fmt}.", _EDITORIAL_PHRASE_MAX_LEN)

    if summ and len(summ) > _MIN_SUMMARY_LEN_FOR_PHRASE and _norm(summ[:60]) != _norm(title[:60]):
        return _clip(summ, _EDITORIAL_PHRASE_MAX_LEN)

    if fmt and inst:
        return f"{fmt} a {inst}."
    return inst or ""


def _clip(text: str, max_len: int = _EDITORIAL_PHRASE_MAX_LEN) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    cut = text[:max_len - 1].rsplit(" ", 1)[0]
    return cut + "…"


def _title_key(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").strip().lower())


def _source_bucket(e: EventItem) -> str:
    s = (e.source or "").strip()
    if s.startswith("rss:"):
        return s[:20]
    return s or "altres"


def select_candidates(
    events: Iterable[EventItem],
    *,
    max_highlights: int = 5,
    max_recommendations: int = 4,
    max_per_source: int = 3,
    judge: Callable[[list[EventItem]], list[SelectionResult]] | None = None,
) -> tuple[list[SelectionResult], list[SelectionResult]]:
    """
    Selecciona highlights i resta. Si `judge` és None, usa heurístiques.
    Quan tinguis LLM API key, passa `judge=llm_judge` per scoring real.
    """
    all_events = list(events)

    if judge is not None:
        results = judge(all_events)
        highlights = sorted(
            [r for r in results if r.is_highlight],
            key=lambda r: -r.score,
        )[:max_highlights]
        rest = [r for r in results if not r.is_highlight]
        return highlights, sorted(rest, key=lambda r: -r.score)

    # Pass 1: Score everything
    scored = [(e, score_event(e)) for e in all_events]
    scored.sort(key=lambda x: (-x[1], x[0].starts_at or "", x[0].title))

    # Pass 2: Pick highlights (no service formats, quality threshold)
    candidates = [(e, s) for e, s in scored if not e.is_service_format]

    picked: list[SelectionResult] = []
    counts: dict[str, int] = defaultdict(int)
    picked_titles: set[str] = set()

    for e, s in candidates:
        if len(picked) >= max_highlights:
            break
        if s < _HIGHLIGHT_SCORE_FLOOR:
            break
        tk = _title_key(e.title)
        if tk in picked_titles:
            continue
        # Pass 3: Soft source diversity
        b = _source_bucket(e)
        if counts[b] >= max_per_source:
            continue
        picked.append(SelectionResult(
            event=e,
            score=s,
            is_highlight=True,
            editorial_phrase=_heuristic_phrase(e),
            category=e.area,
        ))
        counts[b] += 1
        picked_titles.add(tk)

    picked_keys = {r.event.stable_key() for r in picked}
    rest: list[SelectionResult] = []
    for e, s in scored:
        if e.stable_key() in picked_keys:
            continue
        rest.append(SelectionResult(
            event=e,
            score=s,
            is_highlight=False,
            editorial_phrase=_heuristic_phrase(e),
            category=e.area,
        ))

    return picked, rest
