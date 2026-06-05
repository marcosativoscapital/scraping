"""Testes das funções puras de dedup da descoberta de leads por IA (offline)."""

from __future__ import annotations

from src.enrichers.web_enricher import _domain, _nivel_norm, _norm_name


def test_nivel_norm_classifica_tres_niveis():
    # C-level
    assert _nivel_norm("C-level", "CEO") == "c_level"
    assert _nivel_norm(None, "Diretora de Marketing") == "c_level"
    assert _nivel_norm(None, "Sócio-fundador") == "c_level"
    assert _nivel_norm(None, "CFO") == "c_level"
    # Média gestão
    assert _nivel_norm("Média gestão", "Head de Growth") == "mid_level"
    assert _nivel_norm(None, "Gerente de Performance") == "mid_level"
    assert _nivel_norm(None, "Coordenador de Mídia") == "mid_level"
    # Operacional (default)
    assert _nivel_norm(None, "Analista de Tráfego") == "operacional"
    assert _nivel_norm(None, "") == "operacional"
    # não confunde "negócio" (contém "cio") com C-level
    assert _nivel_norm(None, "Analista de Negócios") == "operacional"


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
