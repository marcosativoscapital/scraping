"""Envio de e-mail via SMTP, com modo dry-run.

Configuração por variáveis de ambiente (SMTP_HOST/PORT/USER/PASS/FROM).
Por padrão opera em DRY-RUN (OUTBOUND_DRY_RUN != "false"): apenas loga e
retorna sucesso simulado — para o loop ser testável sem credenciais e sem
disparar e-mails reais. Defina OUTBOUND_DRY_RUN=false + SMTP_* para enviar.
"""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def is_dry_run() -> bool:
    return os.environ.get("OUTBOUND_DRY_RUN", "true").strip().lower() != "false"


def smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_FROM"))


def send_email(to: str, subject: str, body: str) -> dict:
    """Envia um e-mail. Retorna {ok, dry_run, erro}.

    Em dry-run (padrão) ou sem SMTP configurado: loga e devolve ok simulado.
    """
    if not to:
        return {"ok": False, "dry_run": is_dry_run(), "erro": "destinatário vazio"}

    if is_dry_run() or not smtp_configured():
        logger.info(
            "[DRY-RUN e-mail] para=%s assunto=%r (corpo: %d chars) — NÃO enviado",
            to, subject, len(body or ""),
        )
        return {"ok": True, "dry_run": True, "erro": None}

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    sender = os.environ["SMTP_FROM"]

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject or "(sem assunto)"
    msg.set_content(body or "")

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls(context=ssl.create_default_context())
            if user and password:
                server.login(user, password)
            server.send_message(msg)
        logger.info("E-mail enviado para %s (assunto: %r)", to, subject)
        return {"ok": True, "dry_run": False, "erro": None}
    except Exception as e:
        logger.exception("Falha ao enviar e-mail para %s", to)
        return {"ok": False, "dry_run": False, "erro": str(e)}
