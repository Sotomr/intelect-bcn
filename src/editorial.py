"""
Capa editorial: taxonomia temàtica i presentació.

Scoring unificat viu a selector.py (score_event).
"""

from __future__ import annotations

import re
import unicodedata

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


_SOURCE_DISPLAY_NAMES: dict[str, str] = {
    "guia_bcn": "Guia Barcelona",
    "cccb": "CCCB",
    "cidob": "CIDOB",
    "iccub": "ICCUB",
    "icfo": "ICFO",
    "ice_csic": "ICE-CSIC",
    "gencat": "Gencat",
}


def display_source_line(e: EventItem) -> str:
    """Una sola línia de context: nom de la institució (sense costures internes)."""
    inst = (e.institution or "").strip()
    if inst:
        return inst
    src = (e.source or "").strip()
    return _SOURCE_DISPLAY_NAMES.get(src, src)
