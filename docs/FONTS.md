# Fonts: estat al codi

El llistat complet i l’estat de cada font està definit a `src/source_catalog.py` (una sola font de veritat).

## Resum

- **Integrades (scraping / CSV / llistat):** Guia Barcelona (CSV), CCCB, CIDOB, Gencat (stub buit fins tenir API).
- **RSS (feed públic):** IEC, Societat Catalana de Matemàtiques (SCM), MACBA, Ateneu Barcelonès — veure `src/scrapers/rss_feeds.py` (`RSS_FEEDS`). Es poden afegir més URLs aquí quan es validin.
- **Pendent:** la resta del catàleg (CaixaForum, CosmoCaixa, Miró, Santa Mònica, Mies, KBr, UB Filosofia, BNC, La Central, Laie, ICCUB, ICE, ICFO, UPF, UPC, Biennal, Barcelona Pensa, etc.) — sovint per Cloudflare, falta d’RSS estable, o calendari només a la web.

Variables: `RSS_ENABLED`, `RSS_MAX_PER_FEED` (veure `.env.example`).

Per veure el resum per estat des del codi: `python -c "from source_catalog import resum_per_estat; print(resum_per_estat())"` (des de `src/` al `PYTHONPATH`).
