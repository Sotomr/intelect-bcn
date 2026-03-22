import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_rss_builds_events(monkeypatch):
    class E:
        title = "Conferència sobre filosofia política"
        link = "https://example.org/e1"
        summary = "<p>Resum</p>"
        published_parsed = time.struct_time((2026, 3, 25, 12, 0, 0, 0, 0, 0))

    class D:
        entries = [E()]
        bozo = False

    import scrapers.rss_feeds as rf

    monkeypatch.setattr(rf.feedparser, "parse", lambda url: D())

    # Només una font: patch RSS_FEEDS to single entry
    from scrapers.rss_feeds import RssFeed

    monkeypatch.setattr(
        rf,
        "RSS_FEEDS",
        (
            RssFeed(
                "test",
                "https://example.org/feed",
                "Test Institution",
                "premium",
                True,
            ),
        ),
    )
    evs = rf.fetch_rss_feeds(max_per_feed=10)
    assert len(evs) == 1
    assert evs[0].url == "https://example.org/e1"
    assert evs[0].starts_at == "2026-03-25"
