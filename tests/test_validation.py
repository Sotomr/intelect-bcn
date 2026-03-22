from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from models import EventItem  # noqa: E402
from validation import validate_candidate, validate_events  # noqa: E402


def test_rejects_without_date():
    e = EventItem(institution="X", title="Debat", url="http://x", starts_at=None)
    assert validate_candidate(e) is None


def test_rejects_institutional_noise():
    e = EventItem(
        institution="Hangar",
        title="Resolució de la convocatòria de residència",
        url="http://hangar.org/res",
        starts_at="2026-03-25",
        summary="El comitè de selecció ha decidit...",
    )
    assert validate_candidate(e) is None


def test_rejects_sport():
    e = EventItem(
        institution="X",
        title="Victòria del Barça a la final",
        url="http://x",
        starts_at="2026-03-25",
    )
    assert validate_candidate(e) is None


def test_keeps_valid_debate():
    e = EventItem(
        institution="CCCB",
        title="Debat sobre democràcia",
        url="http://cccb.org/d",
        starts_at="2026-03-25",
        event_kind="debat",
        confidence="high",
    )
    result = validate_candidate(e)
    assert result is not None
    assert result.confidence == "high"


def test_validate_events_counts():
    evs = [
        EventItem(institution="A", title="Debat", url="http://a", starts_at="2026-03-25"),
        EventItem(institution="B", title="Sense data", url="http://b", starts_at=None),
        EventItem(
            institution="C",
            title="Resolució de la convocatòria X",
            url="http://c",
            starts_at="2026-03-25",
        ),
    ]
    out = validate_events(evs)
    assert len(out) == 1
    assert out[0].institution == "A"
