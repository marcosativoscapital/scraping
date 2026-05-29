"""Exportador CSV padronizado."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

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
