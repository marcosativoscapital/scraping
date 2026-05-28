"""Scraper de SaaS B2B/B2B2C da ABStartups."""

from __future__ import annotations

import logging
from typing import Any

from .base import BaseScraper

logger = logging.getLogger(__name__)


class SaaSABStartupsScraper(BaseScraper):
    """Coleta startups SaaS B2B do mapeamento ABStartups.

    Fonte: https://abstartups.com.br/brasil/
    """

    vertical = "saas_b2b"
    nome = "ABStartups — Mapeamento"
    fonte_url = "https://abstartups.com.br/brasil/"

    def scrape(self, limit: int | None = None) -> list[dict[str, Any]]:
        logger.info("Coletando SaaS B2B da ABStartups...")
        html = self.fetch_html(self.fonte_url, wait_for="body")
        self.save_raw(html, "abstartups_lista.html")

        return [
            {
                "_tipo": "raw_html",
                "_html": html,
                "_fonte": self.fonte_url,
                "_vertical": self.vertical,
            }
        ]
