# Fonts: estat al codi

El llistat complet i l’estat de cada font està definit a `src/source_catalog.py` (una sola font de veritat).

## Resum

- **Integrades (scraping / CSV / llistat):** Guia Barcelona (CSV), CCCB, CIDOB, Gencat (stub buit fins tenir API).
- **RSS (feed públic):** dues capes a `src/scrapers/rss_feeds.py`: **institucional** (agenda / cultura pròpia) i **mitjà** (premsa; barreja notícies i actes). Per defecte el pipeline només consumeix la capa institucional (`RSS_FEED_SET=institutional`). Per incloure Ara, Betevé, Directa, etc.: `RSS_FEED_SET=all`. Valors: `institutional`, `all`, `media`.
- **Pendent:** la resta del catàleg (CaixaForum, CosmoCaixa, Miró, Santa Mònica, KBr, UB Filosofia, BNC agenda, La Central, Laie, ICCUB, ICE, ICFO, UPF, UPC, Biennal, Barcelona Pensa, etc.) — sovint per Cloudflare, falta d’RSS estable, o calendari només a la web.

**Candidats següents (millor esforç / rendiment):** agenda **ICCUB** (`icc.ub.edu/events`, sense RSS; cal scraper o ICS si el publiquen), **Laboratori CCCB** (feed WordPress intermitent), **blog BNC** (subdomini variable), **MNAC / Palau Música** (sense `/feed/` estable). Prioritat: qualsevol **ICS públic** o **RSS WordPress** verificat abans que HTML.

Variables: `RSS_ENABLED`, `RSS_MAX_PER_FEED`, `RSS_FEED_SET` (veure `.env.example`).

Per veure el resum per estat des del codi: `python -c "from source_catalog import resum_per_estat; print(resum_per_estat())"` (des de `src/` al `PYTHONPATH`).
