"""Integração com o Exact Spotter (Exact Sales).

Envia leads já tratados aqui (empresa + decisor/contato + score/gatilho) como
LEADS no Exact Spotter, onde o SDR roda o questionário e GERA a oportunidade lá.

API v3: POST {BASE_URL}/leads  — header `token_exact` + Content-Type JSON.
Só `name` é obrigatório; origin/market/cpfCnpj/sdrEmail/contatos são opcionais.

Por padrão roda em DRY-RUN: monta e loga o payload SEM enviar. Para enviar de
verdade, configure no .env:
    EXACT_SPOTTER_TOKEN=...           # Spotter > Configurações > Integrações
    EXACT_SPOTTER_DRY_RUN=false
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any

from ..db.store import Store

logger = logging.getLogger(__name__)

BASE_URL = os.environ.get("EXACT_SPOTTER_BASE_URL", "https://api.exactspotter.com/v3").rstrip("/")


def _dry_run_default() -> bool:
    return os.environ.get("EXACT_SPOTTER_DRY_RUN", "true").strip().lower() != "false"


def _digits(s: Any) -> str:
    return re.sub(r"\D", "", str(s or ""))


def lead_link(base_url: str | None, ws_id: Any, lead_id: Any) -> str | None:
    """URL de volta para a ficha do lead na plataforma Solvefy Leads."""
    if not base_url or not lead_id:
        return None
    return f"{str(base_url).rstrip('/')}/dashboard/?ws={ws_id or 1}&lead={lead_id}"


def build_lead_payload(
    lead: dict[str, Any], *, base_url: str | None = None, ws_id: Any = None, sdr_email: str | None = None
) -> dict[str, Any]:
    """Mapeia um lead do Solvefy Leads para o payload do endpoint POST /leadsAdd.

    Schema V3: corpo é `{duplicityValidation, lead: {...}}`. Só `lead.name` é
    obrigatório. O endpoint não recebe array de contatos — decisor + link da ficha
    entram na `description` (e o link também em `mktLink`). `sdrEmail` direciona o
    lead a um pré-vendedor específico.
    """
    empresa = (lead.get("empresa") or lead.get("razao_social") or "").strip() or "Lead sem nome"
    inner: dict[str, Any] = {"name": empresa, "source": "Solvefy Leads"}
    if sdr_email and "@" in sdr_email:
        inner["sdrEmail"] = sdr_email.strip()
    if lead.get("vertical"):
        inner["industry"] = str(lead["vertical"])
    if lead.get("site"):
        inner["website"] = str(lead["site"])
    tel = _digits(lead.get("telefone")).lstrip("0")
    if tel:
        inner["ddiPhone"] = "55"
        inner["phone"] = tel
    doc = _digits(lead.get("cnpj"))
    if len(doc) in (11, 14):  # CPF/CNPJ completos; ignora placeholders (ex.: ...0001-XX)
        inner["cpfcnpj"] = doc

    link = lead_link(base_url, ws_id, lead.get("id"))
    if link:
        inner["mktLink"] = link

    desc: list[str] = []
    if link:
        desc.append(f"Ficha no Solvefy Leads: {link}")
    if lead.get("decisor_nome"):
        d = str(lead["decisor_nome"])
        if lead.get("decisor_cargo"):
            d += f" ({lead['decisor_cargo']})"
        if lead.get("email_provavel"):
            d += f" · {lead['email_provavel']}"
        desc.append("Decisor: " + d)
    if lead.get("score_icp") is not None:
        desc.append(f"Score ICP: {lead['score_icp']}")
    if lead.get("recomendacao"):
        desc.append(f"Recomendação: {lead['recomendacao']}")
    if lead.get("gatilho_personalizado"):
        desc.append(str(lead["gatilho_personalizado"]))
    if desc:
        inner["description"] = "\n".join(desc)

    return {"duplicityValidation": True, "lead": inner}


def push_lead(
    lead: dict[str, Any], dry_run: bool | None = None, *,
    base_url: str | None = None, ws_id: Any = None, sdr_email: str | None = None,
) -> dict[str, Any]:
    """Envia (ou simula) o lead ao Exact Spotter. Retorna {ok, dry_run, payload, ...}."""
    dry = _dry_run_default() if dry_run is None else dry_run
    payload = build_lead_payload(lead, base_url=base_url, ws_id=ws_id, sdr_email=sdr_email)

    if dry:
        logger.info("[exact_spotter dry-run] %s", json.dumps(payload, ensure_ascii=False))
        return {"ok": True, "dry_run": True, "payload": payload}

    token = os.environ.get("EXACT_SPOTTER_TOKEN")
    if not token:
        return {"ok": False, "dry_run": False, "erro": "EXACT_SPOTTER_TOKEN não definido", "payload": payload}

    req = urllib.request.Request(
        f"{BASE_URL}/leadsAdd",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "token_exact": token},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            body = r.read().decode("utf-8", "ignore")
            lead_id_exact = None
            try:
                lead_id_exact = json.loads(body).get("value")
            except Exception:
                pass
            return {"ok": True, "dry_run": False, "status": r.status, "lead_id_exact": lead_id_exact, "payload": payload, "response": body[:2000]}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:2000] if hasattr(e, "read") else str(e)
        logger.warning("Exact Spotter HTTP %s: %s", e.code, detail)
        return {"ok": False, "dry_run": False, "status": e.code, "erro": detail, "payload": payload}
    except Exception as e:  # noqa: BLE001
        logger.warning("Exact Spotter falhou: %s", e)
        return {"ok": False, "dry_run": False, "erro": str(e), "payload": payload}


def push_and_mark(
    lead_id: int, store: "Store | None" = None, dry_run: bool | None = None, *,
    base_url: str | None = None, ws_id: Any = None, sdr_email: str | None = None,
) -> dict[str, Any]:
    """Envia o lead ao Spotter e registra o status em payload_json['exact_spotter']."""
    store = store or Store()
    with store.conn() as c:
        row = c.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
    if not row:
        return {"ok": False, "erro": f"lead {lead_id} não encontrado"}
    lead = dict(row)
    res = push_lead(lead, dry_run=dry_run, base_url=base_url, ws_id=ws_id, sdr_email=sdr_email)
    if res.get("ok"):
        with store.conn() as c:
            raw = lead.get("payload_json") or "{}"
            pd = json.loads(raw) if isinstance(raw, str) else (raw or {})
            pd["exact_spotter"] = {
                "enviado_em": datetime.now().isoformat(timespec="seconds"),
                "dry_run": bool(res.get("dry_run", True)),
                "lead_id_exact": res.get("lead_id_exact"),
                "sdr_email": (sdr_email or None),
            }
            c.execute(
                "UPDATE leads SET payload_json=? WHERE id=?",
                (json.dumps(pd, ensure_ascii=False, default=str), lead_id),
            )
        try:
            store.log_event("exact_spotter_push", {"lead_id": lead_id, "dry_run": bool(res.get("dry_run", True))})
        except Exception:
            pass
    return res
