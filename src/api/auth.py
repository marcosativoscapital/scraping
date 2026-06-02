"""Autenticação via Google (Sign in with Google) — verificação de ID token.

Ativa quando GOOGLE_CLIENT_ID está no ambiente. Sem ela, o app cai no token
único (API_TOKEN) — comportamento atual. As credenciais OAuth são criadas no
Google Cloud pelo usuário e passadas por env; nenhum segredo fica no código.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def google_client_id() -> str | None:
    return os.environ.get("GOOGLE_CLIENT_ID") or None


def google_enabled() -> bool:
    return bool(google_client_id())


def _allowed_domain() -> str | None:
    d = os.environ.get("ALLOWED_EMAIL_DOMAIN", "").strip().lstrip("@")
    return d or None


def verify_google_id_token(credential: str) -> dict:
    """Verifica o ID token do Google Identity Services. Retorna {ok, email, nome, erro}."""
    cid = google_client_id()
    if not cid:
        return {"ok": False, "erro": "Login Google não configurado"}
    if not credential:
        return {"ok": False, "erro": "credential vazio"}
    try:
        from google.auth.transport import requests as g_requests
        from google.oauth2 import id_token as gid

        info = gid.verify_oauth2_token(credential, g_requests.Request(), cid)
    except Exception as e:
        logger.warning("Falha verificando ID token Google: %s", e)
        return {"ok": False, "erro": "token inválido"}

    email = (info.get("email") or "").lower()
    if not email or not info.get("email_verified", False):
        return {"ok": False, "erro": "e-mail não verificado"}
    dom = _allowed_domain()
    if dom and not email.endswith("@" + dom):
        return {"ok": False, "erro": f"domínio não autorizado (use @{dom})"}
    return {
        "ok": True,
        "email": email,
        "nome": info.get("name") or info.get("given_name") or email,
    }
