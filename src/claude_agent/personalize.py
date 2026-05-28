"""Gera gatilho personalizado de outbound para cada lead."""

from __future__ import annotations

from .client import ClaudeClient

SYSTEM_PERSONALIZER = """Você é um copywriter de outbound B2B sênior da Solvefy.

Diferenciais da Solvefy CPaaS:
- 20 anos de pipe ANATEL (herança do Brasilfone)
- 10 bilhões+ SMS enviados, 390M/mês
- Suporte 100% humano (diferencial vs Twilio/Zenvia)
- 20% mais barato que Meta/Google
- Compliance Bacen e LGPD documentado

Princípios da mensagem:
- Frase única, ≤ 25 palavras
- Específica para a empresa (cita gatilho ou contexto real)
- Termina com pergunta de baixa fricção
- Sem buzzwords, sem 'gostaria de apresentar'
- Tom: peer-to-peer, não vendedor desesperado"""


def generate_trigger(client: ClaudeClient, lead: dict) -> str:
    """Gera gatilho personalizado.

    Args:
        lead: dict com info da empresa + vertical + segmento + decisor

    Returns:
        string com frase pronta para cold outbound
    """
    info = "\n".join(f"- {k}: {v}" for k, v in lead.items() if v)

    prompt = f"""Gere uma frase de abordagem cold de até 25 palavras para o lead:

{info}

A frase deve:
1. Citar um gatilho real ou contexto específico da empresa
2. Conectar com uma dor de CPaaS relevante para a vertical
3. Terminar com pergunta simples

Retorne APENAS a frase, sem aspas, sem prefixo."""

    response = client.call(prompt, system=SYSTEM_PERSONALIZER, temperature=0.5)
    return response.content[0].text.strip().strip('"').strip("'")
