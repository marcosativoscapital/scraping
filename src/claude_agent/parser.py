"""Parser que transforma HTML/texto cru em registros estruturados via Claude."""

from __future__ import annotations

from .client import ClaudeClient

SYSTEM_PARSER = """Você é um agente especialista em extrair dados de empresas brasileiras
a partir de páginas públicas (governo, associações, diretórios).

Regras:
- SEMPRE retorne JSON válido
- Nunca invente dados. Se não houver informação, use null
- Limpe nomes (sem espaços extras, sem acentuação inconsistente)
- CNPJ deve vir formatado: XX.XXX.XXX/XXXX-XX
- Sites devem ser URLs válidas com https://
- Não traduza nomes próprios"""


def extract_companies_from_html(
    client: ClaudeClient,
    html: str,
    vertical: str,
    fonte_url: str,
) -> list[dict]:
    """Extrai lista de empresas de um HTML.

    Args:
        client: instância ClaudeClient
        html: HTML cru da página
        vertical: betting | pagamentos | cobranca | saas_b2b
        fonte_url: URL da fonte original

    Returns:
        lista de dicts com chaves: empresa, cnpj, razao_social, site, status_licenca, observacoes
    """
    # Trunca HTML se gigante (mantém início onde geralmente está a tabela)
    if len(html) > 80_000:
        html = html[:80_000]

    schema = """{
  "empresas": [
    {
      "empresa": "Nome comercial",
      "cnpj": "XX.XXX.XXX/XXXX-XX ou null",
      "razao_social": "Razão social ou null",
      "site": "https://... ou null",
      "status_licenca": "autorizado / em_analise / null",
      "data_autorizacao": "YYYY-MM-DD ou null",
      "marcas": ["array de marcas se houver"],
      "observacoes": "qualquer info relevante"
    }
  ]
}"""

    prompt = f"""Extraia TODAS as empresas listadas no HTML abaixo. A vertical é: {vertical}.

Fonte: {fonte_url}

HTML:
{html}

Extraia tudo que conseguir. Para cada empresa, identifique nome, CNPJ (se houver),
site oficial, status de licença e qualquer dado relevante."""

    result = client.extract_json(prompt, system=SYSTEM_PARSER, schema_hint=schema)
    return result.get("empresas", [])
