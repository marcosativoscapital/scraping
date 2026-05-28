"""Monitor de mudanças regulatórias.

Compara a lista atual com o último snapshot armazenado e identifica:
- NOVAS empresas autorizadas
- empresas que SUMIRAM (licença suspensa)
- mudanças de status

Notifica via webhook Slack se houver mudança.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ..claude_agent.client import GeminiClient
from ..claude_agent.parser import extract_companies_from_html
from ..db.store import Store
from ..integrations.slack import notify_slack
from ..scrapers.base import BaseScraper
from ..scrapers.bets_spa_mf import BetsSPAMFScraper
from ..scrapers.cobranca_ohub import CobrancaOHubScraper
from ..scrapers.ips_bacen import IPsBacenScraper
from ..scrapers.saas_abstartups import SaaSABStartupsScraper

logger = logging.getLogger(__name__)


SCRAPERS_MONITOR: dict[str, type[BaseScraper]] = {
    "betting": BetsSPAMFScraper,
    "pagamentos": IPsBacenScraper,
    "cobranca": CobrancaOHubScraper,
    "saas_b2b": SaaSABStartupsScraper,
}


def _key(empresa: dict[str, Any]) -> str:
    """Chave de identidade para diff."""
    cnpj = (empresa.get("cnpj") or "").replace(".", "").replace("/", "").replace("-", "")
    if cnpj:
        return f"cnpj:{cnpj}"
    return f"nome:{(empresa.get('empresa') or '').lower().strip()}"


def diff_lists(previous: list[dict], current: list[dict]) -> dict[str, list[dict]]:
    """Calcula o que entrou, saiu e mudou de status entre dois snapshots."""
    prev_map = {_key(e): e for e in previous if _key(e)}
    curr_map = {_key(e): e for e in current if _key(e)}

    novas = [curr_map[k] for k in curr_map.keys() - prev_map.keys()]
    sumiram = [prev_map[k] for k in prev_map.keys() - curr_map.keys()]

    mudancas_status = []
    for k in curr_map.keys() & prev_map.keys():
        s_old = (prev_map[k].get("status_licenca") or "").lower()
        s_new = (curr_map[k].get("status_licenca") or "").lower()
        if s_old and s_new and s_old != s_new:
            mudancas_status.append(
                {
                    "empresa": curr_map[k].get("empresa"),
                    "cnpj": curr_map[k].get("cnpj"),
                    "status_anterior": s_old,
                    "status_atual": s_new,
                }
            )

    return {"novas": novas, "sumiram": sumiram, "mudancas_status": mudancas_status}


def run_monitor(vertical: str, store: Store | None = None) -> dict[str, Any]:
    """Roda uma checagem de mudanças para uma vertical específica."""
    store = store or Store()

    if vertical not in SCRAPERS_MONITOR:
        raise ValueError(f"Vertical desconhecida: {vertical}")

    scraper_cls = SCRAPERS_MONITOR[vertical]
    scraper = scraper_cls()

    # Coleta atual
    logger.info("Monitor: coletando %s...", vertical)
    raw = scraper.scrape()

    # Parse via Gemini
    client = GeminiClient()
    empresas = []
    for r in raw:
        if r.get("_tipo") == "raw_html":
            empresas.extend(extract_companies_from_html(client, r["_html"], vertical, r["_fonte"]))

    # Diff com último snapshot
    previous = store.last_snapshot(vertical) or []
    delta = diff_lists(previous, empresas)

    # Salva snapshot atual
    store.save_snapshot(vertical, scraper.fonte_url, empresas)

    # Log evento
    store.log_event(
        "monitor_check",
        {
            "vertical": vertical,
            "total_atual": len(empresas),
            "novas": len(delta["novas"]),
            "sumiram": len(delta["sumiram"]),
            "mudancas_status": len(delta["mudancas_status"]),
        },
    )

    # Notifica Slack se houver mudança
    if delta["novas"] or delta["sumiram"] or delta["mudancas_status"]:
        _notify_changes(vertical, delta)

    resultado = {
        "vertical": vertical,
        "total": len(empresas),
        "previous_total": len(previous),
        "novas": delta["novas"],
        "sumiram": delta["sumiram"],
        "mudancas_status": delta["mudancas_status"],
        "checado_em": datetime.now().isoformat(),
    }
    return resultado


def _notify_changes(vertical: str, delta: dict[str, list[dict]]) -> None:
    """Envia notificação no Slack."""
    rotulo = {
        "betting": "Bets autorizadas (SPA/MF)",
        "pagamentos": "Instituições de Pagamento (Bacen)",
        "cobranca": "Empresas de Cobrança",
        "saas_b2b": "SaaS B2B",
    }.get(vertical, vertical)

    msg = f"*Monitor — {rotulo}*\n"
    if delta["novas"]:
        msg += f"\n🆕 {len(delta['novas'])} nova(s) empresa(s) autorizada(s):\n"
        for e in delta["novas"][:10]:
            msg += f"  • {e.get('empresa', '?')} ({e.get('cnpj', 'sem CNPJ')})\n"
    if delta["sumiram"]:
        msg += f"\n⚠️ {len(delta['sumiram'])} empresa(s) saíram da lista:\n"
        for e in delta["sumiram"][:5]:
            msg += f"  • {e.get('empresa', '?')}\n"
    if delta["mudancas_status"]:
        msg += f"\n🔄 {len(delta['mudancas_status'])} mudança(s) de status:\n"
        for m in delta["mudancas_status"][:5]:
            msg += f"  • {m['empresa']}: {m['status_anterior']} → {m['status_atual']}\n"

    notify_slack(msg)
