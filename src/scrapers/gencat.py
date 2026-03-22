from __future__ import annotations

import logging

from models import EventItem

logger = logging.getLogger(__name__)


def fetch_gencat_placeholder() -> list[EventItem]:
    """
    Agenda Cultural de la Generalitat (agenda.cultura.gencat.cat).
    El portal és AEM + front dinàmic; cal un connector estable (API interna, GraphQL o export).
    Es deixa preparat per afegir-hi cerca per data sense dependre d’un scraper fràgil de HTML.
    """
    logger.info(
        "Gencat: pendent d’integració (recomanat: API o dataset estable; veure README)."
    )
    return []
