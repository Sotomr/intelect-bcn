import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_rss_feeds_for_set_filters_institutional_vs_media():
    from scrapers.rss_feeds import RSS_FEEDS, rss_feeds_for_set

    assert len(rss_feeds_for_set("all")) == len(RSS_FEEDS)
    inst = rss_feeds_for_set("institutional")
    assert all(f.kind == "institutional" for f in inst)
    assert len(inst) < len(RSS_FEEDS)
    media = rss_feeds_for_set("media")
    assert {f.source_id for f in media} >= {"ara_cultura", "beteve"}


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

    class FakeResp:
        content = b"<rss/>"

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(rf.requests, "get", lambda url, timeout=60, headers=None: FakeResp())
    monkeypatch.setattr(rf.feedparser, "parse", lambda data: D())

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


def test_rss_prefers_event_date_in_title_over_publication(monkeypatch):
    class E:
        title = "Cicle: xerrada el 28/03/2026 — tema"
        link = "https://example.org/e2"
        summary = ""
        published_parsed = time.struct_time((2026, 3, 10, 12, 0, 0, 0, 0, 0))

    class D:
        entries = [E()]
        bozo = False

    import scrapers.rss_feeds as rf

    class FakeResp:
        content = b"<rss/>"

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(rf.requests, "get", lambda url, timeout=60, headers=None: FakeResp())
    monkeypatch.setattr(rf.feedparser, "parse", lambda data: D())
    monkeypatch.setattr(rf, "_rss_today", lambda: date(2026, 3, 22))

    from scrapers.rss_feeds import RssFeed

    monkeypatch.setattr(
        rf,
        "RSS_FEEDS",
        (
            RssFeed(
                "test2",
                "https://example.org/feed2",
                "Test Institution",
                "premium",
                False,
            ),
        ),
    )
    evs = rf.fetch_rss_feeds(max_per_feed=10)
    assert len(evs) == 1
    assert evs[0].starts_at == "2026-03-28"
