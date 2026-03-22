from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    data_dir: Path
    snapshot_path: Path
    skip_telegram: bool
    dry_run: bool
    timezone: str
    append_novelties: bool
    window_days: int
    max_events_per_institution: int
    max_base_events: int
    guia_csv_url: str
    cccb_calendar_url: str
    cidob_activities_url: str
    seen_keys_path: Path
    seen_prune_days: int
    rss_enabled: bool
    rss_max_per_feed: int
    rss_feed_set: str
    digest_highlight_count: int
    digest_max_per_source_highlights: int


def _rss_feed_set() -> str:
    """RSS_FEED_SET: all | institutional | media (per defecte només fonts d’agenda institucional)."""
    raw = (os.getenv("RSS_FEED_SET") or "institutional").strip().lower()
    aliases = {
        "tot": "all",
        "*": "all",
        "institucional": "institutional",
        "agenda": "institutional",
    }
    v = aliases.get(raw, raw)
    if v in ("all", "institutional", "media"):
        return v
    return "institutional"


def _int_env(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or str(v).strip() == "":
        return default
    try:
        return int(v)
    except ValueError:
        return default


def load_settings() -> Settings:
    root = _ROOT
    data_dir = root / "data"
    token = os.getenv("TELEGRAM_BOT_TOKEN") or None
    chat_id = os.getenv("TELEGRAM_CHAT_ID") or None
    skip = os.getenv("SKIP_TELEGRAM", "").lower() in ("1", "true", "yes")
    dry = os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes")
    tz = os.getenv("TIMEZONE", "Europe/Madrid").strip() or "Europe/Madrid"
    append_n = os.getenv("APPEND_NOVELTIES", "1").lower() not in ("0", "false", "no")

    return Settings(
        telegram_bot_token=token,
        telegram_chat_id=chat_id,
        data_dir=data_dir,
        snapshot_path=data_dir / "latest_snapshot.json",
        skip_telegram=skip,
        dry_run=dry,
        timezone=tz,
        append_novelties=append_n,
        window_days=max(1, _int_env("WINDOW_DAYS", 7)),
        max_events_per_institution=max(1, _int_env("MAX_EVENTS_PER_INSTITUTION", 12)),
        max_base_events=max(0, _int_env("MAX_BASE_EVENTS", 32)),
        guia_csv_url=os.getenv(
            "GUIA_CSV_URL",
            "https://opendata-ajuntament.barcelona.cat/data/dataset/"
            "a25e60cd-3083-4252-9fce-81f733871cb1/resource/"
            "877ccf66-9106-4ae2-be51-95a9f6469e4c/download",
        ).strip(),
        cccb_calendar_url=os.getenv(
            "CCCB_CALENDAR_URL",
            "https://www.cccb.org/ca/calendari",
        ).strip(),
        cidob_activities_url=os.getenv(
            "CIDOB_ACTIVITIES_URL",
            "https://www.cidob.org/actividades",
        ).strip(),
        seen_keys_path=data_dir / "seen_event_keys.json",
        seen_prune_days=max(0, _int_env("SEEN_PRUNE_DAYS", 120)),
        rss_enabled=os.getenv("RSS_ENABLED", "1").lower() not in ("0", "false", "no"),
        rss_max_per_feed=max(1, _int_env("RSS_MAX_PER_FEED", 25)),
        rss_feed_set=_rss_feed_set(),
        digest_highlight_count=max(3, min(12, _int_env("DIGEST_HIGHLIGHT_COUNT", 5))),
        digest_max_per_source_highlights=max(1, min(6, _int_env("DIGEST_MAX_PER_SOURCE", 3))),
    )
