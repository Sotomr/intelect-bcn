from __future__ import annotations

import html
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Iterable
from zoneinfo import ZoneInfo

from models import EventItem

_TIER_ORDER = ("premium", "nerd", "base")
_TIER_TITLE = {
    "premium": "Institucions destacades",
    "nerd": "Recerca, política i ciència",
    "base": "Radar Guia Barcelona (dades obertes, filtrat)",
}


def _parse_event_date(e: EventItem) -> date | None:
    if not e.starts_at:
        return None
    try:
        return date.fromisoformat(e.starts_at[:10])
    except ValueError:
        return None


def filter_events_in_window(
    events: Iterable[EventItem],
    *,
    tz_name: str,
    window_days: int,
) -> list[EventItem]:
    tz = ZoneInfo(tz_name)
    today = datetime.now(tz).date()
    end = today + timedelta(days=window_days)
    out: list[EventItem] = []
    for e in events:
        d = _parse_event_date(e)
        if d is None:
            continue
        if today <= d < end:
            out.append(e)
    out.sort(
        key=lambda x: (
            _TIER_ORDER.index(x.tier) if x.tier in _TIER_ORDER else 9,
            x.starts_at or "",
            x.area,
            x.institution,
            x.title,
        )
    )
    return out


def _fmt_day(iso: str) -> str:
    if len(iso) < 10:
        return iso
    y, m, d = iso[:10].split("-")
    return f"{d}/{m}"


def _norm_title_key(title: str) -> str:
    t = re.sub(r"\s+", " ", (title or "").strip().lower())
    return t


def _cluster_same_title_same_inst(events: list[EventItem]) -> list[list[EventItem]]:
    """
    Agrupa esdeveniments amb mateix títol (i ja comparteixen institució dins el grup).
    Ordena grups per data del primer dia.
    """
    by_key: dict[str, list[EventItem]] = defaultdict(list)
    for e in events:
        by_key[_norm_title_key(e.title)].append(e)
    clusters: list[list[EventItem]] = []
    for _k, evs in by_key.items():
        evs = sorted(evs, key=lambda x: x.starts_at or "")
        clusters.append(evs)
    clusters.sort(key=lambda g: g[0].starts_at or "")
    return clusters


def _fmt_date_range(cluster: list[EventItem]) -> str:
    days: list[str] = []
    for e in cluster:
        if e.starts_at and len(e.starts_at) >= 10:
            days.append(e.starts_at[:10])
    if not days:
        return ""
    days = sorted(set(days))
    if len(days) == 1:
        return _fmt_day(days[0])
    return f"{_fmt_day(days[0])}–{_fmt_day(days[-1])}"


def _limit_base(events: list[EventItem], max_base: int) -> list[EventItem]:
    if max_base <= 0:
        return events
    non_base = [e for e in events if e.tier != "base"]
    base = [e for e in events if e.tier == "base"][:max_base]
    merged = non_base + base
    merged.sort(
        key=lambda x: (
            _TIER_ORDER.index(x.tier) if x.tier in _TIER_ORDER else 9,
            x.starts_at or "",
            x.area,
            x.institution,
            x.title,
        )
    )
    return merged


def build_digest_html(
    events: list[EventItem],
    *,
    tz_name: str,
    window_days: int,
    max_per_institution: int,
    max_base_events: int,
    failures: list[str],
) -> str:
    tz = ZoneInfo(tz_name)
    today = datetime.now(tz).date()
    end = today + timedelta(days=window_days - 1)
    events = _limit_base(events, max_base_events)

    lines: list[str] = [
        "<b>Intelect BCN</b> — selecció setmanal",
        f"<i>{_fmt_day(today.isoformat())}–{_fmt_day(end.isoformat())} · "
        f"idees, ciència, política, cultura (finestra {window_days} dies)</i>",
        "",
    ]
    if not events and not failures:
        lines.append("Sense esdeveniments amb data dins la finestra (o fonts buides).")
        return "\n".join(lines)

    by_tier: dict[str, list[EventItem]] = {t: [] for t in _TIER_ORDER}
    for e in events:
        if e.tier in by_tier:
            by_tier[e.tier].append(e)
        else:
            by_tier.setdefault("base", []).append(e)

    for tier in _TIER_ORDER:
        chunk = by_tier.get(tier) or []
        if not chunk:
            continue
        lines.append(f"<b>{_TIER_TITLE.get(tier, tier)}</b>")
        by_area: dict[str, list[EventItem]] = {}
        for e in chunk:
            by_area.setdefault(e.area, []).append(e)

        for area in sorted(by_area.keys()):
            lines.append(f"<u>{html.escape(area)}</u>")
            inst_map: defaultdict[str, list[EventItem]] = defaultdict(list)
            for e in by_area[area]:
                inst_map[e.institution].append(e)
            for inst in sorted(inst_map.keys()):
                raw_sorted = sorted(inst_map[inst], key=lambda e: e.starts_at or "")
                clusters = _cluster_same_title_same_inst(raw_sorted)
                shown = clusters[:max_per_institution]
                for cluster in shown:
                    e0 = cluster[0]
                    when = (
                        _fmt_date_range(cluster)
                        if len(cluster) > 1
                        else _fmt_day(e0.starts_at or "")
                    )
                    title = html.escape(e0.title)
                    link = html.escape(e0.url, quote=True)
                    summ = html.escape((e0.summary or e0.title)[:200])
                    inst_h = html.escape(e0.institution)
                    extra = ""
                    if len(cluster) > 1:
                        extra = f' · <i>{len(cluster)} sessions</i>'
                    lines.append(
                        f'• <b>{when}</b> — <a href="{link}">{title}</a> · <i>{inst_h}</i>{extra}'
                        f"\n  <i>{summ}</i>"
                    )
                total = len(clusters)
                if total > max_per_institution:
                    n = total - max_per_institution
                    lines.append(
                        f"  <i>… i {n} més a {html.escape(inst)} (web)</i>"
                    )
            lines.append("")

    if failures:
        lines.append("<b>Fonts amb error</b>")
        for f in failures:
            lines.append(f"  • {html.escape(f)}")
    return "\n".join(lines).strip()


def format_novelties_html(events: list[EventItem]) -> str:
    if not events:
        return ""
    lines: list[str] = [
        "",
        "<b>Novetats al radar</b>",
        "<i>Sessions que encara no havíem vist (respecte al registre d’execucions anteriors)</i>",
        "",
    ]
    for e in events[:14]:
        title = html.escape(e.title)
        link = html.escape(e.url, quote=True)
        when = _fmt_day((e.starts_at or "")[:10])
        lines.append(
            f"  • <b>{html.escape(e.institution)}</b> ({html.escape(e.tier)}) · {when} — "
            f'<a href="{link}">{title}</a>'
        )
    if len(events) > 14:
        lines.append(f"  <i>… i {len(events) - 14} més</i>")
    return "\n".join(lines)
