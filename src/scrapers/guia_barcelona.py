from __future__ import annotations

import csv
import io
import logging
import re
import time
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

_HEADERS = {
    "User-Agent": "intelect-bcn/1.0 (+https://github.com/Sotomr/intelect-bcn)",
    "Accept": "text/csv,*/*",
}


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


def _normalize_csv_keys(row: dict[str, Any]) -> dict[str, Any]:
    """El CSV UTF-16 de l’Ajuntament pot deixar \\ufeff al primer nom de columna; DictReader llavors no troba «name»."""
    return {((k or "").lstrip("\ufeff")): v for k, v in row.items()}


def _row_key(row: dict[str, Any]) -> str | None:
    rid = row.get("register_id")
    if rid is None or str(rid).strip() == "":
        return None
    digits = re.sub(r"\D", "", str(rid).strip().lstrip("\ufeff"))
    return digits or None


def _decode_utf16_csv(raw: bytes) -> str:
    """CSV oficial ve en UTF-16 LE amb BOM; bytes truncats o corruptes trencaven el decoder estricte."""
    if len(raw) < 4:
        raise ValueError("resposta massa curta per ser un CSV UTF-16")
    # Ordre explícit: BOM FF FE = little-endian
    if raw[:2] == b"\xff\xfe":
        codec = "utf-16-le"
    elif raw[:2] == b"\xfe\xff":
        codec = "utf-16-be"
    else:
        codec = "utf-16"
    try:
        text = raw.decode(codec)
    except UnicodeDecodeError:
        logger.warning(
            "Guia CSV: UTF-16 amb seqüència invàlida; es decodifica amb reemplaçament (alguns caràcters poden perdre’s)"
        )
        text = raw.decode(codec, errors="replace")
    if text and text[0] == "\ufeff":
        text = text[1:]
    return text


def _download_csv_bytes(url: str, *, max_attempts: int = 4) -> bytes:
    """Baixa el cos sencer; reintenta si Content-Length no coincideix (xarxa truncada)."""
    last_err: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            r = requests.get(
                url,
                timeout=300,
                headers=_HEADERS,
                stream=True,
            )
            r.raise_for_status()
            chunks: list[bytes] = []
            for block in r.iter_content(chunk_size=262_144):
                if block:
                    chunks.append(block)
            data = b"".join(chunks)
            cl = r.headers.get("Content-Length")
            if cl and cl.isdigit():
                expected = int(cl)
                if len(data) != expected:
                    logger.warning(
                        "Guia CSV: mida %s != Content-Length %s (intent %s/%s)",
                        len(data),
                        expected,
                        attempt,
                        max_attempts,
                    )
                    if attempt < max_attempts:
                        time.sleep(2 * attempt)
                        continue
            if len(data) < 10_000:
                logger.warning(
                    "Guia CSV: fitxer sospitosament petit (%s bytes)",
                    len(data),
                )
            return data
        except (requests.RequestException, OSError) as e:
            last_err = e
            logger.warning("Guia CSV: intent %s/%s falla: %s", attempt, max_attempts, e)
            if attempt < max_attempts:
                time.sleep(2 * attempt)
    assert last_err is not None
    raise last_err


def fetch_guia_barcelona_csv(csv_url: str = DEFAULT_GUIA_CSV) -> list[EventItem]:
    """
    Dades obertes Ajuntament: agenda en CSV (UTF-16), mateixa font que Guia Barcelona.
    Es filtra per paraules clau d’«alta densitat intel·lectual» + finestra temporal (fora d’aquest mòdul).
    """
    logger.info("Guia Barcelona (CSV): baixant %s", csv_url)
    last_decode_err: BaseException | None = None
    text: str | None = None
    for round_i in range(1, 3):
        try:
            raw = _download_csv_bytes(csv_url)
            text = _decode_utf16_csv(raw)
            last_decode_err = None
            break
        except (UnicodeDecodeError, ValueError) as e:
            last_decode_err = e
            logger.warning("Guia CSV: intent de lectura %s/2 falla: %s", round_i, e)
            if round_i < 2:
                time.sleep(4)
    if text is None:
        assert last_decode_err is not None
        logger.error("Guia CSV: no s’ha pogut llegir el CSV després de reintents")
        raise RuntimeError(
            "CSV de la Guia incomplet o corrupte (descàrrega truncada?). Torna a executar."
        ) from last_decode_err

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames:
        reader.fieldnames = [((fn or "").lstrip("\ufeff")) for fn in reader.fieldnames]
    events: list[EventItem] = []
    for raw in reader:
        row = _normalize_csv_keys(raw)
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
    if len(events) == 0:
        logger.warning(
            "Guia Barcelona (CSV): 0 candidats (filtre intel·lectual, dates o claus CSV; revisa logs si esperaves dades)"
        )
    return events
