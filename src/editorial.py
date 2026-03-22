"""
Capa editorial: puntuació, formats, diversitat de fonts i taxonomia més expressiva.
La pregunta no és només «què cau a la finestra», sinó «què mereix destacar aquesta setmana».
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from typing import Iterable

from models import EventItem


def _norm(s: str) -> str:
    s = (s or "").lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s).strip()
    return s


# Taxonomia més intencionada (menys «calax de sastre» que «General (idees)»).
AREA_SECTION_ORDER: tuple[str, ...] = (
    "Filosofia i pensament",
    "Política i món",
    "Ciència i cosmos",
    "Tecnologia i computació",
    "Art i cultura crítica",
    "Literatura i idees",
    "Ciutat i institucions",
)


def classify_area(title: str, institution: str, label: str = "") -> str:
    blob = _norm(f"{title} {institution} {label}")
    if any(
        x in blob
        for x in (
            "intel·ligència artificial",
            "inteligencia artificial",
            "ciberseguretat",
            "ciber",
            "blockchain",
            "algoritme",
            "dades",
            "big data",
            "software lliure",
        )
    ):
        return "Tecnologia i computació"
    if any(
        x in blob
        for x in (
            "polític",
            "politic",
            "geopol",
            "democràcia",
            "democracia",
            "europa",
            "internacional",
            "ucraïn",
            "ucrain",
            "cidob",
            "govern",
            "dret",
        )
    ):
        return "Política i món"
    if any(
        x in blob
        for x in (
            "filosofia",
            "filosofía",
            "pensament",
            "humanitats",
            "ètica",
            "etica",
            "institut d'humanitats",
        )
    ):
        return "Filosofia i pensament"
    if any(
        x in blob
        for x in (
            "ciència",
            "ciencia",
            "física",
            "astro",
            "cosmolog",
            "matemàt",
            "quàntic",
            "icfo",
            "iccub",
            "cosmocaixa",
            "enginy",
            "enginyer",
            "energia",
            "sostenibilitat",
            "biolog",
            "químic",
        )
    ):
        return "Ciència i cosmos"
    if any(
        x in blob
        for x in (
            "art",
            "macba",
            "miró",
            "miro",
            "exposició",
            "exposicion",
            "tapies",
            "santa mònica",
            "santa monica",
            "hangar",
            "mies",
        )
    ):
        return "Art i cultura crítica"
    if any(x in blob for x in ("literatura", "llibre", "presentació del llibre", "poèt", "narrativ", "assaig")):
        return "Literatura i idees"
    if any(x in blob for x in ("visita", "mirador", "portes obertes", "accessible")):
        return "Ciutat i institucions"
    return "Ciutat i institucions"


def _title_key(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").strip().lower())


def source_bucket(e: EventItem) -> str:
    s = (e.source or "").strip()
    if s == "cccb":
        return "cccb"
    if s == "guia_bcn":
        return "guia_bcn"
    if s == "cidob":
        return "cidob"
    if s.startswith("rss:"):
        return s[:20]
    return s or "altres"


def detect_format_label(e: EventItem) -> str:
    t = _norm(f"{e.title} {e.label}")
    if "debat" in t or "debats" in t:
        return "Debat"
    if "col·loqui" in t or "coloquio" in t or "col.loqui" in t:
        return "Col·loqui"
    if "conferència" in t or "conferencia" in t:
        return "Conferència"
    if "seminari" in t or "seminario" in t:
        return "Seminari"
    if "xerrada" in t or "convers" in t or "tertúlia" in t:
        return "Xerrada"
    if "presentació" in t or "presentacion" in t:
        return "Presentació"
    if "visita guiada" in t or (t.startswith("visita ") and "exposici" in t):
        return "Visita guiada"
    if "visita" in t or "mirador" in t:
        return "Visita"
    if "taller" in t or "curs " in t or " curs" in t:
        return "Taller / curs"
    if "projecció" in t or "documental" in t or "audiovisual" in t:
        return "Audiovisual"
    if "exposició" in t or "exposicion" in t:
        return "Exposició"
    return "Activitat"


def editorial_score(e: EventItem) -> float:
    s = 42.0
    s += {"premium": 14.0, "nerd": 11.0, "base": 0.0}.get(e.tier, 0.0)
    fmt = detect_format_label(e)
    fmt_bonus = {
        "Debat": 16.0,
        "Col·loqui": 14.0,
        "Conferència": 15.0,
        "Seminari": 14.0,
        "Xerrada": 10.0,
        "Presentació": 9.0,
        "Taller / curs": 5.0,
        "Exposició": 4.0,
        "Audiovisual": 3.0,
        "Visita guiada": -6.0,
        "Visita": -14.0,
        "Activitat": 2.0,
    }
    s += fmt_bonus.get(fmt, 0.0)
    tb = _norm(e.title)
    if "infant" in tb or "familiar" in tb:
        s -= 28.0
    if "mirador" in tb:
        s -= 12.0
    if "accessible" in tb and "exposici" in tb:
        s -= 6.0
    if "portes obertes" in tb:
        s -= 8.0
    src = (e.source or "")
    if src.startswith("rss:") or src in ("cidob", "guia_bcn"):
        s += 5.0
    if "cidob" in _norm(e.institution):
        s += 6.0
    if "iec" in _norm(e.institution) or "scm" in _norm(e.institution):
        s += 4.0
    return s


def editorial_blurb(e: EventItem) -> str:
    t = _norm(f"{e.title} {e.label}")
    summ = (e.summary or "").strip()
    if "debat" in t or "debats" in t:
        return "Debat amb densitat; bon marc per seguir el fil argumental."
    if "conferència" in t or "conferencia" in t:
        return "Conferència amb cos; útil per situar conceptes i autors."
    if "seminari" in t or "col·loqui" in t:
        return "Format seminarial: aprofundiment i intercanvi."
    if "filosofia" in t or "pensament" in t or "humanitats" in t:
        return "Filosofia i pensament crític al centre."
    if "polític" in t or "democràcia" in t or "geopol" in t:
        return "Política i idees: context actual i conceptes."
    if "ciència" in t or "cosmolog" in t or "física" in t or "matemàt" in t:
        return "Ciència i rigor conceptual."
    if "literatura" in t or "llibre" in t:
        return "Literatura i idees en primer pla."
    if "visita" in t and "debat" not in t:
        return "Activitat de descobriment; menys densitat de debat que una taula o conferència."
    if "," in (e.title or "") and len(e.title or "") > 35:
        return "Taula amb diversos ponents; conversa amb pes específic."
    if summ and len(summ) > 25:
        return summ[:200]
    return "Proposta dins el radar intel·lectual de la setmana."


def pick_highlights(
    events: Iterable[EventItem],
    *,
    k: int = 7,
    max_per_source: int = 3,
) -> tuple[list[EventItem], list[EventItem]]:
    """Selecció greedy per puntuació amb quota suau per font (evita monopol del CCCB)."""
    evs = list(events)
    if not evs:
        return [], []
    scored = sorted(evs, key=lambda e: editorial_score(e), reverse=True)
    picked: list[EventItem] = []
    counts: dict[str, int] = defaultdict(int)
    picked_titles: set[str] = set()
    for e in scored:
        if len(picked) >= k:
            break
        tk = _title_key(e.title)
        if tk in picked_titles:
            continue
        b = source_bucket(e)
        if counts[b] >= max_per_source:
            continue
        picked.append(e)
        counts[b] += 1
        picked_titles.add(tk)
    keys = {e.stable_key() for e in picked}
    rest = [e for e in evs if e.stable_key() not in keys]
    rest.sort(key=lambda e: (-editorial_score(e), e.starts_at or "", e.title))
    picked.sort(key=lambda e: (-editorial_score(e), e.starts_at or "", e.title))
    return picked, rest


def split_agenda_expanded(rest: list[EventItem], *, score_threshold: float = 36.0) -> tuple[list[EventItem], list[EventItem]]:
    """Separa «recomanacions fortes» de visites / baixa puntuació (agenda ampliada)."""
    main: list[EventItem] = []
    low: list[EventItem] = []
    for e in rest:
        fmt = detect_format_label(e)
        sc = editorial_score(e)
        if fmt in ("Visita", "Visita guiada"):
            low.append(e)
        elif sc < score_threshold:
            low.append(e)
        else:
            main.append(e)
    return main, low


def display_source_line(e: EventItem) -> str:
    """Una sola línia de context: institució + font quan aporta (evita «CCCB · CCCB»)."""
    inst = (e.institution or "").strip()
    src = (e.source or "").strip()
    if src == "cccb" and inst.lower() == "cccb":
        return inst
    if src.startswith("rss:"):
        rid = src[4:]
        return f"{inst} · via RSS ({rid})"
    labels = {"guia_bcn": "Guia BCN", "cidob": "CIDOB"}
    if src in labels:
        return f"{inst} · {labels[src]}"
    return f"{inst} · {src}" if src else inst
