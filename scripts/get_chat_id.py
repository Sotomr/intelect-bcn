#!/usr/bin/env python3
"""
Obté el TELEGRAM_CHAT_ID escrivint al teu bot (no cal userinfobot ni el navegador).

Ús:
  cd /Users/ferransoto/intelect-bcn
  export TELEGRAM_BOT_TOKEN="el_token_de_BotFather"
  python3 scripts/get_chat_id.py

Després obre Telegram i escriu qualsevol cosa al TEU bot (el que vas crear amb BotFather).
En uns segons veuràs el chat_id aquí.
"""

from __future__ import annotations

import os
import sys
import time

try:
    import requests
except ImportError:
    print("Instal·la requests: pip install requests")
    sys.exit(1)


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("Define TELEGRAM_BOT_TOKEN amb el token de BotFather, exemple:")
        print('  export TELEGRAM_BOT_TOKEN="123456:ABC..."')
        sys.exit(1)

    base = f"https://api.telegram.org/bot{token}"
    print("Esperant un missatge al teu bot…")
    print("→ Obre Telegram i escriu qualsevol cosa al TEU bot (no a @BotFather).\n")

    try:
        requests.get(f"{base}/deleteWebhook", timeout=10)
    except Exception:
        pass

    for _ in range(12):
        try:
            r = requests.get(
                f"{base}/getUpdates",
                params={"timeout": 50},
                timeout=60,
            )
            r.raise_for_status()
            data = r.json()
            if not data.get("ok"):
                print("Error API:", data)
                break
            for u in data.get("result") or []:
                msg = u.get("message") or u.get("edited_message")
                if not msg:
                    continue
                chat = msg.get("chat") or {}
                cid = chat.get("id")
                typ = chat.get("type")
                if cid is not None:
                    print("\n✅ El teu TELEGRAM_CHAT_ID és:\n")
                    print(f"   {cid}")
                    print(f"\n   (tipus de xat: {typ})\n")
                    print("Copia’l a GitHub → Settings → Secrets → TELEGRAM_CHAT_ID\n")
                    print("o al fitxer .env local.\n")
                    return
        except requests.RequestException as e:
            print("Error de xarxa:", e)
            time.sleep(2)
        time.sleep(1)

    print("\nNo ha arribat cap missatge. Comprova:")
    print("  - Que escrius al bot que correspon AQUEST token (no un altre bot).")
    print("  - Que has enviat /start o un missatge al xat amb el bot.")
    print("  - Si és un grup: afegeix el bot al grup i escriu al grup.")
    sys.exit(1)


if __name__ == "__main__":
    main()
