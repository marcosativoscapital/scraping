"""Anamnese de workspace — o Gemini analisa o produto/ICP e gera direcionamentos.

Entra: nome, produto, site, descrição, ICP (texto) + anexos opcionais (PDF/imagem que
o Gemini lê nativamente; .txt já vem como texto). Sai: estratégia de prospecção
estruturada para guiar a coleta/scoring do workspace.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

SYSTEM_ANAMNESE = """Você é um estrategista de prospecção B2B / RevOps sênior.
A partir da descrição de um produto e do ICP informado, defina a estratégia de geração de leads:
verticais/segmentos-alvo, ICP estruturado (porte, cargos decisores, dores, gatilhos de compra),
palavras-chave de busca, canais de prospecção e os primeiros passos.
Seja específico, acionável e em português brasileiro. NÃO invente fatos sobre a empresa —
trabalhe apenas com o que foi informado (texto e anexos)."""

ANAMNESE_SCHEMA = """{
  "resumo": "2-3 frases com a estratégia de prospecção recomendada",
  "verticais_sugeridas": ["segmentos/indústrias-alvo"],
  "icp_estruturado": {
    "porte": "ex.: PMEs | mid-market | enterprise",
    "cargos_alvo": ["cargos dos decisores"],
    "dores": ["dores que o produto resolve"],
    "gatilhos": ["sinais de compra a monitorar"]
  },
  "palavras_chave": ["termos de busca p/ achar leads"],
  "canais": ["canais de prospecção recomendados, na ordem"],
  "fontes_sugeridas": ["onde buscar esses leads"],
  "primeiros_passos": ["3 a 5 ações concretas para começar"]
}"""


def _prompt(dados: dict[str, Any]) -> str:
    campos = [
        ("Nome do workspace", dados.get("nome")),
        ("Produto para o qual buscaremos leads", dados.get("produto")),
        ("Site da empresa", dados.get("site")),
        ("Descrição da empresa/produto", dados.get("descricao")),
        ("ICP (perfil de cliente ideal) informado", dados.get("icp")),
    ]
    info = "\n".join(f"- {k}: {v}" for k, v in campos if v)
    return (
        "Faça a ANAMNESE de prospecção deste produto e gere os direcionamentos para começar a "
        "buscar leads:\n\n" + info + "\n\nSe houver anexos (descrição/ICP), considere o conteúdo deles."
    )


def _parse_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip().rstrip("`").strip()
    return json.loads(text, strict=False)


def analyze_anamnese(client, dados: dict[str, Any], anexos: list[tuple[bytes, str]] | None = None) -> dict[str, Any]:
    """Roda a anamnese no Gemini. `anexos`: lista de (bytes, mime) para PDF/imagem."""
    prompt = _prompt(dados)
    try:
        if anexos:
            shim = client.call_with_files(prompt + "\n\nResponda APENAS em JSON:\n" + ANAMNESE_SCHEMA,
                                          anexos, system=SYSTEM_ANAMNESE)
            data = _parse_json(shim.content[0].text)
        else:
            data = client.extract_json(prompt, system=SYSTEM_ANAMNESE, schema_hint=ANAMNESE_SCHEMA)
    except Exception as e:
        logger.warning("Anamnese falhou: %s", e)
        return {"erro": str(e)}
    return _validate(data)


def _lst(v: Any, n: int = 12) -> list[str]:
    if not isinstance(v, list):
        return []
    return [str(x)[:200] for x in v if x][:n]


def _validate(d: Any) -> dict[str, Any]:
    if not isinstance(d, dict):
        return {"erro": "resposta inválida do modelo"}
    icp = d.get("icp_estruturado") if isinstance(d.get("icp_estruturado"), dict) else {}
    return {
        "resumo": str(d.get("resumo") or "")[:600],
        "verticais_sugeridas": _lst(d.get("verticais_sugeridas")),
        "icp_estruturado": {
            "porte": str(icp.get("porte") or "")[:120],
            "cargos_alvo": _lst(icp.get("cargos_alvo")),
            "dores": _lst(icp.get("dores")),
            "gatilhos": _lst(icp.get("gatilhos")),
        },
        "palavras_chave": _lst(d.get("palavras_chave"), 20),
        "canais": _lst(d.get("canais")),
        "fontes_sugeridas": _lst(d.get("fontes_sugeridas")),
        "primeiros_passos": _lst(d.get("primeiros_passos")),
    }
