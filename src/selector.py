"""
Selector editorial: scoring, selecció de highlights i frases de valor.
Separa el «què val la pena» del scraping i la presentació.

Dissenyat amb una interfície neta per plugar un LLM com a jutge
(veure paràmetre `judge` a `select_candidates`).
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
    "humanitats", "ciencia",
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
    "palau_macaya": 6,
    "la_central": 5,
}

_PENALTY_PATTERNS = (
    ("infantil", -30), ("familiar", -30), ("mirador", -20),
    ("ceguesa", -15), ("baixa visio", -15), ("portes obertes", -8),
)


@dataclass
class SelectionResult:
    event: EventItem
    score: int
    is_highlight: bool
    editorial_phrase: str
    category: str


def score_event(e: EventItem) -> int:
    """Score 0-100 basat en format, tier, perfil, confiança i font."""
    s = 50
    s += _FORMAT_SCORES.get(e.event_kind, 0)
    s += _TIER_SCORES.get(e.tier, 0)
    s += _CONFIDENCE_SCORES.get(e.confidence, 0)

    blob = _norm(f"{e.title} {e.summary}")
    if any(kw in blob for kw in _PROFILE_KEYWORDS):
        s += 10

    src = (e.source or "").split(":")[0]
    s += _SOURCE_BONUS.get(src, 0)
    if e.source.startswith("rss:"):
        src_id = e.source[4:]
        s += _SOURCE_BONUS.get(src_id, 0)

    tb = _norm(e.title)
    for pattern, penalty in _PENALTY_PATTERNS:
        if pattern in tb:
            s += penalty

    return max(0, min(100, s))


def _heuristic_phrase(e: EventItem) -> str:
    """Frase curta de valor basada en format + tema + institució."""
    kind = e.event_kind or "sessio"
    inst = (e.institution or "").strip()
    title = (e.title or "").strip()

    kind_labels = {
        "debat": "Debat",
        "conferencia": "Conferència",
        "seminari": "Seminari",
        "xerrada": "Xerrada",
        "presentacio": "Presentació",
        "taller": "Taller",
        "projeccio": "Projecció",
        "exposicio": "Exposició",
        "sessio": "Sessió",
        "visita": "Visita",
    }
    fmt = kind_labels.get(kind, "Sessió")

    summ = (e.summary or "").strip()
    if summ and len(summ) > 60 and _norm(summ[:80]) != _norm(title[:80]):
        clip = summ[:220].rsplit(" ", 1)[0] if len(summ) > 220 else summ
        return clip

    blob = _norm(f"{title} {e.label}")
    themes = []
    if any(x in blob for x in ("politic", "democrac", "geopol", "internacional")):
        themes.append("política i món")
    if any(x in blob for x in ("filosof", "pensament", "humanitat", "etica")):
        themes.append("pensament")
    if any(x in blob for x in ("fisic", "astro", "cosmol", "quantic", "matemat")):
        themes.append("ciència")
    if any(x in blob for x in ("literatur", "novel.la", "poetic", "narrativ", "assaig")):
        themes.append("literatura")
    if any(x in blob for x in ("dades", "algoritme", "computac", "intel.lig")):
        themes.append("tecnologia")
    if any(x in blob for x in ("art ", " art", "visual", "exposici")):
        themes.append("art")

    if themes:
        return f"{fmt} sobre {', '.join(themes[:2])} — {inst}."
    return f"{fmt} a {inst}." if inst else f"{fmt}."


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

    scored = [(e, score_event(e)) for e in all_events]
    scored.sort(key=lambda x: (-x[1], x[0].starts_at or "", x[0].title))

    # Visites i servei mai als destacats
    candidates = [(e, s) for e, s in scored if e.event_kind != "visita"]

    picked: list[SelectionResult] = []
    counts: dict[str, int] = defaultdict(int)
    picked_titles: set[str] = set()

    for e, s in candidates:
        if len(picked) >= max_highlights:
            break
        if s < 55:
            break
        tk = _title_key(e.title)
        if tk in picked_titles:
            continue
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
