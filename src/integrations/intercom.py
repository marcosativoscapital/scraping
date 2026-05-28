"""Push de leads qualificados para o Intercom.

Cria contato no Intercom (Contacts API v2.x) com:
- e-mail
- nome
- empresa
- custom attributes: score_icp, vertical, gatilho_personalizado, decisor_cargo
- tag por vertical

Documentação: https://developers.intercom.com/intercom-api-reference/reference/createcontact
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)


INTERCOM_BASE = "https://api.intercom.io"


def _headers() -> dict[str, str] | None:
    token = os.environ.get("INTERCOM_ACCESS_TOKEN")
    if not token:
        return None
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Intercom-Version": "2.11",
    }


def push_lead_to_intercom(lead: dict[str, Any]) -> dict[str, Any]:
    """Cria/atualiza contato no Intercom.

    Returns:
        dict com `ok: bool` e detalhes da resposta.
    """
    headers = _headers()
    if not headers:
        logger.warning("INTERCOM_ACCESS_TOKEN não configurado — push ignorado.")
        return {"ok": False, "reason": "no_token"}

    if not lead.get("email_provavel") and not lead.get("decisor_nome"):
        return {"ok": False, "reason": "no_email_or_name"}

    body = {
        "role": "lead",
        "email": lead.get("email_provavel"),
        "name": lead.get("decisor_nome"),
        "external_id": _external_id(lead),
        "custom_attributes": {
            "empresa": lead.get("empresa"),
            "cnpj": lead.get("cnpj"),
            "vertical": lead.get("vertical"),
            "segmento": lead.get("segmento"),
            "porte_estimado": lead.get("porte_estimado"),
            "decisor_cargo": lead.get("decisor_cargo"),
            "decisor_linkedin": lead.get("decisor_linkedin"),
            "score_icp": lead.get("score_icp"),
            "recomendacao": lead.get("recomendacao"),
            "gatilho_personalizado": lead.get("gatilho_personalizado"),
            "fonte_lead": lead.get("fonte"),
        },
    }

    try:
        # Cria
        r = requests.post(f"{INTERCOM_BASE}/contacts", headers=headers, json=body, timeout=15)
        if r.status_code == 201 or r.status_code == 200:
            data = r.json()
            contact_id = data.get("id")
            # Tag por vertical
            if vertical := lead.get("vertical"):
                _tag_contact(headers, contact_id, f"vertical-{vertical}")
            if (lead.get("score_icp") or 0) >= 80:
                _tag_contact(headers, contact_id, "hot-lead")
            return {"ok": True, "contact_id": contact_id}

        if r.status_code == 409:
            # Contato já existe — atualiza
            existing = _find_by_external_id(headers, _external_id(lead))
            if existing:
                upd = requests.put(
                    f"{INTERCOM_BASE}/contacts/{existing['id']}",
                    headers=headers,
                    json=body,
                    timeout=15,
                )
                return {"ok": upd.ok, "contact_id": existing["id"], "status": upd.status_code}

        logger.warning("Intercom %d: %s", r.status_code, r.text[:300])
        return {"ok": False, "status": r.status_code, "body": r.text[:300]}
    except Exception as e:
        logger.exception("Falha ao push Intercom: %s", e)
        return {"ok": False, "error": str(e)}


def _external_id(lead: dict) -> str:
    """ID estável baseado em CNPJ + e-mail."""
    cnpj = (lead.get("cnpj") or "").replace(".", "").replace("/", "").replace("-", "")
    email = (lead.get("email_provavel") or "").lower().strip()
    return f"solve-{cnpj}-{email}"[:64]


def _find_by_external_id(headers: dict, external_id: str) -> dict | None:
    try:
        r = requests.post(
            f"{INTERCOM_BASE}/contacts/search",
            headers=headers,
            json={"query": {"field": "external_id", "operator": "=", "value": external_id}},
            timeout=10,
        )
        if r.ok:
            data = r.json()
            if data.get("total_count", 0) > 0:
                return data["data"][0]
    except Exception as e:
        logger.debug("Falha em search Intercom: %s", e)
    return None


def _tag_contact(headers: dict, contact_id: str, tag: str) -> None:
    try:
        requests.post(
            f"{INTERCOM_BASE}/contacts/{contact_id}/tags",
            headers=headers,
            json={"id": tag},
            timeout=10,
        )
    except Exception:
        pass


def push_batch(leads: list[dict]) -> dict[str, int]:
    """Empurra uma lista de leads."""
    ok = err = 0
    for lead in leads:
        if (lead.get("score_icp") or 0) < 60:
            continue
        result = push_lead_to_intercom(lead)
        if result.get("ok"):
            ok += 1
        else:
            err += 1
    return {"enviados": ok, "erros": err, "total_analisados": len(leads)}
