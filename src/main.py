from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import load_settings
from intellect_filters import filter_noise_events
from dedupe import dedupe_events
from digest import (
    build_digest_html,
    filter_events_in_window,
    format_novelties_html,
)
from models import EventItem, Snapshot
from notifier import TELEGRAM_MAX, chunk_text, merge_for_telegram, send_telegram_messages
from scrapers.cccb import fetch_cccb_events
from scrapers.cidob import fetch_cidob_events
from scrapers.gencat import fetch_gencat_placeholder
from scrapers.guia_barcelona import fetch_guia_barcelona_csv
from scrapers.rss_feeds import fetch_rss_feeds
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
logger = logging.getLogger("intelect_bcn")


def _run_scrapers(settings) -> tuple[list[EventItem], list[str]]:
    failures: list[str] = []
    events: list[EventItem] = []
    jobs: list[tuple[str, object]] = [
        ("Guia Barcelona", lambda: fetch_guia_barcelona_csv(settings.guia_csv_url)),
        ("Gencat", lambda: fetch_gencat_placeholder()),
        ("CCCB", lambda: fetch_cccb_events(settings.cccb_calendar_url)),
        ("CIDOB", lambda: fetch_cidob_events(settings.cidob_activities_url)),
    ]
    if settings.rss_enabled:
        jobs.append(
            (
                "RSS (IEC, SCM, MACBA, Ateneu, Hangar, Mies, Enginyers BCN…)",
                lambda: fetch_rss_feeds(max_per_feed=settings.rss_max_per_feed),
            )
        )
    for name, fn in jobs:
        try:
            got = fn()
            events.extend(got)
            logger.info("%s: %s esdeveniments", name, len(got))
        except Exception as e:
            msg = f"{name}: {e}"
            logger.exception("Scraper falla: %s", name)
            failures.append(msg)
    events = filter_noise_events(events)
    events = dedupe_events(events)
    logger.info("Total després de deduplicar: %s", len(events))
    return events, failures


def main() -> int:
    settings = load_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    prev = load_snapshot(settings.snapshot_path)
    seen = load_seen_keys(settings.seen_keys_path)
    seen = migrate_seen_from_snapshot(seen, prev)
    is_first_seen_registry = len(seen) == 0

    raw_events, failures = _run_scrapers(settings)
    windowed = filter_events_in_window(
        raw_events,
        tz_name=settings.timezone,
        window_days=settings.window_days,
    )

    fetched_at = datetime.now(timezone.utc).isoformat()
    current = Snapshot(fetched_at=fetched_at, events=windowed)

    is_first_snapshot = prev is None

    body = build_digest_html(
        windowed,
        tz_name=settings.timezone,
        window_days=settings.window_days,
        max_per_institution=settings.max_events_per_institution,
        max_base_events=settings.max_base_events,
        failures=failures,
    )
    _max = TELEGRAM_MAX - 150
    sections = merge_for_telegram(chunk_text(body, _max))

    if settings.append_novelties and not is_first_seen_registry:
        new_e = compute_novelties(windowed, seen)
        if new_e:
            nov = format_novelties_html(new_e)
            sections.extend(merge_for_telegram(chunk_text(nov, _max)))
            logger.info("Novetats (claus noves): %s", len(new_e))

    if is_first_snapshot:
        sections.extend(
            merge_for_telegram(
                [
                    "<i>Primera execució: s’ha creat el snapshot i el registre de novetats. "
                    "A partir d’ara, cada cop es compararà amb el que ja hem vist.</i>"
                ]
            )
        )

    log_text = "\n\n--- missatge següent ---\n\n".join(sections)
    save_snapshot(settings.snapshot_path, current)

    seen = register_current_window(windowed, seen)
    seen = prune_seen_keys(seen, max_age_days=settings.seen_prune_days)
    save_seen_keys(settings.seen_keys_path, seen)

    if settings.skip_telegram or settings.dry_run or not settings.telegram_bot_token:
        logger.info("Telegram desactivat o sense token. Text generat:\n%s", log_text)
        if not settings.skip_telegram and not settings.dry_run:
            logger.warning("Define TELEGRAM_BOT_TOKEN i TELEGRAM_CHAT_ID per enviar avisos.")
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
    except Exception as e:
        logger.exception("No s’ha pogut enviar a Telegram: %s", e)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
