from __future__ import annotations

import logging
from typing import List

import requests

logger = logging.getLogger(__name__)

TELEGRAM_MAX = 3900


def chunk_text(text: str, max_len: int) -> List[str]:
    """Talla el text preferint salts de paràgraf (\\n\\n) per no partir entrades del digest."""
    text = text.strip()
    if len(text) <= max_len:
        return [text]
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    out: List[str] = []
    buf: List[str] = []
    cur = 0
    for b in blocks:
        sep = "\n\n" if buf else ""
        add = len(sep) + len(b)
        if buf and cur + add > max_len:
            out.append("\n\n".join(buf))
            buf = [b]
            cur = len(b)
            continue
        if not buf:
            buf = [b]
            cur = len(b)
            continue
        if cur + add > max_len:
            out.append("\n\n".join(buf))
            buf = [b]
            cur = len(b)
        else:
            buf.append(b)
            cur += add
    if buf:
        out.append("\n\n".join(buf))
    # Si un sol bloc supera max_len, es fa el tall clàssic per línies
    final: List[str] = []
    for chunk in out:
        if len(chunk) <= max_len:
            final.append(chunk)
            continue
        rest = chunk
        while rest:
            if len(rest) <= max_len:
                final.append(rest)
                break
            cut = rest.rfind("\n", 0, max_len)
            if cut < max_len // 2:
                cut = max_len
            final.append(rest[:cut].strip())
            rest = rest[cut:].strip()
    return final


def send_telegram_messages(token: str, chat_id: str, parts: List[str]) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for i, chunk in enumerate(parts):
        if not chunk.strip():
            continue
        payload = {
            "chat_id": chat_id,
            "text": chunk.strip(),
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        logger.info(
            "Telegram part %s/%s (%s chars)",
            i + 1,
            len(parts),
            len(chunk),
        )


def merge_for_telegram(sections: List[str], max_len: int = TELEGRAM_MAX - 150) -> List[str]:
    """Une seccions en blocs que respecten el límit de Telegram."""
    out: List[str] = []
    buf: List[str] = []
    cur = 0
    for s in sections:
        s = s.strip()
        if not s:
            continue
        sep = "\n\n" if buf else ""
        add_len = len(sep) + len(s)
        if buf and cur + add_len > max_len:
            out.append("\n\n".join(buf))
            buf = [s]
            cur = len(s)
        else:
            if buf:
                cur += len(sep) + len(s)
                buf.append(s)
            else:
                buf = [s]
                cur = len(s)
    if buf:
        out.append("\n\n".join(buf))
    return out
