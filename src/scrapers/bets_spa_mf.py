"""Scraper das bets autorizadas pela SPA/MF (Secretaria de Prêmios e Apostas / Ministério da Fazenda)."""

from __future__ import annotations

import logging
from typing import Any

from .base import BaseScraper

logger = logging.getLogger(__name__)


class BetsSPAMFScraper(BaseScraper):
    """Coleta a lista oficial de bets autorizadas no Brasil.

    Fonte: https://www.gov.br/fazenda/pt-br/assuntos/secretaria-de-premios-e-apostas

    A página oficial atualiza periodicamente com a lista de empresas. O scraping é
    feito em duas etapas:
    1. Baixa o HTML renderizado
    2. Envia para Claude parser extrair as ~188 empresas
    """

    vertical = "betting"
    nome = "SPA/MF — Empresas Autorizadas"
    fonte_url = "https://www.gov.br/fazenda/pt-br/assuntos/secretaria-de-premios-e-apostas/empresas-autorizadas"

    def scrape(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Baixa a página, salva raw e retorna HTML para o parser tratar."""
        logger.info("Coletando bets da fonte SPA/MF...")
        html = self.fetch_html(self.fonte_url, wait_for="table, .conteudo")
        self.save_raw(html, "spa_mf_lista.html")

        # Retorna registro único contendo HTML para o pipeline parsear via Claude
        return [
            {
                "_tipo": "raw_html",
                "_html": html,
                "_fonte": self.fonte_url,
                "_vertical": self.vertical,
            }
        ]
