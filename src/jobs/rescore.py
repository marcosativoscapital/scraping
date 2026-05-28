"""Re-scoring periódico.

Re-pontua leads antigos (score 40-69) que estão há > 7 dias sem update.
Se subirem acima de 70, sobe pra "ativar_outbound" e notifica.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ..claude_agent.client import GeminiClient
from ..claude_agent.scorer import score_lead
from ..claude_agent.personalize import generate_trigger
from ..db.store import Store
from ..integrations.slack import notify_slack

logger = logging.getLogger(__name__)


def run_rescore(
    days_since: int = 7,
    max_score: int = 70,
    store: Store | None = None,
) -> dict[str, Any]:
    """Re-pontua leads que precisam de revisão."""
    store = store or Store()
    client = GeminiClient()

    candidatos = store.leads_for_rescore(days_since=days_since, max_score=max_score)
    logger.info("Re-score: %d candidatos", len(candidatos))

    promovidos = []  # leads que subiram acima de 70
    atualizados = 0

    for lead in candidatos:
        try:
            score_old = lead.get("score_icp") or 0
            # Re-pontua com Gemini
            sc = score_lead(client, lead)
            score_new = sc.get("score", 0)
            recomendacao = sc.get("recomendacao", "nutrir")

            lead["score_icp"] = score_new
            lead["recomendacao"] = recomendacao
            lead["score_atualizado_em"] = datetime.now().isoformat()

            # Se passou de 70 e não tinha gatilho, gera agora
            if score_new >= 70 and not lead.get("gatilho_personalizado"):
                try:
                    lead["gatilho_personalizado"] = generate_trigger(client, lead)
                except Exception as e:
                    logger.warning("Falha ao gerar gatilho pra %s: %s", lead.get("empresa"), e)

            store.upsert_lead(lead)
            atualizados += 1

            # Promoção: subiu acima de 70
            if score_old < 70 and score_new >= 70:
                promovidos.append(
                    {
                        "empresa": lead.get("empresa"),
                        "vertical": lead.get("vertical"),
                        "score_anterior": score_old,
                        "score_novo": score_new,
                        "decisor": lead.get("decisor_nome"),
                    }
                )
        except Exception as e:
            logger.warning("Falha no re-score de %s: %s", lead.get("empresa"), e)

    store.log_event(
        "rescore",
        {"candidatos": len(candidatos), "atualizados": atualizados, "promovidos": len(promovidos)},
    )

    if promovidos:
        _notify_promotions(promovidos)

    return {
        "candidatos": len(candidatos),
        "atualizados": atualizados,
        "promovidos": promovidos,
        "rodado_em": datetime.now().isoformat(),
    }


def _notify_promotions(promovidos: list[dict[str, Any]]) -> None:
    msg = f"*Re-score — {len(promovidos)} lead(s) promovido(s) para outbound:*\n"
    for p in promovidos[:10]:
        msg += f"  • {p['empresa']} ({p['vertical']}) — {p['score_anterior']} → {p['score_novo']}\n"
    notify_slack(msg)
