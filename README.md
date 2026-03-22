# intelect-bcn

Bot en Python que recull esdeveniments amb densitat intel·lectual a Barcelona (conferències, debats, geopolítica, cultura), en genera un **digest setmanal** en català (**agrupat per temes**, resum curt, enllaç oficial i **font** de cada línia) i l’envia per **Telegram** (fonts → filtre de soroll → deduplicació → digest HTML → `sendMessage`).

## Objectiu vs cobertura actual

| Objectiu | Estat |
|----------|--------|
| **Vàries fonts**, no una sola institució | Integrades: **Guia** (CSV), **CCCB**, **CIDOB**, **7 RSS** (IEC, SCM, MACBA, Ateneu, Hangar, Mies, Enginyers BCN). **Gencat** preparat però buit (sense API). |
| **Llegible per temes** (filosofia, política, ciència…) | El digest va per **àmbit** (`classify_area`), barrejant fonts; cada línia indica **pipeline** (`Guia BCN`, `CCCB`, `RSS·…`). |
| **Menys soroll** (cinema repetit, etc.) | Filtre per títols tipus **D’A / Festival de Cinema de Barcelona**; mateix acte diversos dies **agrupat** en un interval. |
| **Robustesa** (xarxa, CSV gran) | HTTP: **reintents** i timeout de lectura configurable (`HTTP_READ_TIMEOUT`). Guia: **reintents** i UTF-16 amb fallback. |
| **Novetats** respecte a execucions anteriors | Registre `seen_event_keys.json` + bloc opcional **Novetats al radar**. |
| **Tot el catàleg ETSO** (totes les sales de la llista) | **No** automàtic: moltes depenen de RSS/ICS inexistents o webs protegides; es van afegint fonts vàlides (`RSS_FEEDS`, `source_catalog`). |

**Millores típiques:** afegir URLs a `RSS_FEEDS`, pujar `MAX_BASE_EVENTS` si vols més Guia, o integrar un **ICS** quan una institució el publiqui.

## Fonts integrades ara

| Tipus | Fonts |
|--------|--------|
| **Dades obertes + scraping** | **Guia Barcelona** (CSV Open Data), **CCCB**, **CIDOB** |
| **RSS** (configurable) | **IEC**, **SCM**, **MACBA**, **Ateneu**, **Hangar**, **Mies**, **Col·legi d’Enginyers BCN** — llista editable a `src/scrapers/rss_feeds.py` |
| **Stub** | **Agenda Cultural Gencat** (fins tenir API o export) |

El **catàleg complet** de totes les fonts previstes (ETSO) i el seu estat (`integrada` / `rss` / `pendent`) és a **`src/source_catalog.py`**. Les que encara no entren al pipeline solen ser per Cloudflare, falta de feed estable o web només amb calendari visual.

El digest va **per temes** (filosofia, política, ciència…), barrejant totes les fonts; cada línia indica el pipeline (`Guia BCN`, `CCCB`, `RSS·iec`, etc.).

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

Variables útils: `WINDOW_DAYS`, `MAX_EVENTS_PER_INSTITUTION`, `MAX_BASE_EVENTS`, `APPEND_NOVELTIES`, `RSS_ENABLED`, `RSS_MAX_PER_FEED`, `HTTP_READ_TIMEOUT`, `GUIA_CSV_URL`, `CCCB_CALENDAR_URL`, `CIDOB_ACTIVITIES_URL`.

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
