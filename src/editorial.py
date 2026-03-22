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


AREA_SECTION_ORDER: tuple[str, ...] = (
    "Filosofia i pensament",
    "Política i món",
    "Ciència i cosmos",
    "Tecnologia i computació",
    "Art i cultura crítica",
    "Literatura i idees",
    "Ciutat i cultura visual",
    "Agenda ampliada",
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
    if any(x in blob for x in ("simfonies de ciutat", "simfonies", "estrena de «", "urbanisme", "arquitectur")):
        return "Ciutat i cultura visual"
    if any(x in blob for x in ("ceguesa", "baixa visio", "visita", "mirador", "portes obertes")):
        return "Agenda ampliada"
    return "Ciutat i cultura visual"


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
    if "simfonies" in t or ("estrena" in t and ("audiovisual" in t or "ciutat" in t)):
        return "Projecció audiovisual"
    if "projecció" in t or "documental" in t or "audiovisual" in t:
        return "Audiovisual"
    if "exposició" in t or "exposicion" in t:
        return "Exposició"
    if "connexió" in t and "cinema" in t:
        return "Conversa / peça de mitjà"
    if (e.source or "").startswith("rss:") and "entrevista" in t:
        return "Conversa / peça de mitjà"
    return "Sessió o programa"


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
        "Projecció audiovisual": 5.0,
        "Exposició": 4.0,
        "Audiovisual": 3.0,
        "Conversa / peça de mitjà": -22.0,
        "Visita guiada": -6.0,
        "Visita": -14.0,
        "Sessió o programa": 1.0,
    }
    s += fmt_bonus.get(fmt, 0.0)
    tb = _norm(e.title)
    if "infant" in tb or "familiar" in tb:
        s -= 28.0
    if "mirador" in tb:
        s -= 12.0
    if "accessible" in tb and "exposici" in tb:
        s -= 18.0
    if "ceguesa" in tb or "baixa visió" in tb:
        s -= 14.0
    if "portes obertes" in tb:
        s -= 8.0
    src = (e.source or "")
    if src in ("cidob", "guia_bcn"):
        s += 5.0
    if src.startswith("rss:") and "iec" in _norm(e.institution):
        s += 4.0
    if "cidob" in _norm(e.institution):
        s += 6.0
    if "iec" in _norm(e.institution) or "scm" in _norm(e.institution):
        s += 4.0
    return s


def _clip_text(text: str, max_len: int = 280) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    cut = text[: max_len - 1].rsplit(" ", 1)[0]
    return cut + "…"


def _summary_adds_value(summ: str, title: str) -> bool:
    if not summ or len(summ) < 48:
        return False
    if _norm(summ[: min(110, len(summ))]) == _norm((title or "")[: min(110, len(title or ""))]):
        return False
    return True


def editorial_blurb(e: EventItem) -> str:
    """
    Sense plantilles amb noms propis: prioritza el text que ve de la font (resum),
    si no, munta una sola franja amb etiqueta + format + títol (tot dinàmic).
    """
    summ = (e.summary or "").strip()
    title = (e.title or "").strip()
    lab = (e.label or "").strip()
    if _summary_adds_value(summ, title):
        return _clip_text(summ, 280)
    fmt = detect_format_label(e)
    chunks: list[str] = []
    if lab and _norm(lab) not in _norm(title):
        chunks.append(lab)
    if fmt and fmt != "Sessió o programa":
        chunks.append(fmt)
    if title:
        if chunks:
            chunks.append(title)
        else:
            return _clip_text(title, 280)
    return _clip_text(" · ".join(c for c in chunks if c), 280)


def pick_highlights(
    events: Iterable[EventItem],
    *,
    k: int = 7,
    max_per_source: int = 3,
) -> tuple[list[EventItem], list[EventItem]]:
    """
    Qualitat primer: el pool de candidats a destacat és el que cau a prop del millor
    de la setmana. Diversitat de fonts dins el pool (max_per_source), però mai
    es baixa el llistó per omplir places amb fonts febles.
    """
    all_events = list(events)
    evs = [e for e in all_events if detect_format_label(e) != "Conversa / peça de mitjà"]
    if not evs:
        return [], all_events
    scored_pairs = sorted(
        ((e, editorial_score(e)) for e in evs),
        key=lambda x: (-x[1], x[0].starts_at or "", x[0].title),
    )
    top_score = scored_pairs[0][1]
    floor = max(42.0, top_score - 16.0)
    pool = [e for e, s in scored_pairs if s >= floor]
    if len(pool) < min(k, len(evs)):
        floor = max(36.0, top_score - 24.0)
        pool = [e for e, s in scored_pairs if s >= floor]

    picked: list[EventItem] = []
    counts: dict[str, int] = defaultdict(int)
    picked_titles: set[str] = set()
    for e in pool:
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
    if len(picked) < k:
        floor2 = max(34.0, top_score - 30.0)
        for e, s in scored_pairs:
            if len(picked) >= k:
                break
            if s < floor2:
                continue
            tk = _title_key(e.title)
            if tk in picked_titles:
                continue
            b = source_bucket(e)
            if counts[b] >= max_per_source:
                continue
            picked.append(e)
            picked_titles.add(tk)
            counts[b] += 1
    keys = {e.stable_key() for e in picked}
    rest = [e for e in all_events if e.stable_key() not in keys]
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
        tb = _norm(e.title)
        if fmt == "Conversa / peça de mitjà":
            low.append(e)
            continue
        if "ceguesa" in tb or "baixa visió" in tb or "baixa vision" in tb:
            low.append(e)
            continue
        if fmt in ("Visita", "Visita guiada"):
            low.append(e)
        elif sc < score_threshold:
            low.append(e)
        else:
            main.append(e)
    return main, low


def display_source_line(e: EventItem) -> str:
    """Una sola línia de context: nom de la institució (sense costures internes)."""
    inst = (e.institution or "").strip()
    return inst or (e.source or "").strip()
