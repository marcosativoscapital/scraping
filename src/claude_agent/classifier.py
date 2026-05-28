"""Classifica vertical e segmento dentro da vertical."""

from __future__ import annotations

from .client import ClaudeClient

SYSTEM_CLASSIFIER = """Você é um agente que classifica empresas brasileiras nas verticais-alvo da Solvefy:

VERTICAIS:
1. betting — apostas esportivas, iGaming, casas de apostas reguladas
2. pagamentos — IPs Bacen, sub-acquirers, fintechs de pagamento, gateway
3. cobranca — recuperação de crédito, assessoria de cobrança, SaaS de cobrança
4. saas_b2b — SaaS B2B/B2B2C que pode consumir CPaaS

Regras:
- Se a empresa não fit em nenhuma vertical, retorne 'outros'
- Justifique brevemente a classificação
- Identifique o segmento específico dentro da vertical"""


def classify_company(client: ClaudeClient, empresa_data: dict) -> dict:
    """Classifica uma empresa em vertical + segmento.

    Args:
        empresa_data: dict com pelo menos: empresa, razao_social, site, observacoes

    Returns:
        dict com chaves: vertical, segmento, justificativa, porte_estimado
    """
    schema = """{
  "vertical": "betting|pagamentos|cobranca|saas_b2b|outros",
  "segmento": "sub-classificação dentro da vertical",
  "justificativa": "1-2 frases explicando a classificação",
  "porte_estimado": "pequena|media|grande|enterprise"
}"""

    info = "\n".join(f"- {k}: {v}" for k, v in empresa_data.items() if v)

    prompt = f"""Classifique a empresa abaixo:

{info}

Identifique a vertical, segmento específico e estime o porte."""

    return client.extract_json(prompt, system=SYSTEM_CLASSIFIER, schema_hint=schema)
