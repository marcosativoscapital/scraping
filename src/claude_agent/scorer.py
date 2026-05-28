"""Calcula score de fit com ICP (0-100)."""

from __future__ import annotations

from .client import ClaudeClient

SYSTEM_SCORER = """Você é um agente que avalia o fit de uma empresa com o ICP da Solvefy CPaaS.

CRITÉRIOS (peso entre parênteses):
- Fit com a vertical (25): pertence claramente à vertical-alvo?
- Porte (15): tem porte mínimo para consumir CPaaS (>10k mensagens/mês)?
- Decisor identificado (20): conseguimos identificar o decisor certo?
- Gatilho ativo (25): há sinal recente (novo produto, expansão, regulação)?
- Contato disponível (15): temos e-mail/LinkedIn do decisor?

Score 0-100. Seja crítico — só atribua > 80 a leads muito qualificados."""


def score_lead(client: ClaudeClient, lead: dict) -> dict:
    """Calcula score ICP de um lead.

    Args:
        lead: dict completo com info da empresa + decisor + contato

    Returns:
        dict: { score: int, breakdown: dict, recomendacao: str }
    """
    schema = """{
  "score": 0,
  "breakdown": {
    "fit_vertical": 0,
    "porte": 0,
    "decisor_identificado": 0,
    "gatilho_ativo": 0,
    "contato_disponivel": 0
  },
  "recomendacao": "ativar_outbound|nutrir|descartar"
}"""

    info = "\n".join(f"- {k}: {v}" for k, v in lead.items() if v)

    prompt = f"""Avalie o fit ICP do lead abaixo:

{info}

Calcule score total (soma máxima 100), breakdown por critério, e recomendação."""

    return client.extract_json(prompt, system=SYSTEM_SCORER, schema_hint=schema)
