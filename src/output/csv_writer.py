"""Exportador CSV padronizado."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

COLUNAS_PADRAO = [
    "vertical",
    "segmento",
    "empresa",
    "cnpj",
    "razao_social",
    "site",
    "status_licenca",
    "decisor_nome",
    "decisor_cargo",
    "decisor_linkedin",
    "email_provavel",
    "email_validado",
    "telefone",
    "porte_estimado",
    "score_icp",
    "recomendacao",
    "gatilho_personalizado",
    "fonte",
    "data_coleta",
    "observacoes",
]


def write_leads_csv(
    leads: list[dict],
    output_dir: Path = Path("data/output"),
    vertical_tag: str = "all",
) -> Path:
    """Salva leads em CSV padronizado."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    path = output_dir / f"leads_{vertical_tag}_{timestamp}.csv"

    # Garante todas as colunas
    for lead in leads:
        for col in COLUNAS_PADRAO:
            lead.setdefault(col, None)

    df = pd.DataFrame(leads, columns=COLUNAS_PADRAO)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    logger.info("CSV salvo: %s (%d leads)", path, len(leads))
    return path


def write_apollo_csv(
    leads: list[dict],
    output_dir: Path = Path("data/output"),
) -> Path:
    """Saída formatada para import direto no Apollo (mapeamento de colunas)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    path = output_dir / f"apollo_import_{timestamp}.csv"

    apollo_records = []
    for lead in leads:
        nome = (lead.get("decisor_nome") or "").strip()
        first, last = (nome.split(" ", 1) + [""])[:2] if nome else ("", "")
        apollo_records.append(
            {
                "First Name": first,
                "Last Name": last,
                "Title": lead.get("decisor_cargo"),
                "Company": lead.get("empresa"),
                "Email": lead.get("email_provavel"),
                "Phone": lead.get("telefone"),
                "LinkedIn URL": lead.get("decisor_linkedin"),
                "Website": lead.get("site"),
                "Industry": lead.get("vertical"),
                "Custom - Gatilho": lead.get("gatilho_personalizado"),
                "Custom - Score": lead.get("score_icp"),
            }
        )

    df = pd.DataFrame(apollo_records)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    logger.info("CSV Apollo salvo: %s", path)
    return path


def hydrate_db_row(row: dict[str, Any]) -> dict[str, Any]:
    """Enriquece uma linha do DB com campos que vivem só no payload_json.

    A tabela `leads` não tem colunas próprias para `segmento`, `status_licenca`
    nem `data_coleta` — elas ficam no `payload_json` (e `data_coleta` cai para
    `criado_em`). Sem isso, o CSV exportado do DB sairia com essas colunas vazias.
    """
    out = dict(row)
    raw = out.get("payload_json") or "{}"
    try:
        payload = json.loads(raw) if isinstance(raw, str) else (raw or {})
    except (json.JSONDecodeError, TypeError):
        payload = {}

    out["segmento"] = out.get("segmento") or payload.get("segmento")
    out["status_licenca"] = out.get("status_licenca") or payload.get("status_licenca")
    out["data_coleta"] = out.get("data_coleta") or payload.get("data_coleta") or out.get("criado_em")
    # telefone pode existir só no payload (leads coletados antes da coluna telefone)
    out["telefone"] = out.get("telefone") or payload.get("telefone")
    return out


def export_db_to_csv(
    store: Any,
    vertical: str | None = None,
    min_score: int = 0,
    limit: int = 10000,
    output_dir: Path = Path("data/output"),
    vertical_tag: str | None = None,
) -> Path | None:
    """Exporta leads do DB (já enriquecidos) para CSV padronizado.

    Diferente de `write_leads_csv`, lê do banco — então reflete os decisores,
    e-mails validados e telefones gravados pela etapa de enrichment web.
    """
    leads = store.all_leads(vertical=vertical, min_score=min_score, limit=limit)
    if not leads:
        logger.warning("Nenhum lead no DB para exportar (vertical=%s, min_score=%s)", vertical, min_score)
        return None
    hydrated = [hydrate_db_row(l) for l in leads]
    tag = vertical_tag or (vertical if vertical and vertical != "all" else "db")
    return write_leads_csv(hydrated, output_dir=output_dir, vertical_tag=tag)
