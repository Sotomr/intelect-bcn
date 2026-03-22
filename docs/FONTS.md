# Fonts: estat al codi

El llistat complet i l’estat de cada font està definit a `src/source_catalog.py` (una sola font de veritat).

## Resum

- **Integrades (scraping / CSV / llistat):** Guia Barcelona (CSV), CCCB, CIDOB, Gencat (stub buit fins tenir API).
- **RSS (feed públic):** IEC, SCM, MACBA, Ateneu Barcelonès, Hangar, Fundació Mies van der Rohe, Col·legi d’Enginyers de Barcelona — veure `src/scrapers/rss_feeds.py` (`RSS_FEEDS`). Es poden afegir més URLs aquí quan es validin.
- **Pendent:** la resta del catàleg (CaixaForum, CosmoCaixa, Miró, Santa Mònica, KBr, UB Filosofia, BNC agenda, La Central, Laie, ICCUB, ICE, ICFO, UPF, UPC, Biennal, Barcelona Pensa, etc.) — sovint per Cloudflare, falta d’RSS estable, o calendari només a la web.

**Candidats següents (millor esforç / rendiment):** agenda **ICCUB** (`icc.ub.edu/events`, sense RSS; cal scraper o ICS si el publiquen), **Laboratori CCCB** (feed WordPress intermitent), **blog BNC** (subdomini variable), **MNAC / Palau Música** (sense `/feed/` estable). Prioritat: qualsevol **ICS públic** o **RSS WordPress** verificat abans que HTML.

Variables: `RSS_ENABLED`, `RSS_MAX_PER_FEED` (veure `.env.example`).

Per veure el resum per estat des del codi: `python -c "from source_catalog import resum_per_estat; print(resum_per_estat())"` (des de `src/` al `PYTHONPATH`).
