from __future__ import annotations

import html
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Iterable
from zoneinfo import ZoneInfo

from editorial import AREA_SECTION_ORDER, classify_area, display_source_line
from models import EventItem
from selector import SelectionResult, select_candidates, score_event

_TIER_ORDER = ("nerd", "base", "premium")


def _tier_rank(tier: str) -> int:
    return _TIER_ORDER.index(tier) if tier in _TIER_ORDER else 9


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
            _tier_rank(x.tier),
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
    return re.sub(r"\s+", " ", (title or "").strip().lower())


def _cluster_same_title_same_inst(events: list[EventItem]) -> list[list[EventItem]]:
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
    merged.sort(key=lambda x: (_tier_rank(x.tier), x.starts_at or "", x.title))
    return merged


def _apply_areas(events: list[EventItem]) -> None:
    for e in events:
        e.area = classify_area(e.title, e.institution, e.label)


def _source_label(source: str) -> str:
    s = (source or "").strip()
    labels = {"guia_bcn": "Guia BCN", "cccb": "CCCB", "cidob": "CIDOB", "iccub": "ICCUB"}
    if s in labels:
        return labels[s]
    if s.startswith("rss:"):
        return s[4:].replace("_", " ").title()
    return s or "?"


_KIND_LABELS = {
    "debat": "Debat",
    "conferencia": "Conferència",
    "seminari": "Seminari",
    "xerrada": "Xerrada",
    "presentacio": "Presentació",
    "taller": "Taller",
    "projeccio": "Projecció",
    "exposicio": "Exposició",
    "sessio": "Sessió",
    "visita": "Visita",
}


def _format_highlight_block(r: SelectionResult) -> str:
    e = r.event
    when = _fmt_day(e.starts_at or "")
    fmt = _KIND_LABELS.get(e.event_kind, "Sessió")
    inst = html.escape(display_source_line(e))
    title = html.escape(e.title)
    link = html.escape(e.url, quote=True)
    phrase = html.escape(r.editorial_phrase)
    return (
        f"<b>{when}</b> · {html.escape(fmt)} · {inst}\n"
        f'<a href="{link}">{title}</a>\n'
        f"<i>{phrase}</i>"
    )


def _format_recommendation_line(r: SelectionResult) -> str:
    e = r.event
    when = _fmt_day(e.starts_at or "")
    title = html.escape(e.title)
    link = html.escape(e.url, quote=True)
    inst = html.escape(display_source_line(e))
    return f'• <b>{when}</b> — <a href="{link}">{title}</a> · <i>{inst}</i>'


def build_digest_html(
    events: list[EventItem],
    *,
    tz_name: str,
    window_days: int,
    max_per_institution: int,
    max_base_events: int,
    failures: list[str],
    total_before_window: int | None = None,
    highlight_count: int = 5,
    max_per_source_highlights: int = 3,
    scraper_counts_merged: dict[str, int] | None = None,
) -> str:
    tz = ZoneInfo(tz_name)
    today = datetime.now(tz).date()
    end = today + timedelta(days=window_days - 1)
    events = _limit_base(events, max_base_events)
    _apply_areas(events)

    lines: list[str] = [
        "<b>Intelect BCN</b> — selecció setmanal",
        f"<i>{_fmt_day(today.isoformat())}–{_fmt_day(end.isoformat())} · "
        f"idees, ciència, política, cultura</i>",
        "",
    ]

    if not events and not failures:
        lines.append("Sense esdeveniments amb data dins la finestra.")
        return "\n".join(lines)

    if not events and failures:
        lines.append("<b>Cap acte dins la finestra de dates.</b>")
        lines.append("")

    if events:
        highlights, rest = select_candidates(
            events,
            max_highlights=max(1, highlight_count),
            max_per_source=max_per_source_highlights,
        )

        # Separar rest en recomanacions fortes i agenda ampliada
        main_rest = [r for r in rest if r.event.event_kind != "visita" and r.score >= 40]
        expanded = [r for r in rest if r.event.event_kind == "visita" or r.score < 40]

        lines.append("<b>Destacats</b>")
        if highlights:
            for r in highlights:
                lines.append(_format_highlight_block(r))
                lines.append("")
        else:
            lines.append("<i>(Cap entrada prou rellevant per destacar.)</i>")
            lines.append("")

        max_recs = 6
        if main_rest:
            lines.append("<b>Recomanacions</b>")
            lines.append("")
            by_area: dict[str, list[SelectionResult]] = defaultdict(list)
            for r in main_rest:
                by_area[r.category].append(r)
            area_keys = [a for a in AREA_SECTION_ORDER if by_area.get(a)]
            rest_areas = sorted(k for k in by_area.keys() if k not in AREA_SECTION_ORDER)
            ordered_areas = area_keys + rest_areas

            total_shown = 0
            for area in ordered_areas:
                if total_shown >= max_recs:
                    break
                chunk = by_area.get(area) or []
                if not chunk:
                    continue
                chunk.sort(key=lambda x: (-x.score, x.event.starts_at or ""))
                lines.append(f"<b>{html.escape(area)}</b>")
                for r in chunk[:2]:
                    if total_shown >= max_recs:
                        break
                    lines.append(_format_recommendation_line(r))
                    total_shown += 1
                lines.append("")

        if expanded:
            lines.append("<b>Agenda ampliada</b>")
            lines.append("")
            expanded.sort(key=lambda r: (r.event.starts_at or "", r.event.title))
            for r in expanded[:12]:
                lines.append(_format_recommendation_line(r))
            if len(expanded) > 12:
                lines.append(f"  <i>… i {len(expanded) - 12} més</i>")
            lines.append("")

    if failures:
        lines.append("<b>Fonts amb error</b>")
        for f in failures:
            lines.append(f"  • {html.escape(f)}")
    return "\n".join(lines).strip()


def format_novelties_html(events: list[EventItem]) -> str:
    if not events:
        return ""
    _apply_areas(events)
    lines: list[str] = [
        "",
        "<b>Novetats al radar</b>",
        "",
    ]
    for e in events[:10]:
        title = html.escape(e.title)
        link = html.escape(e.url, quote=True)
        when = _fmt_day((e.starts_at or "")[:10])
        inst = html.escape(display_source_line(e))
        lines.append(
            f'• <b>{when}</b> — <a href="{link}">{title}</a> · <i>{inst}</i>'
        )
    if len(events) > 10:
        lines.append(f"  <i>… i {len(events) - 10} més</i>")
    return "\n".join(lines)
