"""Agente Gemini que seleciona 2-3 playbooks aplicáveis por lead."""

from __future__ import annotations

import logging
from typing import Any

from ..claude_agent.client import ClaudeClient
from .library import PlaybookLibrary, get_library

logger = logging.getLogger(__name__)


SYSTEM_SELECTOR = """Você é um agente que escolhe os 2 a 3 playbooks de outbound mais aplicáveis
para um lead da Solvefy CPaaS, a partir de uma biblioteca pré-definida.

REGRAS:
- Retorne SEMPRE entre 2 e 3 playbooks (nem menos, nem mais)
- Ordene por probabilidade de funcionar com o lead (mais provável primeiro)
- Justifique cada escolha em 1 frase curta citando o sinal específico do lead
- Se nenhum playbook for ideal, escolha os 2 menos ruins (universais) — nunca retorne 0 ou 1
- Use APENAS os IDs da biblioteca fornecida"""


def select_playbooks_for_lead(
    client: ClaudeClient,
    lead: dict[str, Any],
    library: PlaybookLibrary | None = None,
    n: int = 3,
) -> list[dict[str, Any]]:
    """Seleciona N playbooks aplicáveis para o lead.

    Returns:
        lista de dicts: { playbook_id, ordem, justificativa, sinal_detectado }
    """
    lib = library or get_library()
    bib_text = lib.summary_for_llm()

    schema = """{
  "playbooks_selecionados": [
    {
      "playbook_id": "id_do_playbook",
      "ordem": 1,
      "justificativa": "1 frase explicando por que esse playbook funciona aqui",
      "sinal_detectado": "qual sinal específico do lead indicou esse playbook"
    }
  ]
}"""

    lead_info = "\n".join(
        f"- {k}: {v}" for k, v in lead.items() if v and k in {
            "empresa", "vertical", "segmento", "porte_estimado",
            "decisor_nome", "decisor_cargo", "decisor_linkedin",
            "razao_social", "site", "observacoes", "classificacao_obs",
            "email_provavel", "status_licenca", "uf", "municipio",
            "segmento_bacen",
        }
    )

    prompt = f"""LEAD:
{lead_info}

BIBLIOTECA DE PLAYBOOKS DISPONÍVEIS:
{bib_text}

Escolha exatamente {n} playbooks mais aplicáveis a esse lead. Considere:
- Vertical da empresa
- Sinais detectados (porte, cargo do decisor, segmento, etc.)
- Probabilidade de o playbook gerar resposta
- Diversificação: prefira playbooks que cobrem dores diferentes

Para cada um, indique a ordem de prioridade (1 = primeiro a tentar)
e o sinal específico do lead que justifica a escolha."""

    result = client.extract_json(prompt, system=SYSTEM_SELECTOR, schema_hint=schema)
    selecionados = result.get("playbooks_selecionados", [])

    # Valida e enriquece com dados do playbook
    output = []
    for sel in selecionados:
        pb = lib.get(sel.get("playbook_id"))
        if pb:
            output.append({
                "playbook_id": pb.id,
                "playbook_nome": pb.nome,
                "categoria": pb.categoria,
                "ordem": sel.get("ordem", 99),
                "justificativa": sel.get("justificativa", ""),
                "sinal_detectado": sel.get("sinal_detectado", ""),
                "decisor_primario": pb.decisor_primario,
                "dor_alvo": pb.dor_alvo,
                "mensagem_central": pb.mensagem_central,
            })
    output.sort(key=lambda x: x["ordem"])
    return output
