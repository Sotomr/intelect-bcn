import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rss_event_filter import rss_entry_is_valid_event  # noqa: E402


def test_rejects_sport_news():
    assert not rss_entry_is_valid_event(
        source_id="beteve",
        title="El Barça ja és de Divisió d'Honor",
        summary="Victòria a la final del play-off.",
        link="https://beteve.cat/x",
    )


def test_rejects_jfk_gossip():
    assert not rss_entry_is_valid_event(
        source_id="ara_cultura",
        title="La història d'amor de JFK Jr. i Carolyn Bessette",
        summary="Al juliol farà 27 anys que van morir.",
        link="https://ara.cat/x",
    )


def test_keeps_conference_ara():
    assert rss_entry_is_valid_event(
        source_id="ara_cultura",
        title="Presentació del llibre «X» amb debat posterior",
        summary="Sessió a la llibreria amb l'autor.",
        link="https://ara.cat/agenda/x",
    )


def test_institutional_feed_allows_without_strict_url():
    assert rss_entry_is_valid_event(
        source_id="iec",
        title="Conferència sobre matemàtiques i societat",
        summary="A l'IEC.",
        link="https://iec.cat/x",
    )
