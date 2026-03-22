from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scrapers.guia_barcelona import _normalize_csv_keys  # noqa: E402


def test_normalize_csv_row_strips_bom_from_keys():
    raw = {"\ufeffname": "Conferència prova", "register_id": "123"}
    row = _normalize_csv_keys(raw)
    assert row["name"] == "Conferència prova"
    assert row.get("register_id") == "123"
