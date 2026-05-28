"""Scraper de LinkedIn — para uso COM a extensão Chrome.

A extensão captura os dados visíveis no Sales Navigator e envia para este endpoint,
que enriquece e qualifica via Claude.

IMPORTANTE: nunca fazemos scraping direto do LinkedIn pelo servidor (viola ToS).
O usuário navega normalmente no Sales Nav e a extensão coleta o que está na tela.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def parse_linkedin_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Normaliza dados vindos do content script da extensão Chrome.

    Esperado:
    {
      "source": "linkedin_sales_nav" | "linkedin_search" | "linkedin_company",
      "url": "https://...",
      "items": [
        { "nome": "...", "cargo": "...", "empresa": "...", "url": "..." },
        ...
      ]
    }
    """
    items = payload.get("items", [])
    source = payload.get("source", "linkedin")
    fonte_url = payload.get("url", "")

    return [
        {
            "decisor_nome": item.get("nome"),
            "decisor_cargo": item.get("cargo"),
            "empresa": item.get("empresa"),
            "decisor_linkedin": item.get("url"),
            "fonte": source,
            "fonte_url": fonte_url,
        }
        for item in items
    ]
