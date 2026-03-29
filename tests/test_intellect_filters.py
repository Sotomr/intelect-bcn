from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from intellect_filters import (  # noqa: E402
    is_noise_title_intellect,
    text_matches_intellect_blob,
)


def test_noise_da_cinema_festival():
    assert is_noise_title_intellect("D'A - Festival de Cinema de Barcelona 2026")
    assert is_noise_title_intellect("Festival de Cinema de Barcelona 2026 · títol")


def test_noise_not_other_festivals():
    assert not is_noise_title_intellect("Debat sobre democràcia en temps de festival")
    assert not is_noise_title_intellect("Simfonies de ciutat — estrena")


def test_taula_rodona_requires_topic_or_strong():
    assert not text_matches_intellect_blob('Taula rodona: Presentació del fanzín "Oh!"', "")
    assert text_matches_intellect_blob("Taula rodona: drets humans i migracions", "")


def test_noise_taula_rodona_fanzin_combo():
    assert is_noise_title_intellect("Taula rodona: fanzín col·lectiu")


def test_noise_taller_mobles_maqueta():
    assert is_noise_title_intellect("Taller 'Mobles grans, arquitectures petites'")
    assert is_noise_title_intellect("Taller de maquetes urbanes")
