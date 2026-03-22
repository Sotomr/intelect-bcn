from __future__ import annotations

from models import EventItem


def compute_new_events(previous: list[EventItem], current: list[EventItem]) -> list[EventItem]:
    prev_keys = {e.stable_key() for e in previous}
    return [e for e in current if e.stable_key() not in prev_keys]
