from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from intellect_filters import is_noise_title_intellect  # noqa: E402


def test_noise_da_cinema_festival():
    assert is_noise_title_intellect("D'A - Festival de Cinema de Barcelona 2026")
    assert is_noise_title_intellect("Festival de Cinema de Barcelona 2026 · títol")


def test_noise_not_other_festivals():
    assert not is_noise_title_intellect("Debat sobre democràcia en temps de festival")
    assert not is_noise_title_intellect("Simfonies de ciutat — estrena")
