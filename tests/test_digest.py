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
    assert "propostes" in html
    assert "CCCB:" in html
    assert "CCCB" in html


def test_digest_shows_pipeline_counts_and_cccb_only_hint():
    evs = [
        EventItem(
            institution="CCCB",
            title=f"Acte {i}",
            url=f"https://cccb.org/{i}",
            starts_at="2026-03-25",
            tier="premium",
            source="cccb",
        )
        for i in range(4)
    ]
    html = build_digest_html(
        evs,
        tz_name="Europe/Madrid",
        window_days=14,
        max_per_institution=20,
        max_base_events=50,
        failures=[],
        scraper_counts_merged={"cccb": 40},
    )
    assert "Pipeline" in html
    assert "CCCB: 40" in html
    assert "Guia CSV, CIDOB i RSS no figuren" in html
    assert "tot el radar és d’una sola font" in html
