"""
Catàleg de totes les fonts previstes (ETSO). L’estat indica si ja entren al pipeline.

Integrades = scraper o RSS actiu al repo.
Pendent = cal API, HTML fràgil, Cloudflare, o integració manual.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EstatFont(str, Enum):
    integrada = "integrada"
    rss = "rss"
    pendent = "pendent"


@dataclass(frozen=True)
class Font:
    id: str
    nom: str
    estat: EstatFont
    nota: str = ""


FONTS: tuple[Font, ...] = (
    Font("guia_bcn", "Guia Barcelona (Open Data CSV)", EstatFont.integrada, "Dataset oficial agenda"),
    Font("gencat", "Agenda Cultural de la Generalitat", EstatFont.pendent, "AEM; cal API o export estable"),
    Font("cccb", "CCCB", EstatFont.integrada, "Calendari web"),
    Font("ateneu", "Ateneu Barcelonès", EstatFont.rss, "Feed WordPress + filtre intel·lectual"),
    Font("hangar", "Hangar", EstatFont.rss, "Feed WordPress (sense filtre d’entrades; producció/recerca artística)"),
    Font("macaya", "Palau Macaya / Recercaixa", EstatFont.pendent, "Cal scraper o calendari dedicat"),
    Font("caixaforum", "CaixaForum Barcelona", EstatFont.pendent, "Cloudflare / front dinàmic"),
    Font("cosmocaixa", "CosmoCaixa", EstatFont.pendent, "Cloudflare"),
    Font("macba", "MACBA", EstatFont.rss, "Feed WordPress + filtre"),
    Font("mies", "Fundació Mies van der Rohe", EstatFont.rss, "Feed WordPress (arquitectura; pot ser buit)"),
    Font("miro", "Fundació Joan Miró", EstatFont.pendent, "Sense feed estable al web actual"),
    Font("santa_monica", "Arts Santa Mònica", EstatFont.pendent, "SSL/bot; cal revisar"),
    Font("kbr", "KBr / Fundació MAPFRE", EstatFont.pendent, "Cal feed o agenda"),
    Font("cidob", "CIDOB", EstatFont.integrada, "Llistat activitats"),
    Font("ub_filosofia", "Facultat de Filosofia UB", EstatFont.pendent, "Liferay; cal ICS o API"),
    Font("bcn_pensa", "Barcelona Pensa", EstatFont.pendent, "Temporada; cal dates d’edició"),
    Font("iec", "Institut d’Estudis Catalans", EstatFont.rss, "Feed WordPress"),
    Font("bnc", "Biblioteca de Catalunya", EstatFont.pendent, "Cal agenda web o ICS"),
    Font("la_central", "Llibreria La Central", EstatFont.pendent, "Cal agenda / events"),
    Font("laie", "Llibreria Laie", EstatFont.pendent, "Cal agenda / events"),
    Font("iccub", "ICCUB (UB)", EstatFont.pendent, "Cal agenda seminaris"),
    Font("ice_csic", "ICE-CSIC", EstatFont.pendent, "Cal agenda / RSS si existeix"),
    Font("icfo", "ICFO", EstatFont.pendent, "Bot-lockout / cal alternativa"),
    Font("scm", "Societat Catalana de Matemàtiques", EstatFont.rss, "Feed IEC"),
    Font("upf", "UPF (agenda)", EstatFont.pendent, "Cloudflare"),
    Font("upc", "UPC / FIB / FME", EstatFont.pendent, "Portal esdeveniments"),
    Font("biennal", "Biennal Ciutat i Ciència", EstatFont.pendent, "Temporada"),
)


def resum_per_estat() -> str:
    lines = []
    for e in EstatFont:
        ids = [f.nom for f in FONTS if f.estat == e]
        lines.append(f"{e.value}: {len(ids)} — {', '.join(ids[:6])}{'…' if len(ids) > 6 else ''}")
    return "\n".join(lines)
