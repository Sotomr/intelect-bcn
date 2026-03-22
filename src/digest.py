from __future__ import annotations

import html
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Iterable
from zoneinfo import ZoneInfo

from editorial import (
    AREA_SECTION_ORDER,
    classify_area,
    detect_format_label,
    display_source_line,
    editorial_blurb,
    editorial_score,
    pick_highlights,
    split_agenda_expanded,
)
from models import EventItem

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
    t = re.sub(r"\s+", " ", (title or "").strip().lower())
    return t


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
    merged.sort(
        key=lambda x: (
            _tier_rank(x.tier),
            x.starts_at or "",
            x.area,
            x.institution,
            x.title,
        )
    )
    return merged


def _apply_areas(events: list[EventItem]) -> None:
    for e in events:
        e.area = classify_area(e.title, e.institution, e.label)


def _radar_summary_line(events: list[EventItem], failures: list[str]) -> str:
    """Comptes per font + avís si alguna font ha fallat (informació ràpida al missatge)."""
    c: Counter[str] = Counter()
    for e in events:
        s = (e.source or "").strip()
        if s.startswith("rss:"):
            c["RSS"] += 1
        elif s == "cccb":
            c["CCCB"] += 1
        elif s == "guia_bcn":
            c["Guia BCN"] += 1
        elif s == "cidob":
            c["CIDOB"] += 1
        else:
            c[s or "?"] += 1
    parts = [f"{k}: {v}" for k, v in sorted(c.items(), key=lambda x: (-x[1], x[0]))]
    line = "<b>Radar:</b> " + str(len(events)) + " actes a la finestra — " + " · ".join(parts)
    if failures:
        line += f" · <i>{len(failures)} font(s) sense resposta (detall al final)</i>"
    return line


def _format_highlight_block(e: EventItem) -> str:
    when = _fmt_day(e.starts_at or "")
    fmt = detect_format_label(e)
    title = html.escape(e.title)
    link = html.escape(e.url, quote=True)
    blurb = html.escape(editorial_blurb(e))
    ctx = html.escape(display_source_line(e))
    return (
        f"<b>{when}</b> · <i>{html.escape(fmt)}</i>\n"
        f"{ctx}\n"
        f'<a href="{link}">{title}</a>\n'
        f"<i>{blurb}</i>"
    )


def _format_theme_line(e0: EventItem, cluster: list[EventItem]) -> str:
    when = (
        _fmt_date_range(cluster)
        if len(cluster) > 1
        else _fmt_day(e0.starts_at or "")
    )
    title = html.escape(e0.title)
    link = html.escape(e0.url, quote=True)
    summ = html.escape((e0.summary or e0.title)[:220])
    ctx = html.escape(display_source_line(e0))
    extra = ""
    if len(cluster) > 1:
        extra = f' · <i>{len(cluster)} sessions</i>'
    return (
        f'• <b>{when}</b> — <a href="{link}">{title}</a> · <i>{ctx}</i>{extra}\n'
        f"  <i>{summ}</i>"
    )


def build_digest_html(
    events: list[EventItem],
    *,
    tz_name: str,
    window_days: int,
    max_per_institution: int,
    max_base_events: int,
    failures: list[str],
    total_before_window: int | None = None,
    highlight_count: int = 7,
    max_per_source_highlights: int = 3,
) -> str:
    tz = ZoneInfo(tz_name)
    today = datetime.now(tz).date()
    end = today + timedelta(days=window_days - 1)
    events = _limit_base(events, max_base_events)
    _apply_areas(events)

    lines: list[str] = [
        "<b>Intelect BCN</b> — selecció setmanal",
        f"<i>{_fmt_day(today.isoformat())}–{_fmt_day(end.isoformat())} · "
        f"idees, ciència, política, cultura (finestra {window_days} dies)</i>",
        "<i>Prescripció amb criteri: primer els <b>destacats</b> (puntuació + diversitat de fonts), "
        "després la resta per temes. Les visites genèriques cauen més avall.</i>",
        "",
    ]
    if events:
        lines.append(_radar_summary_line(events, failures))
        lines.append("")
    if not events and not failures:
        lines.append("Sense esdeveniments amb data dins la finestra (o fonts buides).")
        return "\n".join(lines)

    if not events and failures:
        if total_before_window is not None and total_before_window > 0:
            lines.append(
                f"<b>Cap acte dins la finestra de dates.</b> S’han recuperat "
                f"<b>{total_before_window}</b> esdeveniments de fonts que han respost, "
                f"però cap amb data dins els pròxims <b>{window_days}</b> dies (avui inclòs). "
                "Puja <code>WINDOW_DAYS</code>, revisa <code>TIMEZONE</code> "
                "(el workflow ha de tenir <code>TIMEZONE=Europe/Madrid</code>) "
                "i recorda que als RSS la data de l’acte s’extreu del títol/resum quan hi ha format <code>DD/MM/AAAA</code> o ISO."
            )
        elif total_before_window is not None and total_before_window == 0:
            lines.append(
                "<b>Cap font no ha aportat esdeveniments</b> (sense comptar les que han fallat). "
                "Si només falla el CCCB, la Guia / RSS / CIDOB haurien d’omplir el llistat: "
                "revisa logs (CSV Guia, filtres) o reexecuta."
            )
        else:
            lines.append(
                "<b>No hi ha cap acte a la finestra</b> a partir de les fonts que han respost. "
                "Revisa dates, filtres o reexecuta més tard."
            )
        lines.append("")

    if events:
        highlights, rest = pick_highlights(
            events,
            k=max(1, highlight_count),
            max_per_source=max_per_source_highlights,
        )
        main_rest, expanded = split_agenda_expanded(rest)

        lines.append("<b>Destacats de la setmana</b>")
        lines.append(
            "<i>Poques peces, màxima densitat; quotes per font per no ser només CCCB.</i>"
        )
        if highlights:
            for e in highlights:
                lines.append(_format_highlight_block(e))
                lines.append("")
        else:
            lines.append("<i>(Cap entrada prou diferenciada; mira la secció següent.)</i>")
            lines.append("")

        if main_rest:
            lines.append("<b>Altres recomanacions</b>")
            lines.append("<i>Per temes; ordenat per rellevància editorial.</i>")
            lines.append("")
            by_area: dict[str, list[EventItem]] = defaultdict(list)
            for e in main_rest:
                by_area[e.area].append(e)
            area_keys = [a for a in AREA_SECTION_ORDER if by_area.get(a)]
            rest_areas = sorted(k for k in by_area.keys() if k not in AREA_SECTION_ORDER)
            ordered_areas = area_keys + rest_areas

            for area in ordered_areas:
                chunk = by_area.get(area) or []
                if not chunk:
                    continue
                lines.append(f"<b>{html.escape(area)}</b>")
                chunk.sort(
                    key=lambda x: (
                        -editorial_score(x),
                        x.starts_at or "",
                        x.institution,
                        x.title,
                    )
                )
                inst_map: defaultdict[str, list[EventItem]] = defaultdict(list)
                for e in chunk:
                    inst_map[e.institution].append(e)
                for inst in sorted(inst_map.keys()):
                    raw_sorted = sorted(inst_map[inst], key=lambda e: e.starts_at or "")
                    clusters = _cluster_same_title_same_inst(raw_sorted)
                    shown = clusters[:max_per_institution]
                    for cluster in shown:
                        lines.append(_format_theme_line(cluster[0], cluster))
                    total = len(clusters)
                    if total > max_per_institution:
                        n = total - max_per_institution
                        lines.append(
                            f"  <i>… i {n} més a {html.escape(inst)} (web)</i>"
                        )
                lines.append("")

        if expanded:
            lines.append("<b>Agenda ampliada</b>")
            lines.append(
                "<i>Visites, formats més de servei o puntuació més baixa; encara útils si busques context.</i>"
            )
            lines.append("")
            expanded.sort(
                key=lambda x: (x.starts_at or "", x.institution, x.title)
            )
            inst_map2: defaultdict[str, list[EventItem]] = defaultdict(list)
            for e in expanded:
                inst_map2[e.institution].append(e)
            for inst in sorted(inst_map2.keys()):
                for e in sorted(inst_map2[inst], key=lambda x: x.starts_at or ""):
                    when = _fmt_day(e.starts_at or "")
                    title = html.escape(e.title)
                    link = html.escape(e.url, quote=True)
                    ctx = html.escape(display_source_line(e))
                    lines.append(
                        f'• <b>{when}</b> — <a href="{link}">{title}</a> · <i>{ctx}</i>'
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
    _apply_areas(events)
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
        ctx = html.escape(display_source_line(e))
        lines.append(
            f"  • <b>{when}</b> — "
            f'<a href="{link}">{title}</a> · <i>{ctx}</i>'
        )
    if len(events) > 14:
        lines.append(f"  <i>… i {len(events) - 14} més</i>")
    return "\n".join(lines)
