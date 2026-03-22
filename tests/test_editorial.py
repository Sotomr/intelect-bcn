from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from editorial import editorial_score, pick_highlights, source_bucket  # noqa: E402
from models import EventItem  # noqa: E402


def test_cccb_quota_in_highlights():
    evs = [
        EventItem(
            institution="CCCB",
            title=f"Acte CCCB {i}",
            url=f"https://cccb.org/{i}",
            starts_at="2026-03-25",
            tier="premium",
            area="Política i món",
            source="cccb",
        )
        for i in range(10)
    ]
    evs.append(
        EventItem(
            institution="CIDOB",
            title="Debat geopolítica",
            url="https://cidob.org/1",
            starts_at="2026-03-25",
            tier="nerd",
            area="Política i món",
            source="cidob",
        )
    )
    hi, rest = pick_highlights(evs, k=7, max_per_source=3)
    assert len(hi) <= 7
    assert sum(1 for e in hi if source_bucket(e) == "cccb") <= 3
    assert any(e.source == "cidob" for e in hi)


def test_visit_scores_lower_than_debate():
    debat = EventItem(
        institution="CCCB",
        title="Debat sobre democràcia",
        url="https://cccb.org/d",
        starts_at="2026-03-25",
        tier="premium",
        label="Debats",
        source="cccb",
    )
    visita = EventItem(
        institution="CCCB",
        title="Visita guiada al Mirador",
        url="https://cccb.org/v",
        starts_at="2026-03-25",
        tier="premium",
        label="Visites",
        source="cccb",
    )
    assert editorial_score(debat) > editorial_score(visita)
