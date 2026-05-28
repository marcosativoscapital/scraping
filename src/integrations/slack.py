"""Notificações no Slack via webhook (opcional)."""

from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger(__name__)


def notify_slack(message: str, channel: str | None = None) -> bool:
    """Envia mensagem ao Slack se SLACK_WEBHOOK_URL estiver configurado.

    Retorna True se enviou, False caso contrário.
    """
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        logger.info("[slack-stub] %s", message)
        return False

    payload = {"text": message}
    if channel:
        payload["channel"] = channel

    try:
        r = requests.post(webhook, json=payload, timeout=10)
        if r.status_code in (200, 204):
            return True
        logger.warning("Slack webhook %d: %s", r.status_code, r.text[:200])
    except Exception as e:
        logger.warning("Falha no Slack: %s", e)
    return False
