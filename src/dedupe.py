from __future__ import annotations

import re

from models import EventItem

_TIER_RANK = {"premium": 0, "nerd": 1, "base": 2}


def _norm_title(t: str) -> str:
    t = t.lower()
    t = re.sub(r"[^a-zà-ÿ0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def dedupe_events(events: list[EventItem]) -> list[EventItem]:
    """
    Si el mateix títol + dia apareix de dues fonts (p. ex. Guia vs web institucional),
    es conserva la còpia amb millor capa editorial (premium > nerd > base).
    """
    best: dict[tuple[str, str], EventItem] = {}
    for e in events:
        key = (_norm_title(e.title), (e.starts_at or "")[:10])
        cur = best.get(key)
        if cur is None:
            best[key] = e
            continue
        r_new = _TIER_RANK.get(e.tier, 9)
        r_old = _TIER_RANK.get(cur.tier, 9)
        if r_new < r_old:
            best[key] = e
        elif r_new == r_old and len(e.url) < len(cur.url):
            best[key] = e
    return list(best.values())
