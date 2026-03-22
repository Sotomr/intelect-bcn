"""
Punt d'entrada únic: python main.py [--mode ingest|digest|full]

- ingest: recull candidats, valida, enriqueix, guarda (job diari)
- digest: carrega candidats, selecciona, genera digest, envia Telegram (job setmanal)
- full: fa ingest + digest seguit (comportament per defecte, compatibilitat)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("intelect_bcn")


def main() -> int:
    parser = argparse.ArgumentParser(description="Intelect BCN")
    parser.add_argument(
        "--mode",
        choices=["ingest", "digest", "full"],
        default="full",
        help="Mode d'execució: ingest (diari), digest (setmanal), full (tot)",
    )
    args = parser.parse_args()

    if args.mode == "ingest":
        from ingest import run_ingest
        return run_ingest()

    if args.mode == "digest":
        from digest_job import run_digest
        return run_digest()

    # full: ingest + digest
    from ingest import run_ingest
    from digest_job import run_digest
    rc = run_ingest()
    if rc != 0:
        return rc
    return run_digest()


if __name__ == "__main__":
    raise SystemExit(main())
