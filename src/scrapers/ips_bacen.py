"""Scraper das Instituições de Pagamento autorizadas pelo Bacen."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests

from .base import BaseScraper

logger = logging.getLogger(__name__)


class IPsBacenScraper(BaseScraper):
    """Coleta a lista de IPs autorizadas pelo Banco Central.

    Estratégias (na ordem):
    1. API pública IFData do Bacen (mais confiável, JSON direto)
    2. Fallback: scraping da SPA com tempo extra para hidratar JS
    """

    vertical = "pagamentos"
    nome = "Bacen — Relação de Instituições de Pagamento"
    fonte_url = "https://www.bcb.gov.br/estabilidadefinanceira/relacaoinstituicoes"
    api_url = "https://olinda.bcb.gov.br/olinda/servico/Instituicoes_em_funcionamento/versao/v1/odata/SedesSociedades"

    def scrape(self, limit: int | None = None) -> list[dict[str, Any]]:
        logger.info("Coletando IPs do Bacen...")

        # 1) Tenta API pública Olinda (Bacen Open Data)
        try:
            data = self._fetch_via_api(limit)
            if data:
                logger.info("Bacen Olinda API: %d empresas", len(data))
                return [{
                    "_tipo": "json_direto",
                    "_empresas": data,
                    "_fonte": self.fonte_url,
                    "_fonte_coleta": "olinda.bcb.gov.br",
                    "_vertical": self.vertical,
                }]
        except Exception as e:
            logger.warning("API Olinda falhou: %s. Caindo pro scraping HTML...", e)

        # 2) Fallback: scraping com SPA wait
        html = self.fetch_html(self.fonte_url, spa_wait_ms=8000)
        self.save_raw(html, "bacen_lista.html")
        return [{
            "_tipo": "raw_html",
            "_html": html,
            "_fonte": self.fonte_url,
            "_vertical": self.vertical,
        }]

    def _fetch_via_api(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Consulta a API Olinda do Bacen — Instituições de Pagamento autorizadas."""
        params = {
            "$format": "json",
            "$filter": "contains(SEGMENTO,'Pagamento')",
            "$top": str(limit or 250),
        }
        r = requests.get(self.api_url, params=params, timeout=20)
        r.raise_for_status()
        rows = r.json().get("value", [])

        empresas = []
        for row in rows:
            cnpj_raw = str(row.get("CNPJ", "")).strip()
            site = (row.get("SITIO_NA_INTERNET") or "").strip().lower()
            if site and not site.startswith("http"):
                site = f"https://{site}"
            # A API do Bacen retorna só a raiz do CNPJ (8 dígitos). Mostramos como XX.XXX.XXX/XXXX-XX
            # com placeholder no sufixo, ou só a raiz formatada se não houver dado completo.
            if len(cnpj_raw) == 8:
                cnpj_fmt = f"{cnpj_raw[:2]}.{cnpj_raw[2:5]}.{cnpj_raw[5:8]}/0001-XX"
            elif len(cnpj_raw) == 14:
                cnpj_fmt = f"{cnpj_raw[:2]}.{cnpj_raw[2:5]}.{cnpj_raw[5:8]}/{cnpj_raw[8:12]}-{cnpj_raw[12:]}"
            else:
                cnpj_fmt = None
            empresas.append({
                "empresa": (row.get("NOME_INSTITUICAO") or "").strip().title(),
                "razao_social": (row.get("NOME_INSTITUICAO") or "").strip(),
                "cnpj": cnpj_fmt,
                "cnpj_raiz": cnpj_raw if len(cnpj_raw) == 8 else None,
                "site": site or None,
                "email_provavel": (row.get("E_MAIL") or "").lower().strip() or None,
                "telefone": f"({row.get('DDD')}) {row.get('TELEFONE')}" if row.get("DDD") and row.get("TELEFONE") else None,
                "uf": row.get("UF"),
                "municipio": row.get("MUNICIPIO"),
                "segmento_bacen": row.get("SEGMENTO"),
                "status_licenca": "autorizado",
            })
        return empresas
