"""
Validació dura: decideix si una peça és un acte al qual pots anar.
Unifica filter_noise_events, filter_product_events i rss_entry_is_valid_event.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Iterable

from models import EventItem

logger = logging.getLogger(__name__)


def _norm(s: str) -> str:
    s = (s or "").lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip()


# ---- Patrons d'exclusió (acumulats de rss_event_filter + intellect_filters) ----

_SPORT = (
    "barça", " fc ", "futbol", "fútbol", "rugby", "bàsquet", "basquet",
    "handbol", "divisió d'honor", "play-off", "playoff", "liga endesa",
    "liga femenina", "classificació", "empat sense gols", "victòria a la final",
    "gol en els darrers", "espanyol b", "ud poblense", "poblense",
)

_RECAP = (
    "ha guanyat", "ha ganado", "han tancat", "ha tancat", "tanca amb",
    "ha recollit", "ha empatat", "ha confirmat", "van morir", "han mort",
)

_LIFESTYLE = (
    "receptes del", "30 anys de receptes", "semproniana", "faig menú",
    "cuinera", "restaurant rosselló",
)

_INTERVIEW = (
    "entrevista exclusiva", "reportatge", "icones d'estil",
    "carla simón", "carla simon",
)

_INSTITUTIONAL_NOISE = (
    "resolució de la convocatòria", "resolucio de la convocatoria",
    "resolució convocatòria", "resolucio convocatoria",
    "presentació de candidatures", "presentar candidatures",
    "candidatures a les comissions",
    "el degà assisteix", "el dega assisteix",
    "el degà d'enginyers", "el dega d'enginyers",
    "acte de reconeixement", "nota corporativa",
    "procés electoral", "proces electoral",
    "jurat estable", "comitè de selecció", "comite de seleccio",
    "the post ",
)

_CINEMA_NOISE_RE = re.compile(r"festival.*cinema|cinema.*festival", re.IGNORECASE)
_RE_D_A = re.compile(r"d['\u2019']a", re.IGNORECASE)

_NON_EVENT_KINDS = frozenset({"article"})


def _is_noise(blob: str, title: str = "") -> bool:
    if any(_norm(x) in blob for x in _SPORT):
        return True
    if any(_norm(x) in blob for x in _RECAP):
        return True
    if any(_norm(x) in blob for x in _LIFESTYLE):
        return True
    if any(_norm(x) in blob for x in _INTERVIEW):
        return True
    if any(_norm(x) in blob for x in _INSTITUTIONAL_NOISE):
        return True
    if "dansa metropolitana" in blob and "tanca" in blob:
        return True
    if "festival" in blob and "espectadors" in blob and "tanca" in blob:
        return True
    if "pedralbes" in blob and "set segles" in blob:
        return True
    t = (title or "").lower()
    if "festival de cinema de barcelona" in t:
        return True
    if "festival" in t and "cinema" in t and _RE_D_A.search(title):
        return True
    return False


def validate_candidate(e: EventItem) -> EventItem | None:
    """
    Porta d'entrada única: retorna l'event (potencialment amb confidence ajustada)
    si és un acte vàlid, o None si s'ha de descartar.

    Pregunta central: "és un acte públic real al qual pots anar?"
    """
    # 1. Data: sense data no entra a cap agenda
    if not e.starts_at:
        return None

    blob = _norm(f"{e.title} {e.summary or ''}")

    # 2. Soroll global (esport, cròniques, lifestyle, institucional)
    if _is_noise(blob, e.title):
        return None

    # 3. Tipus incompatible
    if e.event_kind in _NON_EVENT_KINDS:
        return None

    # 4. Confidence: ajustar si event_kind és visita/servei
    if e.event_kind == "visita":
        if e.confidence == "high":
            e.confidence = "medium"

    return e


def validate_events(events: Iterable[EventItem]) -> list[EventItem]:
    """Aplica validate_candidate a una llista, amb logging."""
    out: list[EventItem] = []
    dropped = 0
    for e in events:
        result = validate_candidate(e)
        if result is not None:
            out.append(result)
        else:
            dropped += 1
    if dropped:
        logger.info("Validació: %s candidates descartades", dropped)
    return out
