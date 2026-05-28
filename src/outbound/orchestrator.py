"""Gera mensagens de outbound personalizadas por canal usando Gemini.

Para cada lead, produz:
- 1 SMS curto (≤ 160 chars)
- 1 e-mail (subject + body, com 5 toques de sequência opcional)
- 1 mensagem LinkedIn (connection request curto + follow-up)

Tudo personalizado pelo `gatilho_personalizado` do lead e mensagem central da vertical.
"""

from __future__ import annotations

import logging
from typing import Any

from ..claude_agent.client import GeminiClient
from ..db.store import Store

logger = logging.getLogger(__name__)


SYSTEM_OUTBOUND = """Você é um copywriter sênior de outbound B2B da Solvefy CPaaS.

Diferenciais da Solvefy:
- 20 anos de pipe ANATEL (Brasilfone) — 10B+ SMS, 390M/mês
- Suporte 100% humano (vs Twilio/Zenvia)
- 20% mais barato que mercado
- Compliance Bacen e LGPD documentado

REGRAS GERAIS:
- Tom: peer-to-peer, técnico, direto
- Sem "gostaria de apresentar", sem buzzwords
- Português brasileiro
- Sentence case (sem CAPS desnecessário)
- Termina com pergunta de baixa fricção

Por canal:
- SMS: ≤ 160 caracteres, 1 frase com gatilho + CTA curta
- E-mail subject: ≤ 55 caracteres, evita spam triggers
- E-mail body: 80-130 palavras, 3 parágrafos curtos (contexto, conexão, CTA)
- LinkedIn connection: ≤ 300 caracteres, peer-to-peer
- LinkedIn follow-up: ≤ 700 caracteres, complementa o connection"""


def generate_outbound_messages(client: GeminiClient, lead: dict[str, Any]) -> dict[str, str]:
    """Gera mensagens para todos os canais.

    Returns:
        dict com chaves: sms, email_subject, email_body, linkedin_connection, linkedin_followup
    """
    schema = """{
  "sms": "mensagem SMS curta",
  "email_subject": "assunto do e-mail",
  "email_body": "corpo do e-mail em 3 parágrafos",
  "linkedin_connection": "mensagem de connection request",
  "linkedin_followup": "mensagem de follow-up se aceitar"
}"""

    info = "\n".join(
        f"- {k}: {v}" for k, v in lead.items() if v and k in {
            "empresa", "vertical", "segmento", "porte_estimado",
            "decisor_nome", "decisor_cargo", "gatilho_personalizado",
            "observacoes",
        }
    )

    prompt = f"""Gere mensagens de outbound multicanal para o lead:

{info}

Use o gatilho personalizado como ponto de partida e adapte para cada canal.
A mensagem central da Solvefy CPaaS deve estar presente em todos os canais,
mas ajustada ao formato de cada um."""

    return client.extract_json(prompt, system=SYSTEM_OUTBOUND, schema_hint=schema)


def generate_and_store(lead_id: int, lead: dict[str, Any], store: Store | None = None) -> dict[str, str]:
    """Gera mensagens e salva no SQLite."""
    store = store or Store()
    client = GeminiClient()

    messages = generate_outbound_messages(client, lead)

    # Salva cada canal como linha separada
    for canal in ("sms", "email_subject", "email_body", "linkedin_connection", "linkedin_followup"):
        if msg := messages.get(canal):
            store.save_outbound(lead_id, canal, msg)

    store.log_event("outbound_generated", {"lead_id": lead_id, "empresa": lead.get("empresa")})
    return messages
