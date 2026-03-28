from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from models import EventItem, clean_placeholder_place  # noqa: E402


def test_clean_placeholder_place():
    assert clean_placeholder_place("Barcelona (lloc)") == ""
    assert clean_placeholder_place("  barcelona  ") == ""
    assert clean_placeholder_place("CCCB") == "CCCB"


def test_from_dict_strips_placeholder_institution():
    e = EventItem.from_dict(
        {
            "institution": "Barcelona (lloc)",
            "title": "Prova",
            "url": "https://example.org/e",
        }
    )
    assert e.institution == ""
    assert e.venue == ""


def test_to_dict_does_not_persist_placeholder():
    e = EventItem(
        institution="Barcelona (lloc)",
        title="Prova",
        url="https://example.org/e",
    )
    assert e.to_dict()["institution"] == ""
