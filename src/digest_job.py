"""
Job setmanal: carrega candidats, filtra finestra temporal, aplica selector,
genera digest, gestiona seen store i envia a Telegram.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import load_settings
from digest import build_digest_html, filter_events_in_window, format_novelties_html
from models import EventItem, Snapshot
from notifier import TELEGRAM_MAX, chunk_text, merge_for_telegram, send_telegram_messages
from seen_store import (
    compute_novelties,
    load_seen_keys,
    migrate_seen_from_snapshot,
    prune_seen_keys,
    register_current_window,
    save_seen_keys,
)
from storage import load_snapshot, save_snapshot

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("digest_job")

CANDIDATES_FILE = "candidates.json"


def _load_candidates(path: Path) -> list[EventItem]:
    if not path.exists():
        logger.warning("No hi ha fitxer de candidats: %s", path)
        return []
    try:
        data = json.loads(path.read_text("utf-8"))
        return [EventItem.from_dict(d) for d in data]
    except Exception as exc:
        logger.error("Error carregant candidats: %s", exc)
        return []


def run_digest() -> int:
    settings = load_settings()
    candidates_path = settings.data_dir / CANDIDATES_FILE

    candidates = _load_candidates(candidates_path)
    logger.info("Candidats carregats: %s", len(candidates))

    windowed = filter_events_in_window(
        candidates,
        tz_name=settings.timezone,
        window_days=settings.window_days,
    )
    logger.info("Candidats dins la finestra: %s", len(windowed))

    prev = load_snapshot(settings.snapshot_path)
    seen = load_seen_keys(settings.seen_keys_path)
    seen = migrate_seen_from_snapshot(seen, prev)
    is_first_seen_registry = len(seen) == 0

    fetched_at = datetime.now(timezone.utc).isoformat()
    current = Snapshot(fetched_at=fetched_at, events=windowed)

    body = build_digest_html(
        windowed,
        tz_name=settings.timezone,
        window_days=settings.window_days,
        failures=[],
        highlight_count=settings.digest_highlight_count,
        max_per_source_highlights=settings.digest_max_per_source_highlights,
    )
    _max = TELEGRAM_MAX - 150
    sections = merge_for_telegram(chunk_text(body, _max))

    if settings.append_novelties and not is_first_seen_registry:
        new_e = compute_novelties(windowed, seen)
        if new_e:
            nov = format_novelties_html(new_e)
            sections.extend(merge_for_telegram(chunk_text(nov, _max)))
            logger.info("Novetats: %s", len(new_e))

    save_snapshot(settings.snapshot_path, current)
    seen = register_current_window(windowed, seen)
    seen = prune_seen_keys(seen, max_age_days=settings.seen_prune_days)
    save_seen_keys(settings.seen_keys_path, seen)

    log_text = "\n\n--- missatge següent ---\n\n".join(sections)

    if settings.skip_telegram or settings.dry_run or not settings.telegram_bot_token:
        logger.info("Telegram desactivat. Text generat:\n%s", log_text)
        return 0

    if not settings.telegram_chat_id:
        logger.error("Falta TELEGRAM_CHAT_ID")
        return 1

    try:
        send_telegram_messages(
            settings.telegram_bot_token,
            settings.telegram_chat_id,
            sections,
        )
    except Exception as exc:
        logger.exception("No s'ha pogut enviar a Telegram: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(run_digest())
