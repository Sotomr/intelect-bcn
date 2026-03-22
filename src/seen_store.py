from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from models import EventItem, Snapshot

logger = logging.getLogger(__name__)


def load_seen_keys(path: Path) -> dict[str, str]:
    """
    Mapa stable_key -> ISO quan es va veure per primer cop.
    Serveix per dir «aquesta sessió és nova» encara que canviï la finestra de 7 dies.
    """
    if not path.is_file():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
        data: dict[str, Any] = json.loads(raw)
        return dict(data.get("keys") or {})
    except (json.JSONDecodeError, OSError, TypeError, ValueError) as e:
        logger.warning("Registre de novetats invàlid (%s): es reinicia", e)
        return {}


def save_seen_keys(path: Path, keys: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = {
        "keys": keys,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    logger.info("Registre de novetats desat (%s claus)", len(keys))


def prune_seen_keys(keys: dict[str, str], *, max_age_days: int) -> dict[str, str]:
    if max_age_days <= 0:
        return keys
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    out: dict[str, str] = {}
    for k, ts in keys.items():
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt >= cutoff:
                out[k] = ts
        except ValueError:
            continue
    if len(out) < len(keys):
        logger.info(
            "Registre de novetats: eliminades %s claus antigues (> %s dies)",
            len(keys) - len(out),
            max_age_days,
        )
    return out


def migrate_seen_from_snapshot(seen: dict[str, str], snap: Snapshot | None) -> dict[str, str]:
    """Si afegim aquest fitxer a un repo que ja tenia snapshot, no inundem de «novetats»."""
    if seen or not snap:
        return seen
    out = {e.stable_key(): snap.fetched_at for e in snap.events}
    logger.info(
        "Registre de novetats inicialitzat des del snapshot anterior (%s claus)",
        len(out),
    )
    return out


def compute_novelties(windowed: list[EventItem], seen: dict[str, str]) -> list[EventItem]:
    return [e for e in windowed if e.stable_key() not in seen]


def register_current_window(windowed: list[EventItem], seen: dict[str, str]) -> dict[str, str]:
    now = datetime.now(timezone.utc).isoformat()
    merged = dict(seen)
    for e in windowed:
        sk = e.stable_key()
        if sk not in merged:
            merged[sk] = now
    return merged
