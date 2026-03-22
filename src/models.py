from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class EventItem:
    """Esdeveniment amb capa editorial (base / premium / nerd) i àmbit temàtic."""

    institution: str
    title: str
    url: str
    starts_at: Optional[str] = None
    ends_at: Optional[str] = None
    label: str = ""
    raw_date: str = ""
    # base = Guia/Gencat filtrat; premium = institucions fortes; nerd = recerca/política/CIència dura
    tier: str = "base"
    area: str = "Cultura i espai públic"
    summary: str = ""
    source: str = ""
    # Només RSS: "institutional" | "media" (buit = no RSS o llegat sense camp)
    rss_source_kind: str = ""
    # Tipus d'acte: debat, conferencia, seminari, taller, exposicio, visita,
    # projeccio, xerrada, presentacio, sessio (buit = no classificat encara)
    event_kind: str = ""
    # Confiança que és un acte real: high, medium, low
    confidence: str = "low"

    def stable_key(self) -> str:
        return f"{self.source}|{self.url}|{self.starts_at or ''}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "institution": self.institution,
            "title": self.title,
            "url": self.url,
            "starts_at": self.starts_at,
            "ends_at": self.ends_at,
            "label": self.label,
            "raw_date": self.raw_date,
            "tier": self.tier,
            "area": self.area,
            "summary": self.summary,
            "source": self.source,
            "rss_source_kind": self.rss_source_kind or "",
            "event_kind": self.event_kind or "",
            "confidence": self.confidence or "low",
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "EventItem":
        return EventItem(
            institution=d["institution"],
            title=d["title"],
            url=d["url"],
            starts_at=d.get("starts_at"),
            ends_at=d.get("ends_at"),
            label=d.get("label") or "",
            raw_date=d.get("raw_date") or "",
            tier=d.get("tier") or "base",
            area=d.get("area") or "Cultura i espai públic",
            summary=d.get("summary") or "",
            source=d.get("source") or "",
            rss_source_kind=d.get("rss_source_kind") or "",
            event_kind=d.get("event_kind") or "",
            confidence=d.get("confidence") or "low",
        )


def _nkind(s: str) -> str:
    s = (s or "").lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip()


def classify_event_kind(title: str, label: str = "", source: str = "") -> str:
    """Classifica el tipus d'acte a partir del títol i label (slug curt)."""
    t = _nkind(f"{title} {label}")
    if "debat" in t or "debats" in t:
        return "debat"
    if "col.loqui" in t or "col·loqui" in t or "coloquio" in t:
        return "debat"
    if "conferencia" in t:
        return "conferencia"
    if "seminari" in t or "seminario" in t:
        return "seminari"
    if "xerrada" in t or "convers" in t or "tertulia" in t:
        return "xerrada"
    if "presentacio" in t:
        return "presentacio"
    if "visita guiada" in t or (t.startswith("visita ") and "exposici" in t):
        return "visita"
    if "visita" in t or "mirador" in t:
        return "visita"
    if "taller" in t or "curs " in t or " curs" in t:
        return "taller"
    if "projeccio" in t or "documental" in t or "audiovisual" in t or "simfonies" in t:
        return "projeccio"
    if "exposicio" in t or "exposicion" in t:
        return "exposicio"
    if source.startswith("rss:") and "entrevista" in t:
        return "article"
    return "sessio"


@dataclass
class Snapshot:
    fetched_at: str
    events: List[EventItem]

    def to_dict(self) -> dict[str, Any]:
        return {
            "fetched_at": self.fetched_at,
            "events": [e.to_dict() for e in self.events],
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Snapshot":
        raw = d.get("events") or []
        return Snapshot(
            fetched_at=d["fetched_at"],
            events=[EventItem.from_dict(x) for x in raw],
        )
