from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dedupe import dedupe_events  # noqa: E402
from models import EventItem  # noqa: E402


def test_dedupe_keeps_better_tier():
    a = EventItem(
        institution="CCCB",
        title="Mateix títol",
        url="https://guia.barcelona.cat/ca/agenda/1",
        starts_at="2026-04-01",
        tier="base",
        area="X",
        source="guia_bcn",
    )
    b = EventItem(
        institution="CCCB",
        title="Mateix títol",
        url="https://www.cccb.org/ca/w/activitats/foo",
        starts_at="2026-04-01",
        tier="premium",
        area="X",
        source="cccb",
    )
    out = dedupe_events([a, b])
    assert len(out) == 1
    assert out[0].tier == "premium"


def test_dedupe_fuzzy_strips_year_position():
    """'Jornada OTEC 2026: Energies...' vs 'Jornada OTEC: Energies... 2026' = 1 event."""
    a = EventItem(
        institution="Col·legi d'Enginyers",
        title="Jornada OTEC 2026: Energies renovables per a empreses",
        url="https://eng.cat/a",
        starts_at="2026-03-22",
        tier="nerd",
        source="rss:enginyers_bcn",
    )
    b = EventItem(
        institution="Col·legi d'Enginyers",
        title="Jornada OTEC: Energies renovables per empreses 2026",
        url="https://eng.cat/b",
        starts_at="2026-03-22",
        tier="nerd",
        source="rss:enginyers_bcn",
    )
    out = dedupe_events([a, b])
    assert len(out) == 1
