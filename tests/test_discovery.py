"""Testes das funções puras de dedup da descoberta de leads por IA (offline)."""

from __future__ import annotations

from src.enrichers.web_enricher import _domain, _norm_name


def test_norm_name_colapsa_variantes():
    # "Brasil" e sufixos societários são removidos → mesma identidade
    assert _norm_name("iProspect Brasil") == _norm_name("iProspect")
    assert _norm_name("Acme Cobrança Ltda") == _norm_name("ACME COBRANCA")
    assert _norm_name("V4 Company") == _norm_name("V4")


def test_domain_colapsa_urls_diferentes():
    # mesmo domínio, paths/locales diferentes → mesma chave (evita duplicata iProspect)
    assert _domain("https://www.iprospect.com/pt/br/") == _domain("https://www.iprospect.com/pt-br/")
    assert _domain("http://only.ag/") == "only.ag"
    assert _domain("https://www.cadastra.com/contato?x=1") == "cadastra.com"


def test_dedup_keys_distintas_para_empresas_diferentes():
    assert _norm_name("iProspect") != _norm_name("Cadastra")
    assert _domain("https://only.ag") != _domain("https://v4company.com")
