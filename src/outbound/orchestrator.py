"""Gera mensagens de outbound personalizadas por canal — linguagem do Bible Book v2.1.

Para cada lead, produz:
- 1 SMS curto (≤ 160 chars)
- 1 e-mail (subject + body, 3 parágrafos)
- 1 mensagem LinkedIn connection request + 1 follow-up
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ..claude_agent.client import GeminiClient
from ..db.store import Store
from ..integrations.email_sender import send_email

logger = logging.getLogger(__name__)


SYSTEM_OUTBOUND = """Você é copywriter sênior de outbound B2B do Solvefy CPaaS.

PRODUTO:
Solvefy CPaaS — infraestrutura de comunicação omnichannel: SMS + WhatsApp + RCS + Voz + E-mail
em uma única API. Brasil-first, fatura em BRL, suporte humano em PT-BR.

DIFERENCIAIS (use os que fizerem sentido para o caso):
- 5 canais reais em 1 API
- Fallback RCS → SMS nativo (único no Brasil)
- Pricing em BRL, sem IOF, sem variação cambial — forecast de 12 meses viável
- Suporte humano PT-BR em todos os planos
- Onboarding em 1 dia útil
- WhatsApp via Meta oficial — zero risco de banimento
- RCS direto operadoras BR (185 mi dispositivos)
- LGPD-first

PERSONAS-ALVO (adapte tom):
- Marketing/Growth (Ana) → ROI claro por canal, dashboard único, autonomia sem TI
- Tech Lead/CTO (Lucas) → REST documentada, webhook que não falha, SLA único, integração em 1 dia útil
- Ops/CFO (Patrícia) → fatura BRL, forecast 12 meses, redução de vendors, zero exposição cambial

GATILHOS QUE FUNCIONAM:
- "Vi que vocês acabaram de [gatilho]..."
- "Reparei que [empresa] roda [X] hoje..."
- "Sei que [vertical] depende muito de [dor específica]..."

REGRAS POR CANAL:
- SMS: ≤ 160 chars, 1 frase com gatilho + CTA curta. Não use abreviações tipo "vc"
- E-mail subject: ≤ 55 chars, evita palavras-spam (grátis, urgente, ganhe)
- E-mail body: 80–130 palavras, 3 parágrafos curtos (contexto → conexão com dor → CTA)
- LinkedIn connection: ≤ 300 chars, peer-to-peer, sem pitch direto
- LinkedIn follow-up: ≤ 700 chars, complementa o connection com prova/dado/gatilho

PROIBIDO:
- "Gostaria de apresentar nossa solução"
- "Espero que esteja bem!"
- Buzzwords ("revolucionário", "transformador", "best-in-class")
- Emoji no chrome da mensagem
- Promessas vagas ("aumentar vendas", "escalar negócio")"""


def generate_outbound_messages(client: GeminiClient, lead: dict[str, Any]) -> dict[str, str]:
    """Gera mensagens para todos os canais.

    Returns:
        dict com chaves: sms, email_subject, email_body, linkedin_connection, linkedin_followup
    """
    schema = """{
  "sms": "mensagem SMS curta (≤ 160 chars)",
  "email_subject": "assunto do e-mail (≤ 55 chars)",
  "email_body": "corpo do e-mail em 3 parágrafos (80-130 palavras)",
  "linkedin_connection": "mensagem de connection request (≤ 300 chars)",
  "linkedin_followup": "mensagem de follow-up após aceitar (≤ 700 chars)"
}"""

    info = "\n".join(
        f"- {k}: {v}" for k, v in lead.items() if v and k in {
            "empresa", "vertical", "segmento", "porte_estimado",
            "decisor_nome", "decisor_cargo", "gatilho_personalizado",
            "observacoes", "classificacao_obs", "site",
        }
    )

    prompt = f"""Gere mensagens de outbound multicanal para o lead:

{info}

Use o gatilho_personalizado como ponto de partida e adapte para cada canal.
Adapte o tom à persona dominante baseada no cargo do decisor:
- Marketing → ROI, dashboard, autonomia
- Tech Lead/CTO → REST, webhook, SLA, integração rápida
- Ops/CFO → fatura BRL, forecast, redução vendors

A dor da vertical deve estar presente em todos os canais, mas modulada ao formato."""

    return client.extract_json(prompt, system=SYSTEM_OUTBOUND, schema_hint=schema)


def generate_and_store(lead_id: int, lead: dict[str, Any], store: Store | None = None) -> dict[str, str]:
    """Gera mensagens e salva no SQLite."""
    store = store or Store()
    client = GeminiClient()

    messages = generate_outbound_messages(client, lead)

    for canal in ("sms", "email_subject", "email_body", "linkedin_connection", "linkedin_followup"):
        if msg := messages.get(canal):
            store.save_outbound(lead_id, canal, msg)

    store.log_event("outbound_generated", {"lead_id": lead_id, "empresa": lead.get("empresa")})
    return messages


EMAIL_CANAIS = ("email_subject", "email_body")


def send_outbound(msg_id: int, store: Store | None = None) -> dict[str, Any]:
    """Envia (ou marca enviada) uma mensagem aprovada.

    E-mail dispara via SMTP (respeitando OUTBOUND_DRY_RUN) e exige email_validado;
    o par assunto+corpo é enviado junto e ambos viram 'enviado'. Demais canais
    (sms/linkedin) não têm auto-envio ainda → "enviado" é marcação manual.
    """
    store = store or Store()
    msg = store.outbound_message(msg_id)
    if not msg:
        return {"ok": False, "erro": "mensagem não encontrada"}
    if msg.get("status") != "aprovado":
        return {"ok": False, "erro": f"status é '{msg.get('status')}'; precisa estar 'aprovado'"}

    canal = msg.get("canal") or ""
    now = datetime.now().isoformat(timespec="seconds")

    if canal in EMAIL_CANAIS:
        if not msg.get("lead_email"):
            return {"ok": False, "erro": "lead sem e-mail"}
        if not msg.get("lead_email_validado"):
            return {"ok": False, "erro": "e-mail do lead não validado (email_validado != 1)"}
        lead_id = msg["lead_id"]
        subj_row = store.outbound_sibling(lead_id, "email_subject")
        body_row = store.outbound_sibling(lead_id, "email_body") or msg
        subject = (subj_row or {}).get("mensagem") or "Solvefy CPaaS"
        body = body_row.get("mensagem") or ""
        res = send_email(msg["lead_email"], subject, body)
        if res.get("ok"):
            for r in (subj_row, body_row):
                if r:
                    store.update_outbound_status(r["id"], "enviado", enviado_em=now, erro=None)
            store.log_event("outbound_sent", {"lead_id": lead_id, "canal": "email", "dry_run": res.get("dry_run")})
            return {"ok": True, "canal": "email", "dry_run": res.get("dry_run")}
        store.update_outbound_status(msg_id, "falhou", erro=res.get("erro"))
        return {"ok": False, "erro": res.get("erro")}

    # canais sem auto-envio: marca enviado manualmente
    store.update_outbound_status(msg_id, "enviado", enviado_em=now, erro=None)
    store.log_event("outbound_sent", {"lead_id": msg.get("lead_id"), "canal": canal, "manual": True})
    return {"ok": True, "canal": canal, "manual": True}
