from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from digest import build_digest_html  # noqa: E402
from models import EventItem  # noqa: E402


def test_digest_multiday_events():
    evs = [
        EventItem(
            institution="CCCB",
            title="Utopies, distopies i imaginació política",
            url="https://www.cccb.org/a",
            starts_at="2026-03-25",
            tier="premium",
            area="Política i món",
            summary="Debats",
            source="cccb",
        ),
        EventItem(
            institution="CCCB",
            title="Utopies, distopies i imaginació política",
            url="https://www.cccb.org/b",
            starts_at="2026-03-26",
            tier="premium",
            area="Política i món",
            summary="Debats",
            source="cccb",
        ),
    ]
    out = build_digest_html(
        evs,
        tz_name="Europe/Madrid",
        window_days=14,
        max_per_institution=20,
        max_base_events=50,
        failures=[],
    )
    assert "Utopies" in out
    assert "Destacats" in out
    assert "CCCB" in out


def test_digest_no_internal_telemetry():
    evs = [
        EventItem(
            institution="CCCB",
            title=f"Debat urgent {i}",
            url=f"https://cccb.org/{i}",
            starts_at="2026-03-25",
            tier="premium",
            source="cccb",
            event_kind="debat",
            confidence="high",
        )
        for i in range(4)
    ]
    out = build_digest_html(
        evs,
        tz_name="Europe/Madrid",
        window_days=14,
        max_per_institution=20,
        max_base_events=50,
        failures=[],
        scraper_counts_merged={"cccb": 40},
    )
    assert "Pipeline" not in out
    assert "RSS mitjà" not in out
    assert "via RSS" not in out
    assert "scraper" not in out.lower()
    assert "Destacats" in out


def test_digest_editorial_phrase_in_highlights():
    evs = [
        EventItem(
            institution="CCCB",
            title="Debat sobre democràcia i futur",
            url="https://cccb.org/debat",
            starts_at="2026-03-25",
            tier="premium",
            source="cccb",
            event_kind="debat",
            confidence="high",
        ),
    ]
    out = build_digest_html(
        evs,
        tz_name="Europe/Madrid",
        window_days=14,
        max_per_institution=5,
        max_base_events=50,
        failures=[],
    )
    assert "Debat" in out
    assert "CCCB" in out
    assert "<i>" in out
