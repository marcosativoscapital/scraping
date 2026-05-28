"""Enriquecimento via BrasilAPI — busca CNPJ, razão social, capital, porte."""

from __future__ import annotations

import logging
import re
from typing import Any

import requests

logger = logging.getLogger(__name__)

BRASIL_API_BASE = "https://brasilapi.com.br/api/cnpj/v1"


def normalize_cnpj(cnpj: str) -> str:
    """Remove caracteres não-numéricos."""
    return re.sub(r"\D", "", cnpj or "")


def format_cnpj(cnpj: str) -> str:
    """Formata como XX.XXX.XXX/XXXX-XX."""
    c = normalize_cnpj(cnpj)
    if len(c) != 14:
        return cnpj
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"


def fetch_cnpj(cnpj: str) -> dict[str, Any] | None:
    """Consulta BrasilAPI e retorna dados da empresa."""
    cnpj_clean = normalize_cnpj(cnpj)
    if len(cnpj_clean) != 14:
        return None

    try:
        r = requests.get(f"{BRASIL_API_BASE}/{cnpj_clean}", timeout=10)
        if r.status_code == 200:
            return r.json()
        logger.warning("BrasilAPI %d para CNPJ %s", r.status_code, cnpj_clean)
    except Exception as e:
        logger.error("Erro na BrasilAPI: %s", e)
    return None


def enrich_with_cnpj(lead: dict[str, Any]) -> dict[str, Any]:
    """Enriquece um lead com dados do CNPJ via BrasilAPI."""
    cnpj = lead.get("cnpj")
    if not cnpj:
        return lead

    data = fetch_cnpj(cnpj)
    if not data:
        return lead

    lead["razao_social"] = data.get("razao_social") or lead.get("razao_social")
    lead["porte_estimado"] = _map_porte(data.get("porte"))
    lead["capital_social"] = data.get("capital_social")
    lead["uf"] = data.get("uf")
    lead["municipio"] = data.get("municipio")
    lead["atividade_principal"] = data.get("cnae_fiscal_descricao")
    lead["cnpj"] = format_cnpj(cnpj)
    return lead


def _map_porte(porte: str | None) -> str:
    if not porte:
        return "desconhecido"
    p = porte.upper()
    if "MEI" in p or "MICRO" in p:
        return "pequena"
    if "PEQUENO" in p or "EPP" in p:
        return "pequena"
    if "MÉDIO" in p or "MEDIO" in p:
        return "media"
    if "GRANDE" in p or "DEMAIS" in p:
        return "grande"
    return "media"
