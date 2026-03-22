from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scrapers.cccb import _parse_cccb_calendar  # noqa: E402
from scrapers.cidob import _parse_cidob_date, _parse_cidob_listing  # noqa: E402


def test_cidob_date():
    assert _parse_cidob_date("29  Ene 2026") is not None
    d = _parse_cidob_date("18  Feb 2026")
    assert d.year == 2026 and d.month == 2 and d.day == 18


def test_cidob_listing_snippet():
    html = """
    <article class="event event-simple">
      <a href="/actividades/foo-bar" class="event-simple__link event__link-wrapper">
        <h3 class="event-simple__title h3">Prova geopolítica</h3>
        <div class="event-simple__date">15  Mar 2026</div>
      </a>
    </article>
    """
    evs = _parse_cidob_listing(html, "https://www.cidob.org")
    assert len(evs) == 1
    assert evs[0].institution == "CIDOB"
    assert "Prova" in evs[0].title
    assert evs[0].url == "https://www.cidob.org/actividades/foo-bar"
    assert evs[0].starts_at == "2026-03-15"


def test_cccb_calendar_fixture():
    html = """
    <html><body>
    <h2 class="mb-spacer-300 text-capitalize">març 2026</h2>
    <div class="agenda-card-row">
      <div class="agenda-card-date">
        <span class="agenda-card-date-num">14</span>
        <span class="agenda-card-date-text">dijous</span>
      </div>
      <ul class="agenda-card-list">
        <li class="agenda-card-item">
          <a href="https://www.cccb.org/ca/w/activitats/exemple-debat"
             title="Debat d'exemple">
            <p class="agenda-card-pretitle"><span>Debat</span>Programa</p>
            <p class="agenda-card-title">Debat d'exemple</p>
          </a>
        </li>
      </ul>
    </div>
    </body></html>
    """
    evs = _parse_cccb_calendar(html)
    assert len(evs) == 1
    assert evs[0].starts_at == "2026-03-14"
    assert evs[0].institution == "CCCB"
