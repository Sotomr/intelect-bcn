from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scrapers.guia_barcelona import (  # noqa: E402
    _digest_intellect_summary,
    _normalize_csv_keys,
)


def test_digest_intellect_summary_includes_csv_filters():
    """El digest filtra amb title+summary; ha de rebre els mateixos filtres que el scrape CSV."""
    s = _digest_intellect_summary("Taller de prova", "Cultura / Filosofia")
    assert "Filosofia" in s
    assert _digest_intellect_summary("Sols títol", "").strip()


def test_normalize_csv_row_strips_bom_from_keys():
    raw = {"\ufeffname": "Conferència prova", "register_id": "123"}
    row = _normalize_csv_keys(raw)
    assert row["name"] == "Conferència prova"
    assert row.get("register_id") == "123"
