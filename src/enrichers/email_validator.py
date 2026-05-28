"""Validação de e-mails via MX records (determinística, gratuita)."""

from __future__ import annotations

import logging
import re

import dns.resolver

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def is_valid_email_format(email: str) -> bool:
    """Validação de formato apenas."""
    return bool(EMAIL_REGEX.match(email or ""))


def has_mx_record(domain: str) -> bool:
    """Verifica se o domínio tem MX records (recebe e-mail)."""
    try:
        records = dns.resolver.resolve(domain, "MX", lifetime=5)
        return len(records) > 0
    except Exception as e:
        logger.debug("Sem MX para %s: %s", domain, e)
        return False


def validate_email(email: str) -> dict[str, bool]:
    """Retorna dict com format_ok e mx_ok."""
    if not is_valid_email_format(email):
        return {"format_ok": False, "mx_ok": False}
    domain = email.split("@")[1]
    return {"format_ok": True, "mx_ok": has_mx_record(domain)}
