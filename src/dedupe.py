from __future__ import annotations

import re

from models import EventItem

_TIER_RANK = {"premium": 0, "nerd": 1, "base": 2}

_YEAR_RE = re.compile(r"\b20\d{2}\b")


def _norm_title(t: str) -> str:
    t = t.lower()
    t = re.sub(r"[^a-zà-ÿ0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _fuzzy_key(t: str) -> str:
    """Strip years, articles and prepositions for fuzzy comparison."""
    t = _YEAR_RE.sub("", t)
    t = re.sub(r"\b(de|del|per|a|la|el|les|els|l|d)\b", "", t)
    return re.sub(r"\s+", " ", t).strip()


def _better(new: EventItem, old: EventItem) -> bool:
    r_new = _TIER_RANK.get(new.tier, 9)
    r_old = _TIER_RANK.get(old.tier, 9)
    if r_new < r_old:
        return True
    if r_new == r_old and len(new.url) < len(old.url):
        return True
    return False


def dedupe_events(events: list[EventItem]) -> list[EventItem]:
    """
    Dedup en dues passades:
    1. Títol normalitzat exacte + mateix dia.
    2. Títol fuzzy (sense anys/articles) + mateix dia — captura quasi-duplicats.
    """
    best: dict[tuple[str, str], EventItem] = {}
    for e in events:
        key = (_norm_title(e.title), (e.starts_at or "")[:10])
        cur = best.get(key)
        if cur is None:
            best[key] = e
        elif _better(e, cur):
            best[key] = e

    fuzzy_best: dict[tuple[str, str], tuple[str, EventItem]] = {}
    for exact_key, e in best.items():
        fk = (_fuzzy_key(_norm_title(e.title)), (e.starts_at or "")[:10])
        cur = fuzzy_best.get(fk)
        if cur is None:
            fuzzy_best[fk] = (exact_key[0], e)
        elif _better(e, cur[1]):
            fuzzy_best[fk] = (exact_key[0], e)

    return [e for _, e in fuzzy_best.values()]
