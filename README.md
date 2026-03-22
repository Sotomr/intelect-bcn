# intelect-bcn

Bot en Python que recull esdeveniments amb densitat intel·lectual a Barcelona (conferències, debats, geopolítica, cultura), en genera un **digest setmanal** en català (agrupat per capes i àmbits, amb resum curt i enllaç oficial) i l’envia per **Telegram** (mateix patró que `cinema-alert`: fonts → deduplicació → digest HTML → `sendMessage`).

## Fonts integrades ara

| Tipus | Fonts |
|--------|--------|
| **Dades obertes + scraping** | **Guia Barcelona** (CSV Open Data), **CCCB**, **CIDOB** |
| **RSS** (configurable) | **IEC**, **SCM**, **MACBA**, **Ateneu**, **Hangar**, **Mies** — llista editable a `src/scrapers/rss_feeds.py` |
| **Stub** | **Agenda Cultural Gencat** (fins tenir API o export) |

El **catàleg complet** de totes les fonts previstes (ETSO) i el seu estat (`integrada` / `rss` / `pendent`) és a **`src/source_catalog.py`**. Les que encara no entren al pipeline solen ser per Cloudflare, falta de feed estable o web només amb calendari visual.

Capes al missatge (ordre al Telegram): **nerd** (RSS) → **base** (Guia, altres sales) → **premium** (CCCB, MACBA…), perquè no quedi tot el primer missatge només amb CCCB.

Documentació: `docs/FONTS.md`, preferències IA: `docs/AI_CONTEXT.md`.

Pots afegir URLs a `RSS_FEEDS` o nous mòduls a `src/scrapers/` i registrar-los a `src/main.py`.

## Ús local

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # només variables locals (no es puja al repo)
python src/main.py
```

El **chat id** no va al codi: el poses al `.env` o als secrets de GitHub. Per obtenir-lo **només des de Telegram**: obre [@userinfobot](https://t.me/userinfobot) i copia el número que et mostra (xat privat amb tu). Abans envia `/start` al teu bot. Opcional: `scripts/get_chat_id.py` si prefereixes que surti el id en terminal després d’escriure al bot.

Prova sense enviar res:

```bash
DRY_RUN=1 python src/main.py
```

Variables útils: `WINDOW_DAYS`, `MAX_EVENTS_PER_INSTITUTION`, `MAX_BASE_EVENTS`, `APPEND_NOVELTIES`, `RSS_ENABLED`, `RSS_MAX_PER_FEED`, `GUIA_CSV_URL`, `CCCB_CALENDAR_URL`, `CIDOB_ACTIVITIES_URL`.

## GitHub Actions

El workflow `.github/workflows/intelect-bcn.yml` executa el digest **cada dilluns** (UTC 09:00; ajustable) i fa commit de:

- `data/latest_snapshot.json` — última finestra d’esdeveniments enviada
- `data/seen_event_keys.json` — registre de sessions **ja vistes** (per calcular **novetats** de veritat: només apareixen actes nous respecte a execucions anteriors, encara que canviï la setmana del calendari)

Pots executar-lo manualment (`workflow_dispatch`) o canviar el `cron` a diari si vols avisos més sovint.

Configura els secrets `TELEGRAM_BOT_TOKEN` i `TELEGRAM_CHAT_ID`.

## Tests

```bash
pytest tests/
```
