from __future__ import annotations

import csv
import io
import logging
import re
from datetime import date, datetime
from typing import Any

import requests

from intellect_filters import (
    classify_area,
    text_matches_intellect_blob,
    venue_tier_boost,
)
from models import EventItem

logger = logging.getLogger(__name__)

DEFAULT_GUIA_CSV = (
    "https://opendata-ajuntament.barcelona.cat/data/dataset/"
    "a25e60cd-3083-4252-9fce-81f733871cb1/resource/"
    "877ccf66-9106-4ae2-be51-95a9f6469e4c/download"
)


def _short_summary(title: str, max_len: int = 130) -> str:
    t = re.sub(r"\s+", " ", title.strip())
    if len(t) <= max_len:
        return t
    cut = t[: max_len - 1].rsplit(" ", 1)[0]
    return cut + "…"


def _parse_start_date(val: str | None) -> str | None:
    if not val or not str(val).strip():
        return None
    s = str(val).strip()
    try:
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).date().isoformat()
        return date.fromisoformat(s[:10]).isoformat()
    except ValueError:
        return None


def _row_key(row: dict[str, Any]) -> str | None:
    rid = row.get("register_id")
    if rid is None or str(rid).strip() == "":
        return None
    digits = re.sub(r"\D", "", str(rid).strip().lstrip("\ufeff"))
    return digits or None


def fetch_guia_barcelona_csv(csv_url: str = DEFAULT_GUIA_CSV) -> list[EventItem]:
    """
    Dades obertes Ajuntament: agenda en CSV (UTF-16), mateixa font que Guia Barcelona.
    Es filtra per paraules clau d’«alta densitat intel·lectual» + finestra temporal (fora d’aquest mòdul).
    """
    logger.info("Guia Barcelona (CSV): baixant %s", csv_url)
    r = requests.get(csv_url, timeout=180, headers={"User-Agent": "intelect-bcn/1.0"})
    r.raise_for_status()
    # CSV oficial: UTF-16 LE amb BOM; el codec «utf-16» detecta el BOM.
    text = r.content.decode("utf-16")
    reader = csv.DictReader(io.StringIO(text))
    events: list[EventItem] = []
    for row in reader:
        name = (row.get("name") or "").strip()
        if not name:
            continue
        filt = " ".join(
            filter(
                None,
                [
                    row.get("secondary_filters_fullpath") or "",
                    row.get("secondary_filters_name") or "",
                ],
            )
        )
        if not text_matches_intellect_blob(name, filt):
            continue
        start = _parse_start_date(row.get("start_date"))
        if not start:
            continue
        rid = _row_key(row)
        if not rid:
            continue
        inst = (row.get("institution_name") or "").strip() or "Barcelona (lloc)"
        url = f"https://guia.barcelona.cat/ca/agenda/{rid}"
        tier = "premium" if venue_tier_boost(inst) else "base"
        area = classify_area(name, inst)
        ev = EventItem(
            institution=inst,
            title=name,
            url=url,
            starts_at=start,
            ends_at=_parse_start_date(row.get("end_date")),
            label="Guia Barcelona",
            raw_date=start,
            tier=tier,
            area=area,
            summary=_short_summary(name),
            source="guia_bcn",
        )
        events.append(ev)
    logger.info("Guia Barcelona (CSV): %s candidats després del filtre intel·lectual", len(events))
    return events
