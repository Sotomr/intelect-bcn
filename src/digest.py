"""
Digest setmanal — construeix l'HTML per Telegram.

Format:
- 5 destacats amb data, hora, lloc, títol i frase editorial
- 4 recomanacions en llista plana (sense agrupació per àrea)
- Agenda ampliada (max 6, col·lapsada)
- Sense telemetria interna
"""

from __future__ import annotations

import html
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Iterable
from zoneinfo import ZoneInfo

from editorial import classify_area, display_source_line
from models import EventItem
from selector import SelectionResult, select_candidates


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
    out.sort(key=lambda x: (x.starts_at or "", x.title))
    return out


def _fmt_day(iso: str) -> str:
    if len(iso) < 10:
        return iso
    y, m, d = iso[:10].split("-")
    return f"{d}/{m}"


def _norm_title_key(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").strip().lower())


def _collapse_duplicates(results: list[SelectionResult]) -> list[SelectionResult]:
    """Collapse same-title entries into one with a date range."""
    by_title: dict[str, list[SelectionResult]] = defaultdict(list)
    for r in results:
        by_title[_norm_title_key(r.event.title)].append(r)

    collapsed: list[SelectionResult] = []
    for key, group in by_title.items():
        best = max(group, key=lambda r: r.score)
        if len(group) > 1:
            dates = sorted({r.event.starts_at[:10] for r in group if r.event.starts_at})
            if len(dates) > 1:
                best.event.starts_at = dates[0]
                best.event.ends_at = dates[-1]
        collapsed.append(best)
    collapsed.sort(key=lambda r: (-r.score, r.event.starts_at or ""))
    return collapsed


def _format_highlight_block(r: SelectionResult) -> str:
    e = r.event
    when = _fmt_day(e.starts_at or "")
    if e.ends_at and e.ends_at != e.starts_at:
        when = f"{when}–{_fmt_day(e.ends_at)}"

    time_venue_parts: list[str] = [f"<b>{when}</b>"]
    if e.starts_at_time:
        time_venue_parts.append(e.starts_at_time + "h")
    venue = e.venue or e.institution
    if venue:
        time_venue_parts.append(html.escape(venue))

    header = " · ".join(time_venue_parts)
    title = html.escape(e.title)
    link = html.escape(e.url, quote=True)
    phrase = html.escape(r.editorial_phrase)

    return (
        f"{header}\n"
        f'<a href="{link}">{title}</a>\n'
        f"<i>{phrase}</i>"
    )


def _format_recommendation_line(r: SelectionResult) -> str:
    e = r.event
    when = _fmt_day(e.starts_at or "")
    if e.ends_at and e.ends_at != e.starts_at:
        when = f"{when}–{_fmt_day(e.ends_at)}"
    title = html.escape(e.title)
    link = html.escape(e.url, quote=True)
    inst = html.escape(display_source_line(e))
    return f'• <b>{when}</b> — <a href="{link}">{title}</a> · <i>{inst}</i>'


def _apply_areas(events: list[EventItem]) -> None:
    for e in events:
        e.area = classify_area(e.title, e.institution, e.label)


def build_digest_html(
    events: list[EventItem],
    *,
    tz_name: str,
    window_days: int,
    max_per_institution: int = 0,
    max_base_events: int = 0,
    failures: list[str],
    total_before_window: int | None = None,
    highlight_count: int = 5,
    max_per_source_highlights: int = 3,
    scraper_counts_merged: dict[str, int] | None = None,
) -> str:
    tz = ZoneInfo(tz_name)
    today = datetime.now(tz).date()
    end = today + timedelta(days=window_days - 1)
    _apply_areas(events)

    lines: list[str] = [
        "<b>Intelect BCN</b> — selecció setmanal",
        f"<i>{_fmt_day(today.isoformat())}–{_fmt_day(end.isoformat())}</i>",
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
            max_recommendations=4,
            max_per_source=max_per_source_highlights,
        )

        highlights = _collapse_duplicates(highlights)
        rest = _collapse_duplicates(rest)

        main_rest = [r for r in rest if not r.event.is_service_format and r.score >= 40]
        expanded = [r for r in rest if r.event.is_service_format or r.score < 40]

        # Destacats
        lines.append("<b>Destacats de la setmana</b>")
        lines.append("")
        if highlights:
            for r in highlights:
                lines.append(_format_highlight_block(r))
                lines.append("")
        else:
            lines.append("<i>(Cap entrada prou rellevant per destacar.)</i>")
            lines.append("")

        # Recomanacions (flat list, max 4)
        if main_rest:
            lines.append("<b>Recomanacions</b>")
            main_rest.sort(key=lambda r: (-r.score, r.event.starts_at or ""))
            for r in main_rest[:4]:
                lines.append(_format_recommendation_line(r))
            lines.append("")

        # Agenda ampliada (max 6)
        if expanded:
            lines.append("<b>Agenda ampliada</b>")
            expanded.sort(key=lambda r: (r.event.starts_at or "", r.event.title))
            for r in expanded[:6]:
                lines.append(_format_recommendation_line(r))
            if len(expanded) > 6:
                lines.append(f"  <i>… i {len(expanded) - 6} més</i>")
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
