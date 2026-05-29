"""Calcula score de fit com ICP do Solvefy CPaaS (0-100)."""

from __future__ import annotations

from .client import ClaudeClient

SYSTEM_SCORER = """Você avalia o fit de uma empresa brasileira com o ICP do Solvefy CPaaS.

ICP IDEAL (Bible Book v2.1 + planilha ICP):
- 10 a 1.000 funcionários
- Já opera 2+ canais de comunicação (SMS, WhatsApp, E-mail, Voz)
- Possui ≥ 1 dev dedicado
- Budget R$ 1.000–15.000/mês em comunicação multicanal
- Insatisfação concreta com vendor atual (custo, complexidade, cambial, banimento)
- Decisor identificado no trio: Marketing inicia, Tech Lead valida, Ops/CFO aprova

SINAIS POSITIVOS (somam pontos):
- Já usa SMS/WhatsApp/E-mail manualmente
- Tem dev dedicado
- Quer reduzir vendors / Operação 2+ canais hoje
- Histórico de banimento por API pirata
- CFO veta ferramentas em USD
- Investe em RD Station, HubSpot, ERPs
- Produz campanhas com cadência
- Já operou com Twilio/Infobip e sentiu o atrito

SINAIS NEGATIVOS (penalizam):
- < 10 funcionários
- Apenas 1 canal sem intenção de expandir
- Sem equipe técnica
- Foco exclusivo em helpdesk
- Startup pré-produto

CRITÉRIOS (peso entre parênteses):
- fit_vertical (20): empresa pertence claramente à vertical-alvo (betting/pagamentos/cobranca/saas_b2b)?
- porte (15): tem porte mínimo 10-1.000 funcionários?
- multi_canal_ativo (15): já opera 2+ canais de comunicação hoje?
- decisor_identificado (15): conseguimos identificar o decisor certo (Marketing/Tech Lead/Ops)?
- gatilho_ativo (20): há sinal recente (novo produto, regulação, crescimento, banimento)?
- contato_disponivel (15): temos e-mail ou LinkedIn do decisor?

Score 0-100. Aplique penalidades dos sinais negativos.
Seja crítico — só atribua > 80 a leads claramente qualificados (trio completo + gatilho + contato).

RECOMENDAÇÕES:
- score >= 80: ativar_outbound (prioridade alta — passar pro SDR imediatamente)
- score 60-79: ativar_outbound (prioridade normal)
- score 40-59: nutrir (nurture sequence)
- score < 40: descartar"""


def score_lead(client: ClaudeClient, lead: dict) -> dict:
    """Calcula score ICP de um lead."""
    schema = """{
  "score": 0,
  "breakdown": {
    "fit_vertical": 0,
    "porte": 0,
    "multi_canal_ativo": 0,
    "decisor_identificado": 0,
    "gatilho_ativo": 0,
    "contato_disponivel": 0
  },
  "sinais_positivos_detectados": ["lista de sinais positivos identificados"],
  "sinais_negativos_detectados": ["lista de sinais negativos identificados"],
  "recomendacao": "ativar_outbound|nutrir|descartar",
  "racional": "1-2 frases justificando o score"
}"""

    info = "\n".join(f"- {k}: {v}" for k, v in lead.items() if v)

    prompt = f"""Avalie o fit ICP do lead abaixo para o Solvefy CPaaS:

{info}

Calcule score total (máximo 100), breakdown por critério, sinais detectados e recomendação."""

    return client.extract_json(prompt, system=SYSTEM_SCORER, schema_hint=schema)
