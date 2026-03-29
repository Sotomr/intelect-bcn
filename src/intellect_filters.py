from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from models import EventItem

_RE_D_A = re.compile(r"d['\u2019']a", re.IGNORECASE)

# Termes que per si sols indiquen densitat intel·lectual alta
_STRONG_TERMS: tuple[str, ...] = (
    "conferència",
    "conferencia",
    "debat",
    "xerrada",
    "seminari",
    "seminario",
    "col·loqui",
    "coloquio",
    "tertúlia",
    "tertulia",
    "simposi",
    "simposio",
    "jornad",
    "congrés",
    "congres",
)

# Termes temàtics: el contingut és intel·lectual independentment del format
_TOPIC_TERMS: tuple[str, ...] = (
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
    "literatura",
    "llibre",
    "assaig",
    "ensayo",
    "investigació",
    "investigacion",
    "documental",
    "història",
    "historia",
    "sociologia",
    "antropolog",
    "economia",
    "urbanisme",
    "arquitectur",
    "ecologia",
    "sostenibilitat",
    "drets humans",
    "derechos humanos",
)

# Termes que NOMÉS compten si van acompanyats d'un terme temàtic
_WEAK_TERMS: tuple[str, ...] = (
    "taller",
    "curs ",
    " curs",
    "presentació",
    "presentacion",
    "exposició",
    "exposicion",
    "projecció",
    "proyeccion",
    "festival",
    "convers",
    # Sols rellevant amb terme temàtic o format fort (evita taules rodones «genèriques» sense densitat)
    "taula rodona",
    "mesa rodona",
    "mesa redonda",
)

INCLUDE_TERMS: tuple[str, ...] = _STRONG_TERMS + _TOPIC_TERMS + _WEAK_TERMS

# Excloure soroll evident (encara que coincideixi amb INCLUDE)
EXCLUDE_TERMS: tuple[str, ...] = (
    # Públic infantil / familiar
    "infantil",
    "familiar",
    "en família",
    "en familia",
    "nadó",
    "nado",
    "kids",
    "nens i nenes",
    "nens ",
    " nens",
    "nenes ",
    "per a petits",
    "per als petits",
    "peques",
    "primària",
    "primaria",
    "secundària",
    "secundaria",
    " eso ",
    "3r a 6è",
    "1r a 3r",
    "4t a 6è",
    "p3",
    "p4",
    "p5",
    "contacontes",
    "conta contes",
    "titella",
    "titelles",
    "animació infantil",
    # Activitats de vacances / festes populars
    "casalet",
    "casal d'estiu",
    "casal de nadal",
    "pasqua",
    "setmana santa",
    "festa major",
    "carnaval",
    "cavalcada",
    "revetlla",
    "castellers",
    "gegants ",
    "diables",
    "correfoc",
    # Esport / cos / dansa
    "activitat esportiva",
    "zumba",
    "gimnàstica",
    "gimnastica",
    "ioga",
    "yoga",
    "pilates",
    "dansa",
    "danza",
    "ballet",
    "hip hop",
    "hip-hop",
    "swing",
    "salsa",
    "bachata",
    "shuffle",
    "breakdance",
    "coreograf",
    # Música / concerts / espectacles
    "concert",
    "orquestra",
    "simfònic",
    "simfonic",
    "coral ",
    "karaoke",
    "dj session",
    "circ",
    "màgia",
    "magia",
    "espectacle",
    "show ",
    "stand-up",
    # Manualitats / tallers genèrics
    "manualitats",
    "creatiu",
    "flipbook",
    "bestiari",
    "bestioles",
    "bèsties",
    "besties",
    "piu, piu",
    "fabricació col·lectiva",
    "fabricacio col·lectiva",
    "papiroflèxia",
    "papiroflexia",
    "ganxet",
    "punt de creu",
    "scrapbook",
    # Concursos / competicions no intel·lectuals
    "concurs de cartells",
    "concurs de disfresses",
    "masterclass de ball",
    # Altres soroll
    "criança autogestionat",
    "grup de criança",
    "nous vins",
    "cal bardera",
    "mercat",
    "fira ",
    " fira",
    "botiga",
    "showcooking",
    "tast de vins",
    "tast de cervesa",
    "escape room",
    "paintball",
    "laser tag",
    "intercanvi de llibres",
    "recollida de llibres",
    "bookcrossing",
    "gent gran",
    # Cultura lleugera que s'amaga darrere formats «seriosos»
    "fanzín",
    "fanzin",
    " fanzine",
    "barswing",
    "barswingona",
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
    if any(_norm(x) in blob for x in _STRONG_TERMS):
        return True
    if any(_norm(x) in blob for x in _TOPIC_TERMS):
        return True
    if any(_norm(x) in blob for x in _WEAK_TERMS):
        has_topic = any(_norm(x) in blob for x in _TOPIC_TERMS)
        has_strong = any(_norm(x) in blob for x in _STRONG_TERMS)
        return has_topic or has_strong
    return False


_NOISE_COMBOS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("taller", ("animals", "natura", "pasqua", "nadal", "estiu", "primavera",
                "manualitat", "creatiu", "dibuix", "pintura", "collage",
                "reciclat", "flor", "planta", "insecte", "ocell",
                "cos col·lectiu", "cos collectiu",
                "mobles", "moble ", "maqueta", "maquetes", "diorama")),
    ("festival", ("cinema", "swing", "dansa", "danza", "ball", "música",
                  "musica", "rock", "jazz", "reggae", "electrònica",
                  "electronica", "gastro", "cervesa")),
    ("concurs", ("cartell", "disfress", "fotografi")),
)


def is_noise_title_intellect(title: str) -> bool:
    """
    Detecció de soroll que passa els filtres inicials.
    Inclou patrons combinats (taller + animal = soroll) i patrons directes.
    """
    if not title or not str(title).strip():
        return False
    t = _norm(str(title))
    if "festival de cinema de barcelona" in t:
        return True
    if "festival" in t and "cinema" in t and _RE_D_A.search(title):
        return True
    if any(x in t for x in ("taula rodona", "mesa rodona", "mesa redonda")):
        if any(
            x in t
            for x in (
                "fanz",
                "zine",
                "flipbook",
                "shuffle showcase",
                "bestiari",
                "barswing",
                "oh! i trans",
                "casalet",
                "setmana santa",
                "festa major",
                "primaria",
                "masterclass de ball",
            )
        ):
            return True
    for trigger, noise_words in _NOISE_COMBOS:
        if trigger in t:
            if any(nw in t for nw in noise_words):
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
            "Filtre soroll títol: %s esdeveniments exclos (patrons combinats / soroll editorial)",
            dropped,
        )
    return out


def venue_tier_boost(institution_name: str) -> bool:
    n = _norm(institution_name or "")
    return any(h in n for h in PREMIUM_VENUE_HINTS)


def classify_area(title: str, institution: str, label: str = "") -> str:
    """Taxonomia expressiva; implementació a `editorial`."""
    from editorial import classify_area as _classify

    return _classify(title, institution, label)
