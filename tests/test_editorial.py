from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from editorial import display_source_line  # noqa: E402
from selector import score_event, select_candidates  # noqa: E402
from models import EventItem  # noqa: E402


def test_selector_quality_first():
    """Visites no entren als destacats."""
    cccb = [
        EventItem(
            institution="CCCB",
            title=f"Debat urgent {i}",
            url=f"https://cccb.org/d{i}",
            starts_at="2026-03-25",
            tier="premium",
            source="cccb",
            event_kind="debat",
            confidence="high",
        )
        for i in range(6)
    ]
    guia_visita = EventItem(
        institution="Museu de prova",
        title="Visita al museu",
        url="https://guia.barcelona.cat/ca/agenda/visita-test",
        starts_at="2026-03-25",
        tier="base",
        source="guia_bcn",
        event_kind="visita",
        confidence="high",
    )
    hi, _rest = select_candidates(cccb + [guia_visita], max_highlights=5, max_per_source=3)
    assert not any(r.event.source == "guia_bcn" for r in hi)


def test_selector_source_quota():
    evs = [
        EventItem(
            institution="CCCB",
            title=f"Debat CCCB {i}",
            url=f"https://cccb.org/{i}",
            starts_at="2026-03-25",
            tier="premium",
            source="cccb",
            event_kind="debat",
            confidence="high",
        )
        for i in range(10)
    ]
    evs.append(
        EventItem(
            institution="CIDOB",
            title="Debat geopolítica CIDOB",
            url="https://cidob.org/1",
            starts_at="2026-03-25",
            tier="nerd",
            source="cidob",
            event_kind="debat",
            confidence="high",
        )
    )
    hi, rest = select_candidates(evs, max_highlights=5, max_per_source=3)
    assert len(hi) <= 5
    cccb_hi = sum(1 for r in hi if r.event.source == "cccb")
    assert cccb_hi <= 3


def test_debate_scores_higher_than_visit():
    debat = EventItem(
        institution="CCCB",
        title="Debat sobre democràcia",
        url="https://cccb.org/d",
        starts_at="2026-03-25",
        tier="premium",
        source="cccb",
        event_kind="debat",
        confidence="high",
    )
    visita = EventItem(
        institution="CCCB",
        title="Visita guiada al Mirador",
        url="https://cccb.org/v",
        starts_at="2026-03-25",
        tier="premium",
        source="cccb",
        event_kind="visita",
        confidence="high",
    )
    assert score_event(debat) > score_event(visita)


def test_display_source_line_shows_institution_only():
    e = EventItem(
        institution="Institut d'Estudis Catalans",
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


def test_selector_editorial_phrase():
    e = EventItem(
        institution="CIDOB",
        title="Conferència sobre geopolítica i Europa",
        url="https://cidob.org/conf",
        starts_at="2026-03-25",
        tier="nerd",
        source="cidob",
        event_kind="conferencia",
        confidence="high",
    )
    hi, _ = select_candidates([e], max_highlights=5)
    assert len(hi) == 1
    assert hi[0].editorial_phrase
    assert len(hi[0].editorial_phrase) > 10
