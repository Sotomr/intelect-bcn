from __future__ import annotations

import re
import unicodedata
from typing import Iterable

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


def venue_tier_boost(institution_name: str) -> bool:
    n = _norm(institution_name or "")
    return any(h in n for h in PREMIUM_VENUE_HINTS)


def classify_area(title: str, institution: str, label: str = "") -> str:
    blob = _norm(f"{title} {institution} {label}")
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
        )
    ):
        return "Política i geopolítica"
    if any(
        x in blob
        for x in (
            "filosofia",
            "filosofía",
            "pensament",
            "humanitats",
            "ètica",
            "etica",
        )
    ):
        return "Filosofia i humanitats"
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
        )
    ):
        return "Ciència i tecnologia"
    if any(x in blob for x in ("art", "macba", "miró", "miro", "exposició", "exposicion")):
        return "Art i cultura visual"
    if any(x in blob for x in ("literatura", "llibre", "presentació", "poèt", "narrativ")):
        return "Literatura i idees"
    return "General (idees)"
