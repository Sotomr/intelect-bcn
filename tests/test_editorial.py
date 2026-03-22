from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from editorial import display_source_line, editorial_score, pick_highlights, source_bucket  # noqa: E402
from models import EventItem  # noqa: E402


def test_highlights_represent_unpicked_source_below_score_floor():
    """Si tot el pool és CCCB fort, una font amb puntuació baixa (p. ex. Guia visita) té 1 slot."""
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
    assert any(e.source == "guia_bcn" for e in hi)


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


def test_media_rss_lower_score_than_institutional_rss():
    base = dict(
        title="Conferència sobre ciència i ciutat",
        url="https://example.org/c",
        starts_at="2026-03-25",
        tier="nerd",
        label="Conferències",
        institution="Institut d’Estudis Catalans",
    )
    inst_rss = EventItem(**base, source="rss:iec", rss_source_kind="institutional")
    media_rss = EventItem(**base, source="rss:ara_cultura", rss_source_kind="media")
    assert editorial_score(inst_rss) > editorial_score(media_rss)


def test_display_source_line_marks_media_rss():
    e = EventItem(
        institution="Ara Cultura",
        title="Taula rodona",
        url="https://ara.cat/x",
        starts_at="2026-03-25",
        tier="nerd",
        source="rss:ara_cultura",
        rss_source_kind="media",
    )
    assert "RSS mitjà" in display_source_line(e)
