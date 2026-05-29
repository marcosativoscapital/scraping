"""Pipeline principal — orquestra scrapers, Claude e enrichers."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from tqdm import tqdm

from .claude_agent.classifier import classify_company
from .claude_agent.client import ClaudeClient
from .claude_agent.parser import extract_companies_from_html
from .claude_agent.personalize import generate_trigger
from .claude_agent.scorer import score_lead
from .db.store import Store
from .enrichers.brasil_api import enrich_with_cnpj
from .enrichers.email_validator import validate_email
from .enrichers.hunter import domain_from_site, find_email
from .playbooks.selector import select_playbooks_for_lead
from .scrapers.base import BaseScraper
from .scrapers.bets_spa_mf import BetsSPAMFScraper
from .scrapers.cobranca_ohub import CobrancaOHubScraper
from .scrapers.ips_bacen import IPsBacenScraper
from .scrapers.saas_abstartups import SaaSABStartupsScraper
from .sdr.queue import SDRQueue

logger = logging.getLogger(__name__)
console = Console()

SCRAPERS: dict[str, type[BaseScraper]] = {
    "betting": BetsSPAMFScraper,
    "pagamentos": IPsBacenScraper,
    "cobranca": CobrancaOHubScraper,
    "saas_b2b": SaaSABStartupsScraper,
}


def run_pipeline(
    vertical: str,
    limit: int | None = None,
    enrich_email: bool = False,
    output_dir: Path = Path("data/output"),
) -> list[dict[str, Any]]:
    """Executa o pipeline completo para uma vertical (ou 'all')."""
    client = ClaudeClient()
    verticais_a_rodar = list(SCRAPERS.keys()) if vertical == "all" else [vertical]

    todos_leads: list[dict] = []

    for vert in verticais_a_rodar:
        if vert not in SCRAPERS:
            console.print(f"[red]Vertical desconhecida: {vert}[/red]")
            continue

        console.print(f"\n[bold cyan]▶ {vert.upper()}[/bold cyan]")
        scraper = SCRAPERS[vert]()

        # 1) Scrape
        with Progress(SpinnerColumn(), TextColumn("[cyan]{task.description}")) as p:
            t = p.add_task(f"Coletando {vert}...", total=None)
            raw_results = scraper.scrape(limit=limit)
            p.update(t, completed=1)

        # 2) Parse HTML → empresas via Claude (ou JSON direto da API)
        empresas: list[dict] = []
        for raw in raw_results:
            tipo = raw.get("_tipo")
            if tipo == "raw_html":
                console.print("  • Parseando HTML com Gemini...")
                parsed = extract_companies_from_html(
                    client, raw["_html"], vert, raw["_fonte"]
                )
                empresas.extend(parsed)
            elif tipo == "json_direto":
                console.print(f"  • Coleta direta via API: {len(raw['_empresas'])} empresas")
                empresas.extend(raw["_empresas"])
            else:
                empresas.append(raw)

        if limit:
            empresas = empresas[:limit]

        console.print(f"  • [green]{len(empresas)} empresas extraídas[/green]")

        # 3) Para cada empresa: classifica, enriquece, pontua, personaliza
        leads_vert = []
        for empresa in tqdm(empresas, desc=f"  Processando {vert}", leave=False):
            lead: dict[str, Any] = {
                "vertical": vert,
                "data_coleta": datetime.now().isoformat(timespec="seconds"),
                "fonte": scraper.fonte_url,
                **empresa,
            }

            # 3.1) Classifica
            try:
                cls = classify_company(client, lead)
                lead["vertical"] = cls.get("vertical", vert)
                lead["segmento"] = cls.get("segmento")
                lead["porte_estimado"] = cls.get("porte_estimado")
                lead["classificacao_obs"] = cls.get("justificativa")
            except Exception as e:
                logger.warning("Falha ao classificar %s: %s", lead.get("empresa"), e)

            # 3.2) Enriquece via BrasilAPI (se tiver CNPJ)
            if lead.get("cnpj"):
                lead = enrich_with_cnpj(lead)

            # 3.3) Enriquece e-mail (opcional)
            if enrich_email and lead.get("site"):
                domain = domain_from_site(lead["site"])
                if domain:
                    hunter_data = find_email(domain)
                    if hunter_data and hunter_data.get("emails"):
                        primary = hunter_data["emails"][0]
                        lead["email_provavel"] = primary.get("value")
                        if lead["email_provavel"]:
                            v = validate_email(lead["email_provavel"])
                            lead["email_validado"] = v["mx_ok"]

            # 3.4) Pontua
            try:
                sc = score_lead(client, lead)
                lead["score_icp"] = sc.get("score")
                lead["score_breakdown"] = sc.get("breakdown")
                lead["recomendacao"] = sc.get("recomendacao")
            except Exception as e:
                logger.warning("Falha ao pontuar %s: %s", lead.get("empresa"), e)
                lead["score_icp"] = 0

            # 3.5) Gera gatilho personalizado (só pros bons)
            if (lead.get("score_icp") or 0) >= 50:
                try:
                    lead["gatilho_personalizado"] = generate_trigger(client, lead)
                except Exception as e:
                    logger.warning("Falha ao personalizar %s: %s", lead.get("empresa"), e)

            # 3.6) Seleciona 2-3 playbooks de outbound aplicáveis (score >= 40)
            if (lead.get("score_icp") or 0) >= 40:
                try:
                    playbooks = select_playbooks_for_lead(client, lead, n=3)
                    lead["playbooks_sugeridos"] = playbooks
                except Exception as e:
                    logger.warning("Falha ao selecionar playbooks %s: %s", lead.get("empresa"), e)

            leads_vert.append(lead)

        # 4) Persiste no DB + playbooks vinculados
        store = Store()
        sdr_queue = SDRQueue(store)
        for lead in leads_vert:
            lead_id = store.upsert_lead(lead)
            pbs = lead.get("playbooks_sugeridos") or []
            if pbs:
                sdr_queue.assign_playbooks(lead_id, pbs)

        todos_leads.extend(leads_vert)
        console.print(
            f"  • [green]{len(leads_vert)} leads processados em {vert}[/green]"
        )

    # Estatísticas Claude
    stats = client.stats()
    console.print(
        f"\n[bold]Claude stats:[/bold] cache hits={stats['hits']} misses={stats['misses']}"
        f" tokens in={stats['total_input_tokens']:,} out={stats['total_output_tokens']:,}"
    )

    return todos_leads
