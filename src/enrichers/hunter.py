"""Enriquecimento de e-mails via Hunter.io (opcional)."""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

HUNTER_BASE = "https://api.hunter.io/v2"


def find_email(domain: str, first_name: str | None = None, last_name: str | None = None) -> dict[str, Any] | None:
    """Busca e-mail por domínio. Se nome for fornecido, faz email-finder.

    Requer HUNTER_API_KEY no .env. Sem chave, retorna None silenciosamente.
    """
    api_key = os.environ.get("HUNTER_API_KEY")
    if not api_key:
        return None

    try:
        if first_name and last_name:
            r = requests.get(
                f"{HUNTER_BASE}/email-finder",
                params={
                    "domain": domain,
                    "first_name": first_name,
                    "last_name": last_name,
                    "api_key": api_key,
                },
                timeout=10,
            )
        else:
            r = requests.get(
                f"{HUNTER_BASE}/domain-search",
                params={"domain": domain, "api_key": api_key, "limit": 5},
                timeout=10,
            )

        if r.status_code == 200:
            return r.json().get("data")
        logger.warning("Hunter %d para %s", r.status_code, domain)
    except Exception as e:
        logger.error("Erro Hunter: %s", e)
    return None


def domain_from_site(site: str | None) -> str | None:
    """Extrai domínio de uma URL."""
    if not site:
        return None
    site = site.replace("https://", "").replace("http://", "").replace("www.", "")
    return site.split("/")[0]
