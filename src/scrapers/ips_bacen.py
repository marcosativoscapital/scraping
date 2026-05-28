"""Scraper das Instituições de Pagamento autorizadas pelo Bacen."""

from __future__ import annotations

import logging
from typing import Any

from .base import BaseScraper

logger = logging.getLogger(__name__)


class IPsBacenScraper(BaseScraper):
    """Coleta a lista de IPs autorizadas pelo Banco Central.

    Fonte: https://www.bcb.gov.br/estabilidadefinanceira/relacaoinstituicoes
    """

    vertical = "pagamentos"
    nome = "Bacen — Relação de Instituições de Pagamento"
    fonte_url = "https://www.bcb.gov.br/estabilidadefinanceira/relacaoinstituicoes"

    def scrape(self, limit: int | None = None) -> list[dict[str, Any]]:
        logger.info("Coletando IPs do Bacen...")
        html = self.fetch_html(self.fonte_url, wait_for="table, .relacao-instituicoes")
        self.save_raw(html, "bacen_lista.html")

        return [
            {
                "_tipo": "raw_html",
                "_html": html,
                "_fonte": self.fonte_url,
                "_vertical": self.vertical,
            }
        ]
