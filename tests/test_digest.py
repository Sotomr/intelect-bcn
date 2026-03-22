from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from digest import build_digest_html  # noqa: E402
from models import EventItem  # noqa: E402


def test_digest_merges_same_title_multiday():
    evs = [
        EventItem(
            institution="CCCB",
            title="Utopies, distopies i imaginació política",
            url="https://www.cccb.org/a",
            starts_at="2026-03-25",
            tier="premium",
            area="Política i geopolítica",
            summary="Debats",
            source="cccb",
        ),
        EventItem(
            institution="CCCB",
            title="Utopies, distopies i imaginació política",
            url="https://www.cccb.org/b",
            starts_at="2026-03-26",
            tier="premium",
            area="Política i geopolítica",
            summary="Debats",
            source="cccb",
        ),
        EventItem(
            institution="CCCB",
            title="Utopies, distopies i imaginació política",
            url="https://www.cccb.org/c",
            starts_at="2026-03-27",
            tier="premium",
            area="Política i geopolítica",
            summary="Debats",
            source="cccb",
        ),
    ]
    html = build_digest_html(
        evs,
        tz_name="Europe/Madrid",
        window_days=14,
        max_per_institution=20,
        max_base_events=50,
        failures=[],
    )
    assert "25/03–27/03" in html
    assert "3 sessions" in html
    assert html.count("Utopies, distopies i imaginació política") == 1
    assert "Política i geopolítica" in html
    assert "CCCB" in html
