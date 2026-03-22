"""
Job diari: recull candidats de totes les fonts, valida, dedup, enriqueix
i guarda a data/candidates.json.
"""

from __future__ import annotations

import json
import logging
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import load_settings
from dedupe import dedupe_events
from enrichment import enrich_batch
from models import EventItem
from scrapers.cccb import fetch_cccb_events
from scrapers.cidob import fetch_cidob_events
from scrapers.gencat import fetch_gencat_placeholder
from scrapers.guia_barcelona import fetch_guia_barcelona_csv
from scrapers.iccub import fetch_iccub_events
from scrapers.icfo import fetch_icfo_events
from scrapers.ice_csic import fetch_ice_csic_events
from scrapers.rss_feeds import fetch_rss_feeds
from validation import validate_events

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("ingest")

CANDIDATES_FILE = "candidates.json"


def _run_scrapers(settings) -> tuple[list[EventItem], list[str]]:
    failures: list[str] = []
    events: list[EventItem] = []
    jobs: list[tuple[str, object]] = [
        ("Guia Barcelona", lambda: fetch_guia_barcelona_csv(settings.guia_csv_url)),
        ("Gencat", lambda: fetch_gencat_placeholder()),
        ("CCCB", lambda: fetch_cccb_events(settings.cccb_calendar_url)),
        ("CIDOB", lambda: fetch_cidob_events(settings.cidob_activities_url)),
        ("ICCUB", lambda: fetch_iccub_events()),
        ("ICFO", lambda: fetch_icfo_events()),
        ("ICE-CSIC", lambda: fetch_ice_csic_events()),
    ]
    if settings.rss_enabled:
        jobs.append((
            f"RSS (set={settings.rss_feed_set})",
            lambda: fetch_rss_feeds(
                max_per_feed=settings.rss_max_per_feed,
                feed_set=settings.rss_feed_set,
            ),
        ))

    workers = min(8, len(jobs))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        future_to_name = {ex.submit(fn): name for name, fn in jobs}
        for fut in as_completed(future_to_name):
            name = future_to_name[fut]
            try:
                got = fut.result()
                events.extend(got)
                logger.info("%s: %s esdeveniments", name, len(got))
            except Exception as exc:
                msg = f"{name}: {exc}"
                logger.exception("Scraper falla: %s", name)
                failures.append(msg)

    return events, failures


def _load_existing(path: Path) -> list[EventItem]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text("utf-8"))
        return [EventItem.from_dict(d) for d in data]
    except Exception as exc:
        logger.warning("No s'ha pogut carregar candidates: %s", exc)
        return []


def _save_candidates(path: Path, events: list[EventItem]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [e.to_dict() for e in events]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    logger.info("Guardat %s candidats a %s", len(events), path)


def run_ingest() -> int:
    settings = load_settings()
    candidates_path = settings.data_dir / CANDIDATES_FILE
    existing = _load_existing(candidates_path)
    logger.info("Candidats existents: %s", len(existing))

    raw, failures = _run_scrapers(settings)
    c = Counter((e.source or "?") for e in raw)
    logger.info("Scrapers: %s total — %s",
                len(raw),
                ", ".join(f"{k}={v}" for k, v in sorted(c.items(), key=lambda x: (-x[1], x[0]))))

    validated = validate_events(raw)
    merged = existing + validated
    deduped = dedupe_events(merged)
    logger.info("Després de validació + dedup (amb existents): %s", len(deduped))

    enriched = enrich_batch(deduped, max_workers=4)

    _save_candidates(candidates_path, enriched)

    if failures:
        logger.warning("Fonts amb error: %s", "; ".join(failures))

    return 0


if __name__ == "__main__":
    raise SystemExit(run_ingest())
