from __future__ import annotations

import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; intelect-bcn/1.0; +https://github.com/) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ca-ES,ca;q=0.9,es;q=0.8,en;q=0.7",
}


def _timeout_tuple() -> tuple[float, float]:
    """(connect, read) en segons; el calendari CCCB pot tardar en pic de càrrega."""
    raw = (os.getenv("HTTP_READ_TIMEOUT") or "").strip()
    if raw.isdigit():
        read_s = float(raw)
    else:
        read_s = 120.0
    return (20.0, read_s)


def fetch_text(
    url: str,
    timeout: float | tuple[float, float] | None = None,
    *,
    max_attempts: int = 3,
) -> str:
    """
    GET amb reintents (timeouts i errors de xarrega puntuals, p. ex. GitHub Actions).
    """
    if timeout is None:
        timeout = _timeout_tuple()
    last_err: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            r = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
            return r.text
        except requests.RequestException as e:
            last_err = e
            logger.warning(
                "GET %s falla (intent %s/%s): %s",
                url[:80],
                attempt,
                max_attempts,
                e,
            )
            if attempt < max_attempts:
                time.sleep(2.0 * attempt)
    assert last_err is not None
    raise last_err
