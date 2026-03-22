from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from enrichment import _extract_time, _clean_text  # noqa: E402
from models import EventItem  # noqa: E402


def test_extract_time_colon():
    assert _extract_time("Horari: de 18:30 a 20:00") == "18:30"


def test_extract_time_h():
    assert _extract_time("From 15h00 to 16h00") == "15:00"


def test_extract_time_no_match():
    assert _extract_time("16 de febrer 2026") == ""


def test_extract_time_dotted_with_h():
    assert _extract_time("Inici: 19.30 h") == "19:30"


def test_clean_text_trims():
    text = "A " * 2000
    result = _clean_text(text, max_len=100)
    assert len(result) <= 100


def test_rss_low_confidence_rejected_by_validation():
    from validation import validate_candidate

    e = EventItem(
        institution="Test RSS",
        title="Article cultural",
        url="http://example.com/rss",
        starts_at="2026-03-25",
        source="rss:test_feed",
        confidence="low",
    )
    assert validate_candidate(e) is None


def test_rss_high_confidence_kept():
    from validation import validate_candidate

    e = EventItem(
        institution="Test RSS",
        title="Conferència sobre física",
        url="http://example.com/conf",
        starts_at="2026-03-28",
        source="rss:test_feed",
        confidence="high",
        event_kind="conferencia",
    )
    result = validate_candidate(e)
    assert result is not None
