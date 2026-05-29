"""Scraper das bets autorizadas pela SPA/MF (Secretaria de Prêmios e Apostas / Ministério da Fazenda).

Fonte primária: gov.br/fazenda (bloqueia scraping com 403)
Fonte de mirror: lance.com.br (mantém a lista oficial atualizada em formato indexável)

A lista das ~188 empresas autorizadas é a mesma — apenas a fonte de coleta muda.
"""

from __future__ import annotations

import logging
from typing import Any

from .base import BaseScraper

logger = logging.getLogger(__name__)


class BetsSPAMFScraper(BaseScraper):
    """Coleta a lista oficial de bets autorizadas no Brasil.

    Estratégia:
    1. Tenta gov.br/fazenda direto
    2. Se 403/falha, usa mirror lance.com.br
    """

    vertical = "betting"
    nome = "SPA/MF — Empresas Autorizadas (via Lance.com.br mirror)"
    fonte_oficial = "https://www.gov.br/fazenda/pt-br/assuntos/secretaria-de-premios-e-apostas/empresas-autorizadas"
    fonte_mirror = "https://www.lance.com.br/sites-de-apostas/bets-autorizadas.html"
    fonte_url = fonte_mirror  # exposto como fonte declarada

    def scrape(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Baixa a página, salva raw e retorna HTML para o parser tratar."""
        logger.info("Coletando bets autorizadas (mirror Lance)...")

        # Tenta o mirror que sabemos funcionar
        try:
            html = self.fetch_html(self.fonte_mirror)
            self.save_raw(html, "spa_mf_lista.html")
            return [
                {
                    "_tipo": "raw_html",
                    "_html": html,
                    "_fonte": self.fonte_oficial,  # referenciamos a fonte oficial para auditoria
                    "_fonte_coleta": self.fonte_mirror,
                    "_vertical": self.vertical,
                }
            ]
        except Exception as e:
            logger.warning("Mirror lance falhou: %s. Tentando fonte oficial...", e)

        # Fallback: fonte oficial (geralmente 403, mas tenta)
        html = self.fetch_html(self.fonte_oficial)
        self.save_raw(html, "spa_mf_lista_oficial.html")
        return [
            {
                "_tipo": "raw_html",
                "_html": html,
                "_fonte": self.fonte_oficial,
                "_fonte_coleta": self.fonte_oficial,
                "_vertical": self.vertical,
            }
        ]
