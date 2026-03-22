from __future__ import annotations

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
    area: str = "Ciutat i institucions"
    summary: str = ""
    source: str = ""

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
            area=d.get("area") or "Ciutat i institucions",
            summary=d.get("summary") or "",
            source=d.get("source") or "",
        )


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
