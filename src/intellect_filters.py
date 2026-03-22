from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from models import EventItem

_RE_D_A = re.compile(r"d['\u2019']a", re.IGNORECASE)

# Paraules que orienten cap a densitat intel·lectual (català/castellà, sense ser exhaustives)
INCLUDE_TERMS: tuple[str, ...] = (
    "conferència",
    "conferencia",
    "debat",
    "xerrada",
    "seminari",
    "seminario",
    "taller",
    "curs ",
    " curs",
    "presentació",
    "presentacion",
    "llibre",
    "literatura",
    "filosofia",
    "filosofía",
    "pensament",
    "pensamiento",
    "humanitats",
    "humanidades",
    "ciència",
    "ciencia",
    "astrofís",
    "astrofis",
    "cosmolog",
    "física",
    "fisica",
    "matemàt",
    "matemat",
    "quàntic",
    "cuantic",
    "intel·ligència artificial",
    "inteligencia artificial",
    "política",
    "politica",
    "geopol",
    "democràcia",
    "democracia",
    "història",
    "historia",
    "assaig",
    "ensayo",
    "investigació",
    "investigacion",
    "col·loqui",
    "coloquio",
    "tertúlia",
    "tertulia",
    "convers",
    "mesa rodona",
    "mesa redonda",
    "exposició",
    "exposicion",
    "projecció",
    "proyeccion",
    "documental",
    "simposi",
    "simposio",
    "jornad",
    "festival",
)

# Excloure soroll evident (encara que coincideixi amb INCLUDE)
EXCLUDE_TERMS: tuple[str, ...] = (
    "infantil",
    "familiar",
    "en família",
    "nadó",
    "nado",
    "activitat esportiva",
    "zumba",
    "gimnàstica",
    "gimnastica",
    "criança autogestionat",
    "grup de criança",
    "nous vins",
    "cal bardera",
)

# Si el nom del lloc conté aquests fragments, pujem la rellevància (capa «premium» / institucions fortes)
PREMIUM_VENUE_HINTS: tuple[str, ...] = (
    "cccb",
    "ateneu",
    "cosmocaixa",
    "caixafòrum",
    "caixaforum",
    "macba",
    "miró",
    "miro",
    "santa mònica",
    "santa monica",
    "palau macaya",
    "macaya",
    "mies van der rohe",
    "mapfre",
    "kbr",
    "biblioteca de catalunya",
    "institut d'estudis catalans",
    "iec",
    "ub ",
    "universitat de barcelona",
    "filosofia",
    "upf",
    "upc",
    "icfo",
    "iccub",
    "ice-csic",
    "ice ",
    "csic",
)


def _norm(s: str) -> str:
    s = s.lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s).strip()
    return s


def text_matches_intellect_blob(title: str, extra: str = "") -> bool:
    blob = _norm(f"{title} {extra}")
    if any(_norm(x) in blob for x in EXCLUDE_TERMS):
        return False
    return any(_norm(x) in blob for x in INCLUDE_TERMS)


def is_noise_title_intellect(title: str) -> bool:
    """
    Esdeveniments que passen el filtre per «festival» però són programa de cinema repetit
    (mateix bloc molts dies al digest), no «idees» al sentit del bot.
    """
    if not title or not str(title).strip():
        return False
    t = str(title).lower()
    if "festival de cinema de barcelona" in t:
        return True
    if "festival" in t and "cinema" in t and _RE_D_A.search(title):
        return True
    return False


def filter_noise_events(events: list[EventItem]) -> list[EventItem]:
    """Elimina soroll editorial abans de deduplicar (totes les fonts)."""
    import logging

    out: list[EventItem] = []
    dropped = 0
    for e in events:
        if is_noise_title_intellect(e.title):
            dropped += 1
            continue
        out.append(e)
    if dropped:
        logging.getLogger(__name__).info(
            "Filtre soroll: %s esdeveniments exclos (cinema/festival repetit)", dropped
        )
    return out


def venue_tier_boost(institution_name: str) -> bool:
    n = _norm(institution_name or "")
    return any(h in n for h in PREMIUM_VENUE_HINTS)


def classify_area(title: str, institution: str, label: str = "") -> str:
    """Taxonomia expressiva; implementació a `editorial`."""
    from editorial import classify_area as _classify

    return _classify(title, institution, label)
