"""Scraper de empresas de recuperação de crédito do oHub."""

from __future__ import annotations

import logging
from typing import Any

from .base import BaseScraper

logger = logging.getLogger(__name__)


class CobrancaOHubScraper(BaseScraper):
    """Coleta empresas de recuperação de crédito do diretório oHub.

    Fonte: https://www.ohub.com.br/empresas/recuperacao-de-credito
    """

    vertical = "cobranca"
    nome = "oHub — Recuperação de Crédito"
    fonte_url = "https://www.ohub.com.br/empresas/recuperacao-de-credito"

    def scrape(self, limit: int | None = None) -> list[dict[str, Any]]:
        logger.info("Coletando empresas de cobrança do oHub...")
        html = self.fetch_html(self.fonte_url, wait_for="body")
        self.save_raw(html, "ohub_lista.html")

        return [
            {
                "_tipo": "raw_html",
                "_html": html,
                "_fonte": self.fonte_url,
                "_vertical": self.vertical,
            }
        ]
