"""Testes básicos de sanidade — não exigem chave Claude."""

from __future__ import annotations

import pytest

from src.enrichers.brasil_api import format_cnpj, normalize_cnpj
from src.enrichers.email_validator import is_valid_email_format
from src.scrapers.linkedin import parse_linkedin_payload


def test_normalize_cnpj():
    assert normalize_cnpj("11.222.333/0001-44") == "11222333000144"
    assert normalize_cnpj("11222333000144") == "11222333000144"
    assert normalize_cnpj("") == ""


def test_format_cnpj():
    assert format_cnpj("11222333000144") == "11.222.333/0001-44"
    assert format_cnpj("11.222.333/0001-44") == "11.222.333/0001-44"
    # CNPJ inválido retorna como veio
    assert format_cnpj("123") == "123"


def test_email_format():
    assert is_valid_email_format("foo@bar.com")
    assert is_valid_email_format("foo.bar@example.co.uk")
    assert not is_valid_email_format("foo@")
    assert not is_valid_email_format("foo")
    assert not is_valid_email_format("")


def test_parse_linkedin_payload_empty():
    payload = {"source": "linkedin_sales_nav", "url": "https://x", "items": []}
    assert parse_linkedin_payload(payload) == []


def test_parse_linkedin_payload_basic():
    payload = {
        "source": "linkedin_sales_nav",
        "url": "https://linkedin.com/sales/search/people",
        "items": [
            {
                "nome": "Felipe Santos",
                "cargo": "Head of Product",
                "empresa": "Betano",
                "url": "https://linkedin.com/in/felipesantos",
            }
        ],
    }
    parsed = parse_linkedin_payload(payload)
    assert len(parsed) == 1
    assert parsed[0]["decisor_nome"] == "Felipe Santos"
    assert parsed[0]["empresa"] == "Betano"
    assert parsed[0]["fonte"] == "linkedin_sales_nav"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
