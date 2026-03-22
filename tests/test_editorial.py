from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from editorial import display_source_line, editorial_score, pick_highlights, source_bucket  # noqa: E402
from models import EventItem  # noqa: E402


def test_highlights_quality_first_no_forced_diversity():
    """Una visita de baixa puntuació NO entra als destacats només per diversitat de fonts."""
    cccb = [
        EventItem(
            institution="CCCB",
            title=f"Debat urgent {i}",
            url=f"https://cccb.org/d{i}",
            starts_at="2026-03-25",
            tier="premium",
            label="Debats",
            source="cccb",
        )
        for i in range(6)
    ]
    guia_visita = EventItem(
        institution="Museu de prova",
        title="Visita al museu (prova editorial)",
        url="https://guia.barcelona.cat/ca/agenda/visita-test",
        starts_at="2026-03-25",
        tier="base",
        label="Guia Barcelona",
        source="guia_bcn",
    )
    hi, _rest = pick_highlights(cccb + [guia_visita], k=7, max_per_source=3)
    assert not any(e.source == "guia_bcn" for e in hi)


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
def test_display_source_line_shows_institution_only():
    e = EventItem(
        institution="Institut d’Estudis Catalans",
        title="Taula rodona",
        url="https://iec.cat/x",
        starts_at="2026-03-25",
        tier="nerd",
        source="rss:iec",
    )
    line = display_source_line(e)
    assert "via RSS" not in line
    assert "RSS mitjà" not in line
    assert "Institut" in line
