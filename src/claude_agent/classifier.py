"""Classifica vertical e segmento dentro do ICP da Solvefy CPaaS."""

from __future__ import annotations

from .client import ClaudeClient

SYSTEM_CLASSIFIER = """Você é um agente que classifica empresas brasileiras como prospects do Solvefy CPaaS.

CONTEXTO — O QUE É O PRODUTO
Solvefy CPaaS é infraestrutura de comunicação omnichannel (SMS + WhatsApp + RCS + Voz + E-mail)
em uma única API, com fatura em BRL e suporte humano em PT-BR.

ICP GERAL (Bible Book v2.1):
- Empresas brasileiras, 10–1.000 funcionários
- Setores-alvo: e-commerce, fintechs, gaming, varejo, saúde, educação, SaaS B2B, serviços
- Já opera ou pretende operar 2+ canais de comunicação

VERTICAIS PRIORITÁRIAS DO KR2:
1. betting — apostas esportivas, iGaming, bets reguladas SPA/MF, cassino online
2. pagamentos — Instituições de Pagamento Bacen, fintechs de pagamento, sub-acquirers,
   gateways, emissores de moeda eletrônica, iniciadores de pagamento
3. cobranca — assessorias de cobrança, recuperação de crédito, SaaS de cobrança,
   bureaus de crédito
4. saas_b2b — SaaS B2B/B2B2C com produto digital que precisa de comunicação multicanal
   para usuário final (healthtech, edtech, logtech, HRtech, ERPs verticais, etc.)

OUT OF SCOPE (classifique como 'outros'):
- CRM ou ferramenta de pipeline puro
- Helpdesk/ticketing isolado
- E-mail marketing isolado
- Operadora de telecom própria
- Empresas < 10 funcionários
- Startup em fase de exploração sem produto

REGRAS:
- Use 'outros' quando não houver fit claro
- 'porte_estimado': pequena (10-49), media (50-249), grande (250-999), enterprise (1000+)
- Justifique brevemente"""


def classify_company(client: ClaudeClient, empresa_data: dict) -> dict:
    """Classifica uma empresa em vertical + segmento.

    Returns:
        dict com chaves: vertical, segmento, justificativa, porte_estimado, fit_icp_geral
    """
    schema = """{
  "vertical": "betting|pagamentos|cobranca|saas_b2b|outros",
  "segmento": "sub-classificação específica dentro da vertical",
  "justificativa": "1-2 frases explicando a classificação",
  "porte_estimado": "pequena|media|grande|enterprise",
  "fit_icp_geral": true,
  "fit_icp_geral_razao": "por que está ou não no ICP geral do Bible"
}"""

    info = "\n".join(f"- {k}: {v}" for k, v in empresa_data.items() if v)

    prompt = f"""Classifique a empresa abaixo:

{info}

Identifique a vertical, segmento específico, porte e fit com o ICP geral da Solvefy CPaaS."""

    return client.extract_json(prompt, system=SYSTEM_CLASSIFIER, schema_hint=schema)
