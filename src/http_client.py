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

# El CCCB sovint respon 504 (gateway saturat); es reintenta amb pausa.
_RETRY_STATUS = frozenset({429, 502, 503, 504})


def _timeout_tuple() -> tuple[float, float]:
    """(connect, read) en segons; el calendari CCCB pot tardar en pic de càrrega."""
    raw = (os.getenv("HTTP_READ_TIMEOUT") or "").strip()
    if raw.isdigit():
        read_s = float(raw)
    else:
        read_s = 120.0
    return (25.0, read_s)


def _max_http_attempts() -> int:
    v = (os.getenv("HTTP_MAX_ATTEMPTS") or "").strip()
    if v.isdigit():
        return max(1, min(12, int(v)))
    # Per defecte 4: equilibri entre 504 del CCCB i durada del job (6 intents + backoff llarg ≈ molts minuts)
    return 4


def _backoff_seconds(attempt: int, *, gateway: bool) -> float:
    """Pausa entre intents; gateway (504) abans era massa agressiu i allargava Actions diversos minuts."""
    if gateway:
        return min(8.0 * attempt, 35.0)
    return min(4.0 * attempt, 25.0)


def fetch_text(
    url: str,
    timeout: float | tuple[float, float] | None = None,
    *,
    max_attempts: int | None = None,
) -> str:
    """
    GET amb reintents: 504/502/503/429, timeouts i errors de connexió.
    Els 404 i altres 4xx no es reintanten (raise_for_status).
    """
    if timeout is None:
        timeout = _timeout_tuple()
    if max_attempts is None:
        max_attempts = _max_http_attempts()

    for attempt in range(1, max_attempts + 1):
        try:
            r = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
            if r.status_code in _RETRY_STATUS:
                gw = r.status_code in (502, 503, 504)
                logger.warning(
                    "GET %s → HTTP %s (intent %s/%s)",
                    url[:88],
                    r.status_code,
                    attempt,
                    max_attempts,
                )
                if attempt < max_attempts:
                    time.sleep(_backoff_seconds(attempt, gateway=gw))
                    continue
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
            return r.text
        except (requests.Timeout, requests.ConnectionError) as e:
            logger.warning(
                "GET %s falla (intent %s/%s): %s",
                url[:88],
                attempt,
                max_attempts,
                e,
            )
            if attempt < max_attempts:
                time.sleep(_backoff_seconds(attempt, gateway=False))
                continue
            raise
