"""
RSS: només volem actes / sessions programades a Barcelona (o àmbit català), no notícies esportives,
cròniques, entrevistes sense cita o peces lifestyle. Això és independent del filtre «intel·lectual».
"""

from __future__ import annotations

import logging
import re
import unicodedata

from models import EventItem

# Fonts de mitjà: cal senyal clar d’agenda (no només titular de premsa).
STRICT_AGENDA_SOURCE_IDS: frozenset[str] = frozenset(
    {
        "beteve",
        "ara_cultura",
        "directa",
        "el_critic",
        "rezero",
    }
)


def _norm(s: str) -> str:
    s = (s or "").lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s).strip()
    return s


# Esport i resultats (fora del producte).
_SPORT_OR_RESULT = (
    "barça",
    " fc ",
    "futbol",
    "fútbol",
    "futbol",
    "rugby",
    "bàsquet",
    "basquet",
    "handbol",
    "divisió d'honor",
    "divisio d'honor",
    "play-off",
    "playoff",
    "primera federació",
    "primera federacio",
    "liga endesa",
    "liga femenina",
    "classificació",
    "empat sense gols",
    "victòria a la final",
    "victoria a la final",
    "gol en els darrers",
    "gol en los últimos",
    "espanyol b",
    "ud poblense",
    "sant andreu",
    "túria",
    "poblense",
)

# Cròniques / tancaments (no són cites futures).
_RECAP_NEWS = (
    "ha guanyat",
    "ha ganado",
    "han tancat",
    "ha tancat",
    "tanca amb",
    "tanca con",
    "ha recollit",
    "ha empatat",
    "ha confirmat",
    "van morir",
    "han mort",
    "fa 26 anys",
    "fa 27 anys",
    "26 anys després",
    "polèmica 26 anys",
    "accident letal",
    "jfk",
    "kennedy jr",
    "carolyn bessette",
)

# Lifestyle / receptes / llibre de cuina sense acte.
_LIFESTYLE = (
    "receptes del",
    "30 anys de receptes",
    "semproniana",
    "faig menú",
    "faig menu",
    "cuinera",
    "restaurant rosselló",
)

# Entrevistes / cinema sense cita (patrons típics de peça, no agenda).
_INTERVIEW_OR_FEATURE = (
    "sento que hi ha una connexió",
    "sento que hi ha una connexion",
    "entrevista exclusiva",
    "reportatge",
    "la història d'amor",
    "història d'amor de",
    "icones d'estil",
    "carla simón",
    "carla simon",
)

# Senyals d'acte: paraules que indiquen un ACTE programat (conferència, debat, taller…).
_EVENT_ACTION = (
    "presentació del llibre",
    "presentacion del libro",
    "presentació pública",
    "conferència",
    "conferencia",
    "debat ",
    " debat",
    "debats",
    "seminari",
    "seminario",
    "col·loqui",
    "coloquio",
    "xerrada",
    "taula rodona",
    "mesa redonda",
    "sessió",
    "sesión",
    "inauguració",
    "inauguracion",
    "estrena ",
    "estreno ",
    "entrades a la venda",
    "entrades esgotades",
    "inscripció",
    "inscripcion",
    "a les ",
    "a las ",
    "jornada ",
    "simposi",
    "simposio",
    "taller ",
)

# Llocs/institucions: un article que ESMENTA un lloc no és necessàriament un ACTE al lloc.
# Per fonts institucionals (no estrictes) reforcen, però per fonts de mitjà no basten sols.
_EVENT_VENUE = (
    "teatre lliure",
    "teatre nacional",
    "auditori",
    "palau de la música",
    "cccb",
    "institut d'humanitats",
    "cidob",
    "ateneu barcelonès",
    "ateneu barcelones",
    "macba",
    "cosmocaixa",
)

_EVENT_STRONG = _EVENT_ACTION + _EVENT_VENUE

_URL_EVENT_HINTS = ("/agenda/", "/event/", "/activitat/", "/actividad/", "/exposicions/", "/exposiciones/")


def _has_strong_event_signal(blob: str) -> bool:
    return any(x in blob for x in _EVENT_STRONG)


def _url_suggests_event(link: str) -> bool:
    u = (link or "").lower()
    return any(h in u for h in _URL_EVENT_HINTS)


def _retrospective_culture_article(blob: str) -> bool:
    """Crònica / record de festival o descoberta passada (no cita futura)."""
    if "el 2011" in blob and ("festival" in blob or "cinema" in blob or "públic" in blob):
        return True
    if "va descobrir" in blob and "públic" in blob:
        return True
    if "primera edició del festival" in blob or "primera edicio del festival" in blob:
        return True
    if "des d'aleshores" in blob and "festival" in blob:
        return True
    if "mia hansen" in blob and "2011" in blob:
        return True
    return False


def _global_exclude(blob: str) -> bool:
    if any(x in blob for x in _SPORT_OR_RESULT):
        return True
    if any(x in blob for x in _RECAP_NEWS):
        return True
    if any(x in blob for x in _LIFESTYLE):
        return True
    if any(x in blob for x in _INTERVIEW_OR_FEATURE):
        return True
    if _retrospective_culture_article(blob):
        return True
    # Dansa / festival ja tancat (crònica d’assistència).
    if "dansa metropolitana" in blob and "tanca" in blob:
        return True
    if "festival" in blob and "espectadors" in blob and "tanca" in blob:
        return True
    # Article històric / patrimoni sense cita d’acte.
    if "pedralbes" in blob and "set segles" in blob:
        return True
    if "monestir de pedralbes" in blob and "històries" in blob:
        return True
    return False


def _strict_agenda_ok(blob: str, link: str) -> bool:
    """Per mitjans: cal senyal d’acte (conferencia, debat…) o URL d’agenda; mencions de llocs no basten."""
    if _url_suggests_event(link):
        return True
    if _retrospective_culture_article(blob):
        return False
    if any(x in blob for x in _EVENT_ACTION):
        return True
    if "pedralbes" in blob and "set segles" in blob:
        return False
    if "monestir de pedralbes" in blob and "històries" in blob:
        return False
    return False


def filter_product_events(events: list[EventItem]) -> list[EventItem]:
    """Segona passada global: treu soroll que hagi pogut escapar (esport, cròniques, etc.)."""
    out: list[EventItem] = []
    dropped = 0
    for e in events:
        blob = _norm(f"{e.title} {e.summary or ''}")
        if _global_exclude(blob):
            dropped += 1
            continue
        out.append(e)
    if dropped:
        logging.getLogger(__name__).info(
            "Filtre producte: %s entrades excloses (esport, crònica, no-agenda)", dropped
        )
    return out


def rss_entry_is_valid_event(
    *,
    source_id: str,
    title: str,
    summary: str,
    link: str,
) -> bool:
    """
    True si l’entrada pot entrar al radar d’«actes» (no només article de mitjà).
    Les fonts STRICT_AGENDA_* tenen el llistó més alt.
    """
    blob = _norm(f"{title} {summary[:1200]}")
    if _global_exclude(blob):
        return False
    if source_id in STRICT_AGENDA_SOURCE_IDS:
        return _strict_agenda_ok(blob, link)
    # Fonts institucionals (IEC, MACBA…): global exclude n’hi ha prou en la majoria dels casos.
    if not _has_strong_event_signal(blob) and not _url_suggests_event(link):
        # Evitem entrevistes genèriques sense senyal d’acte.
        if any(x in blob for x in _INTERVIEW_OR_FEATURE):
            return False
        if "entrevista" in blob and "festival d'a" not in blob:
            return False
    return True
