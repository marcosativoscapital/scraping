"""Scraper de SaaS B2B brasileiros.

A página institucional do ABStartups não tem lista direta. Usamos como fonte:
- Econodata "500 Maiores empresas de SaaS no Brasil" (HTML público)
- Fallback: ABStartups institucional (SPA com longa espera)
"""

from __future__ import annotations

import logging
from typing import Any

from .base import BaseScraper

logger = logging.getLogger(__name__)


class SaaSABStartupsScraper(BaseScraper):
    """Coleta SaaS B2B brasileiros."""

    vertical = "saas_b2b"
    nome = "SaaS B2B BR (via Econodata)"
    fonte_oficial = "https://abstartups.com.br/brasil/"
    fonte_econodata = "https://www.econodata.com.br/maiores-empresas/todo-brasil/saas"
    fonte_url = fonte_econodata

    def scrape(self, limit: int | None = None) -> list[dict[str, Any]]:
        logger.info("Coletando SaaS B2B...")
        try:
            html = self.fetch_html(self.fonte_econodata, spa_wait_ms=4000)
            self.save_raw(html, "econodata_saas.html")
            return [
                {
                    "_tipo": "raw_html",
                    "_html": html,
                    "_fonte": self.fonte_econodata,
                    "_fonte_coleta": "econodata.com.br",
                    "_vertical": self.vertical,
                }
            ]
        except Exception as e:
            logger.warning("Econodata falhou: %s. Caindo pro ABStartups SPA...", e)

        html = self.fetch_html(self.fonte_oficial, spa_wait_ms=8000)
        self.save_raw(html, "abstartups_lista.html")
        return [
            {
                "_tipo": "raw_html",
                "_html": html,
                "_fonte": self.fonte_oficial,
                "_vertical": self.vertical,
            }
        ]
