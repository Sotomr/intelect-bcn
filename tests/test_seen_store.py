from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from models import EventItem, Snapshot  # noqa: E402
from seen_store import (  # noqa: E402
    compute_novelties,
    migrate_seen_from_snapshot,
    prune_seen_keys,
    register_current_window,
)


def test_novelties_only_new_keys():
    a = EventItem(
        institution="X",
        title="Un",
        url="https://a",
        starts_at="2026-04-01",
        tier="base",
        area="G",
        source="t",
    )
    b = EventItem(
        institution="Y",
        title="Dos",
        url="https://b",
        starts_at="2026-04-02",
        tier="base",
        area="G",
        source="t",
    )
    seen = {a.stable_key(): "2026-01-01T00:00:00+00:00"}
    nov = compute_novelties([a, b], seen)
    assert len(nov) == 1
    assert nov[0].url == "https://b"


def test_migrate_from_snapshot():
    e = EventItem(
        institution="Z",
        title="Z",
        url="https://z",
        starts_at="2026-05-01",
        tier="base",
        area="G",
        source="s",
    )
    snap = Snapshot(fetched_at="2026-03-01T00:00:00+00:00", events=[e])
    seen = migrate_seen_from_snapshot({}, snap)
    assert e.stable_key() in seen


def test_prune_old_keys():
    seen = {
        "old": "2020-01-01T00:00:00+00:00",
        "new": "2026-03-01T00:00:00+00:00",
    }
    out = prune_seen_keys(seen, max_age_days=30)
    assert "old" not in out
    assert "new" in out


def test_register_adds_keys():
    e = EventItem(
        institution="Z",
        title="N",
        url="https://n",
        starts_at="2026-06-01",
        tier="base",
        area="G",
        source="s",
    )
    out = register_current_window([e], {})
    assert e.stable_key() in out
