"""Parser que transforma HTML/texto cru em registros estruturados via Gemini."""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

from .client import ClaudeClient

logger = logging.getLogger(__name__)


SYSTEM_PARSER = """Você é um agente especialista em extrair dados de empresas brasileiras
a partir de páginas públicas (governo, associações, diretórios, listas oficiais).

Regras:
- SEMPRE retorne JSON válido conforme o schema fornecido
- Extraia TODAS as empresas mencionadas na página, sem pular
- Nunca invente dados. Se não houver informação, use null
- Limpe nomes (sem espaços extras)
- CNPJ deve vir formatado: XX.XXX.XXX/XXXX-XX
- Sites devem ser URLs válidas com https://
- Não traduza nomes próprios"""


def _clean_html(html: str, max_chars: int = 500_000) -> str:
    """Remove scripts, styles, navigation e elementos sem dado.

    Mantém só o conteúdo principal e o texto útil para extração.
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove elementos não-úteis
    for tag in soup(["script", "style", "noscript", "iframe", "svg", "meta", "link"]):
        tag.decompose()
    for tag in soup.find_all(attrs={"role": ["banner", "navigation", "complementary"]}):
        tag.decompose()
    for selector in ["header", "footer", "nav", "aside"]:
        for tag in soup.find_all(selector):
            tag.decompose()

    # Pega só o body
    body = soup.body or soup
    text_html = str(body)

    # Colapsa whitespace
    text_html = re.sub(r"\s+", " ", text_html)
    text_html = re.sub(r">\s+<", "><", text_html)

    if len(text_html) > max_chars:
        text_html = text_html[:max_chars]
    return text_html


def extract_companies_from_html(
    client: ClaudeClient,
    html: str,
    vertical: str,
    fonte_url: str,
) -> list[dict]:
    """Extrai lista de empresas de um HTML usando Gemini.

    Args:
        client: instância GeminiClient
        html: HTML cru da página
        vertical: betting | pagamentos | cobranca | saas_b2b
        fonte_url: URL da fonte original

    Returns:
        lista de dicts: empresa, cnpj, razao_social, site, status_licenca, marcas
    """
    # Pré-processa para reduzir ruído
    clean_html = _clean_html(html)
    logger.info("HTML limpo: %d chars (de %d original)", len(clean_html), len(html))

    # Schema enxuto: só o essencial. Enrichment posterior pega CNPJ via BrasilAPI.
    schema = """{
  "empresas": [
    {
      "empresa": "Nome comercial",
      "site": "URL ou null",
      "cnpj": "XX.XXX.XXX/XXXX-XX ou null"
    }
  ]
}"""

    prompt = f"""Extraia TODAS as empresas listadas no HTML abaixo. Vertical: {vertical}.

Fonte: {fonte_url}

REGRAS:
- A página contém uma lista de empresas (bets autorizadas, IPs Bacen, cobrança ou SaaS B2B)
- Procure tabelas, listas, cards ou blocos repetidos
- Não duplique empresas que aparecem em mais de um lugar
- Retorne SOMENTE os 3 campos: empresa, site, cnpj
- Use null para campos ausentes — não invente
- IMPORTANTE para o campo "site": prefira o domínio oficial da empresa
  (ex: betano.bet.br, brazino777.com). Se o único link disponível for um redirector
  de tracker/agregador (ex: contém "swiftly", "candle", "redirect", "out", "vai-"
  no path, ou domínios encurtadores), retorne null em vez do redirect.

HTML:
{clean_html}

Extraia TODAS as empresas. Resposta concisa, apenas JSON conforme schema."""

    result = client.extract_json(prompt, system=SYSTEM_PARSER, schema_hint=schema)
    empresas = result.get("empresas", [])
    logger.info("Empresas extraídas: %d", len(empresas))
    return empresas
