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
        EventItem(
            institution="CCCB",
            title="Utopies, distopies i imaginació política",
            url="https://www.cccb.org/c",
            starts_at="2026-03-27",
            tier="premium",
            area="Política i món",
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
    # Un dia pot anar a «Destacats»; la resta es fusiona en «Altres recomanacions».
    assert "sessions" in html
    assert "Utopies, distopies i imaginació política" in html
    assert "Política i món" in html
    assert "Destacats de la setmana" in html
    assert "Radar:" in html
    assert "CCCB:" in html
    assert "CCCB" in html
